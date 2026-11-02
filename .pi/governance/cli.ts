import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { queryAgentTree } from "./agent-tree.ts";
import { queryArchives, queryDelegations, queryEvents, queryRunLineage } from "./audit-query.ts";
import { executionAttempts, probeExecutionAttempt } from "./execution-identity.ts";
import { type Identity, observeIdentity, resolveIdentity } from "./identity.ts";
import { INSTALL_VERSION } from "./installation.ts";
import { GovernanceKernel } from "./kernel.ts";
import { observeRun } from "./native-observability.ts";
import { scanOrphanRuns } from "./orphan-scan.ts";
import { reconcileNativeRun } from "./run-reconciliation.ts";
import { checkRuntimeVersion, checkSessionRuntime } from "./runtime-version.ts";
import { projectStatus } from "./status.ts";
import { dataRoot, GovernanceStore, primaryWorktree } from "./store.ts";
import {
	approveSubagentPolicy,
	saveSubagentPolicy,
	subagentPolicyStatus,
	syncSubagentPolicy,
} from "./subagent-policy.ts";
import { awaitNativeStop, readNativeRunStatus, requestNativeStop } from "./subagent-supervision.ts";
import { queryTaskTree } from "./task-tree.ts";
import type { ProjectContract, TaskContract, Verification } from "./types.ts";
import { assertProjectDocumentsWritable, checkViews, renderViews } from "./views.ts";
import { createWorkspace, destroyWorkspace, inspectWorkspace, verifyTakeover } from "./workspace.ts";
import { archiveWorkspace } from "./workspace-archive.ts";

const project = primaryWorktree(execFileSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" }).trim());
const store = new GovernanceStore(dataRoot(project));
const kernel = new GovernanceKernel(store);
/**
 * Who this process is, resolved rather than assumed.
 *
 * `local:<user>` used to be the only identity available, which made an agent's command
 * indistinguishable from the operator typing it. The levels are now explicit and every
 * fallback is recorded, so a reader can tell "a governed Run said this" from "an account
 * name was the best we had".
 */
const identity = await resolveProcessIdentity();

async function resolveProcessIdentity(): Promise<Identity> {
	const observed = observeIdentity({
		env: process.env,
		username: (() => {
			try {
				return os.userInfo().username;
			} catch {
				return null;
			}
		})(),
		interactive: Boolean(process.stdin.isTTY),
	});
	// A session ID in the environment proves nothing on its own: a stale or forged value
	// must not be promoted. Only a session the ledger has observed counts.
	if (observed.sessionId) observed.sessionKnown = isObservedSession(kernel.getState(), observed.sessionId);
	return resolveIdentity(observed);
}

function isObservedSession(state: ReturnType<GovernanceKernel["getState"]>, sessionId: string): boolean {
	return state.events.some(
		(event) => event.type === "agent.session-observed" && event.payload.sessionId === sessionId,
	);
}

const actor = identity.id;
const [command, action, ...args] = process.argv.slice(2);

function required(value: string | undefined, label: string): string {
	if (!value) throw new Error(`${label} is required`);
	return value;
}

function jsonFile<T>(file: string): T {
	return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

try {
	let output: unknown;
	if (command === "project" && action === "draft") {
		assertProjectDocumentsWritable(project);
		kernel.submitProjectDraft(jsonFile<ProjectContract>(required(args[0], "project contract file")), actor);
		output = "Project draft recorded; human approval pending";
	} else if (command === "project" && action === "approve") {
		kernel.approveProject(Number(required(args[0], "project revision")), actor);
		output = "Project baseline approved";
	} else if (command === "project" && action === "reject") {
		kernel.rejectProject(Number(required(args[0], "project revision")), actor, required(args[1], "rejection reason"));
		output = "Project draft rejected; prior approved baseline remains active";
	} else if (command === "project" && (action === "pause" || action === "resume" || action === "revoke")) {
		kernel.controlProject(action, actor);
		output = `Project ${action} recorded`;
	} else if (command === "project" && action === "reset") {
		// Two positional arguments are the second confirmation: the project id has to
		// be retyped, and the reason is required so the ledger says why.
		const event = kernel.resetProject({
			actor,
			reason: required(args[1], "reset reason"),
			confirm: required(args[0], "project id confirmation"),
		});
		output = {
			reset: "project governance revoked",
			sequence: event.sequence,
			backup: (event.payload.backupReference as { path?: string } | undefined)?.path ?? null,
			next: "Submit a new project draft, then `project approve <revision>`. Historical Tasks, Runs and acceptances stay readable but no longer authorize execution.",
		};
	} else if (command === "project" && action === "archive") {
		const event = kernel.archiveHistory({
			actor,
			reason: required(args[1], "archive reason"),
			confirm: required(args[0], "project id confirmation"),
		});
		output = {
			archived: event.payload.archiveId,
			sequence: event.sequence,
			counts: event.payload.archivedRecordCounts,
			backup: (event.payload.backupReference as { path?: string } | undefined)?.path ?? null,
			next: "The current workspace is empty. View the archive in management/ARCHIVE.md.",
		};
	} else if (command === "task" && (action === "create" || action === "create-internal" || action === "revise")) {
		const evaluation = kernel.submitTask(
			jsonFile<TaskContract>(required(args[0], "contract file")),
			actor,
			action === "create-internal" ? "internal" : action === "revise" ? "revision" : "ordinary",
		);
		output =
			evaluation.effect === "auto"
				? `Task authorized by approval rule ${evaluation.ruleId}`
				: `Task created; approval is pending under rule ${evaluation.ruleId}`;
	} else if (command === "decision" && (action === "approve" || action === "reject")) {
		output = kernel.recordDecision(
			required(args[0], "decision ID"),
			action === "approve" ? "approved" : "rejected",
			actor,
			required(args[1], "scope"),
			args[2] ?? null,
			[],
		);
	} else if (command === "task" && action === "approve") {
		const decisionId = required(args[1], "decision ID");
		// One human command approves a pending task decision: record the
		// decision, then bind the approval to the task revision.
		if (kernel.getState().decisions[decisionId]?.result === "pending")
			kernel.recordDecision(decisionId, "approved", actor, "task revision", null, []);
		kernel.approveTask(required(args[0], "task ID"), decisionId, actor);
		output = "Task revision approved";
	} else if (command === "task" && action === "tree") {
		output = queryTaskTree(kernel.getState());
	} else if (command === "workspace" && action === "create") {
		output = createWorkspace(project, required(args[0], "task ID"), kernel);
	} else if (command === "workspace" && action === "archive") {
		const event = archiveWorkspace(project, store, {
			actor,
			confirm: required(args[0], "project id confirmation"),
			reason: required(args[1], "archive reason"),
		});
		output = {
			archiveId: event.payload.archiveId,
			sequence: event.sequence,
			snapshot: event.payload.snapshotReference,
			next: `Current Project and Plan are empty. Create and approve project revision r${kernel.getState().projectRevisionFloor + 1}; approve the retained Subagent policy before delegation.`,
		};
	} else if (command === "workspace" && action === "inspect") {
		const workspace = kernel.getState().workspaces[required(args[0], "workspace ID")];
		if (!workspace) throw new Error("Unknown workspace");
		output = inspectWorkspace(workspace);
	} else if (command === "workspace" && action === "takeover") {
		const workspace = kernel.getState().workspaces[required(args[0], "workspace ID")];
		if (!workspace) throw new Error("Unknown workspace");
		output = verifyTakeover(workspace, kernel);
	} else if (command === "workspace" && action === "release") {
		kernel.releaseWorkspace(
			required(args[0], "workspace ID"),
			required(args[1], "run ID"),
			actor,
			required(args[2], "terminal proof"),
		);
		output = "Workspace released";
	} else if (command === "workspace" && action === "destroy") {
		output = destroyWorkspace(project, required(args[0], "workspace ID"), kernel, actor);
	} else if (command === "task" && action === "cancel") {
		const taskId = required(args[0], "task ID");
		const reason = required(args[1], "reason");
		// Runs still in flight have to be stopped with the Task, otherwise the record
		// would claim a cancelled Task while a child is still working. Passing the
		// flag is what says the operator wants that, rather than discovering it.
		const cancellation = kernel.cancelTask(taskId, reason, actor, {
			cancelRuns: args.includes("--cancel-runs"),
		});
		output = {
			taskId: cancellation.taskId,
			cancelledRuns: cancellation.cancelledRunIds,
			releasedTokens: cancellation.releasedTokens,
		};
	} else if (command === "run" && action === "cancel") {
		// Stop, confirm, then record. The old order recorded first and freed the
		// concurrency slot while the child kept working - it ran ten more minutes and
		// spent 853,137 more tokens under a ledger that already said CANCELLED.
		const runId = required(args[0], "run ID");
		const reason = required(args[1], "reason");
		const current = kernel.getState().runs[runId];
		if (!current) throw new Error("Unknown Run");
		const request = requestNativeStop(current, reason);
		if (!request.requested) throw new Error(`Cannot stop Run ${runId}: ${request.detail}`);
		const stopped = await awaitNativeStop(current);
		if (!stopped.stopped)
			throw new Error(
				`Stop requested for Run ${runId} but not confirmed: ${stopped.detail}. ` +
					"The Run stays active so its concurrency slot is not released while work may continue.",
			);
		const native = readNativeRunStatus(current);
		if (native.terminalOutcome) {
			// The child may have finished before it noticed the stop request. Its
			// observed result wins over the requested cancellation.
			const reconciled = reconcileNativeRun(kernel, runId, actor);
			output = {
				runId,
				state: reconciled.run.state,
				usageTokens: reconciled.run.usageTokens,
				stopConfirmed: true,
				cancellationWon: false,
			};
		} else {
			const run = kernel.cancelRun(runId, reason, actor);
			output = { runId: run.runId, state: run.state, usageTokens: run.usageTokens, stopConfirmed: true };
		}
	} else if (command === "run" && action === "state") {
		const next = required(args[1], "state");
		if (next !== "FAILED" && next !== "CANCELLED")
			throw new Error("Manual Run correction supports only FAILED or CANCELLED");
		const proof = required(args[2], "terminal proof");
		output = kernel.updateRun(required(args[0], "run ID"), next, {}, proof);
	} else if (command === "run" && action === "inspect") {
		const run = kernel.getState().runs[required(args[0], "run ID")];
		if (!run) throw new Error("Unknown Run");
		// The ledger record says what governance decided; the observation says what the
		// child is doing. Both are needed: showing only the record lets a running child
		// look identical to a stalled one.
		output = { run, native: readNativeRunStatus(run), observation: observeRun(run) };
	} else if (command === "run" && action === "activity") {
		const run = kernel.getState().runs[required(args[0], "run ID")];
		if (!run) throw new Error("Unknown Run");
		const observed = observeRun(run);
		output = {
			runId: run.runId,
			taskId: run.taskId,
			state: { governance: run.state, native: observed.native.state },
			observedAt: observed.observedAt,
			turn: observed.native.turns,
			step: observed.native.step,
			lastTool: observed.activity.tools.at(-1) ?? null,
			windowTokens: observed.native.windowTokens,
			windowPeakTokens: observed.native.windowPeakTokens,
			outputTokens: observed.native.outputTokens,
			lastOutputAt: observed.activity.lastOutputAt,
			secondsSinceOutput:
				!(["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"] as const).some((state) => state === run.state) ||
				observed.activity.lastOutputAt === null
					? null
					: Math.max(0, Math.floor((observed.observedAt - observed.activity.lastOutputAt) / 1000)),
			unknowns: observed.unknowns,
		};
	} else if (command === "run" && action === "probe") {
		// Read-only on purpose: probing answers "can this be settled", and settling it is a
		// separate explicit action. A probe that changed state would make asking expensive.
		const runId = required(args[0], "run ID");
		const run = kernel.getState().runs[runId];
		if (!run) throw new Error("Unknown Run");
		const attempts = executionAttempts(kernel.getState(), runId);
		const probe = probeExecutionAttempt(run, attempts);
		if (args.includes("--confirm-lost")) {
			// Only the verdict that was actually proven may free the slot. `releasable` is
			// computed by the probe from positive evidence; re-deriving it here would let a
			// second, cheaper rule drift from the first.
			if (!probe.releasable) throw new Error(`Run ${runId} cannot be declared lost: ${probe.reason}`);
			output = {
				probe,
				lost: kernel.markExecutionLost(runId, "dead", probe.reason, actor),
			};
		} else {
			output = probe;
		}
	} else if (command === "run" && action === "orphans") {
		// Lists what could be settled. `--confirm-lost` settles every candidate whose probe
		// already proved death - the probe decides, not this loop, so a Run that is merely
		// stuck stays stuck rather than being guessed away in bulk.
		const scan = scanOrphanRuns(kernel.getState());
		output = args.includes("--confirm-lost")
			? {
					scan,
					lost: scan.candidates.map((candidate) =>
						kernel.markExecutionLost(candidate.runId, "dead", candidate.probe.reason, actor),
					),
				}
			: scan;
	} else if (command === "run" && action === "reconcile") {
		output = reconcileNativeRun(kernel, required(args[0], "run ID"), actor);
	} else if (command === "deliverable" && action === "submit") {
		output = kernel.submitDeliverable(jsonFile(required(args[0], "deliverable file")), project);
	} else if (command === "verification" && action === "record") {
		const input = jsonFile<{
			deliverableId: string;
			criteria: Verification["criteria"];
			/** Run that performed the review; its identity is read from the ledger, not here. */
			verifierRunId?: string;
		}>(required(args[0], "verification file"));
		output = kernel.recordVerification(input.deliverableId, actor, input.criteria, input.verifierRunId, {
			source: identity.source,
			assurance: identity.assurance,
		});
	} else if (command === "task" && action === "accept") {
		kernel.acceptTask(required(args[0], "task ID"), required(args[1], "verification ID"), actor);
		output = "Task accepted";
	} else if (command === "views" && action === "render") {
		output = "Views rendered";
	} else if (command === "views" && action === "check") {
		const status = checkViews(project);
		if (!status.fresh) process.exitCode = 1;
		output = status.fresh ? `Views current (ledger sequence ${status.currentSequence})` : status.reasons.join("; ");
	} else if (command === "version") {
		// Two facts, compared. `verified: true` from `gov upgrade` describes the disk;
		// this reports what the files on disk are, so an operator can tell a deployed
		// fix from a running one.
		output = {
			// Two different questions. `process` describes this CLI invocation, which
			// always loads the disk copy; `session` describes the pi process that owns
			// the ledger. Only the second one can tell an operator that a deployed fix
			// is not running yet.
			process: checkRuntimeVersion(project),
			session: checkSessionRuntime(project, kernel.getState()),
			installVersion: INSTALL_VERSION,
		};
	} else if (command === "state" && action === "show") {
		output = {
			...kernel.getState(),
			runtimeVersion: {
				process: checkRuntimeVersion(project),
				session: checkSessionRuntime(project, kernel.getState()),
			},
		};
	} else if (command === "status") {
		output = projectStatus(kernel.getState(), project);
	} else if (command === "policy" && action === "show") {
		output = subagentPolicyStatus(project, kernel.getState());
	} else if (command === "policy" && action === "sync") {
		output = syncSubagentPolicy(project, kernel, actor);
	} else if (command === "policy" && action === "save") {
		output = saveSubagentPolicy(
			project,
			kernel,
			jsonFile<unknown>(required(args[0], "policy JSON file")),
			required(args[1], "current policy digest"),
			actor,
		);
	} else if (command === "policy" && action === "approve") {
		approveSubagentPolicy(project, kernel, actor);
		output = `Subagent policy approved: ${subagentPolicyStatus(project, kernel.getState()).approvedDigest}`;
	} else if (command === "audit" && action === "delegations") {
		output = queryDelegations(kernel.getState(), args[0]);
	} else if (command === "audit" && action === "tree") {
		output = queryAgentTree(kernel.getState());
	} else if (command === "audit" && action === "run") {
		output = queryRunLineage(kernel.getState(), required(args[0], "run ID"));
	} else if (command === "audit" && action === "events") {
		output = queryEvents(kernel.getState(), required(args[0], "event type prefix"));
	} else if (command === "audit" && action === "archive") {
		output = queryArchives(kernel.getState(), args[0]);
	} else if (command === "backup" && action === "export") {
		const destination = path.resolve(required(args[0], "destination"));
		store.backup(destination);
		output = destination;
	} else if (command === "backup" && action === "restore") {
		store.restore(path.resolve(required(args[0], "backup file")));
		output = "Governance log restored into an empty data root";
	} else {
		throw new Error(
			"Usage: project draft|approve|reject|pause|resume|revoke|reset|archive, task create|create-internal|revise|approve|accept|cancel|tree, decision approve|reject, workspace create|inspect|takeover|release|destroy|archive, run state|inspect|activity|probe|orphans|reconcile|cancel, deliverable submit, verification record, views render|check, state show, status, version, policy show|save|sync|approve, audit tree|delegations|run|events|archive, backup export|restore",
		);
	}
	if (
		command !== "state" &&
		command !== "status" &&
		command !== "version" &&
		!(command === "run" && (action === "inspect" || action === "activity")) &&
		!(command === "policy" && (action === "show" || action === "sync" || action === "save")) &&
		!(command === "task" && action === "tree") &&
		command !== "audit" &&
		command !== "backup" &&
		!(command === "views" && action === "check")
	)
		renderViews(project, kernel);
	process.stdout.write(`${typeof output === "string" ? output : JSON.stringify(output, null, 2)}\n`);
} catch (error) {
	process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
	process.exitCode = 1;
}
