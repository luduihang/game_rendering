import { createHash, randomUUID } from "node:crypto";
import * as path from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { capabilitiesOf } from "./agent-templates.ts";
import { awaitNativePid, newExecutionAttemptId } from "./execution-identity.ts";
import { GovernanceKernel, isTaskActivatedForSession } from "./kernel.ts";
import { describeOrphanCandidates, scanOrphanRuns } from "./orphan-scan.ts";
import { withProfileDefault } from "./profiles.ts";
import { acquireSidecarLock, type SidecarHandle, startSidecar } from "./remote.ts";
import { checkRuntimeVersion, recordRuntimeLoad } from "./runtime-version.ts";
import { resolveSessionOrigin } from "./session-identity.ts";
import { dataRoot, GovernanceStore, primaryWorktree } from "./store.ts";
import { loadSubagentPolicy, resolveSubagentRoute, subagentPolicyStatus } from "./subagent-policy.ts";
import { compareNativeTools, readNativeRunStatus, subagentRpc } from "./subagent-supervision.ts";
import type {
	ApprovalDiagnosis,
	Authority,
	Delegation,
	GovernanceEventInput,
	ProjectContract,
	RunState,
	TaskContract,
} from "./types.ts";
import { assertProjectDocumentsWritable, renderViews } from "./views.ts";
import { verifyTakeover } from "./workspace.ts";

const params = Type.Object({
	taskId: Type.String(),
	agent: Type.Optional(Type.String()),
	objective: Type.String(),
	budgetTokens: Type.Integer({ minimum: 1 }),
	workspaceId: Type.Optional(Type.String()),
	parentRunId: Type.Optional(Type.String()),
	retryOf: Type.Optional(Type.String()),
	contextTier: Type.Optional(Type.String()),
	modelProfile: Type.Optional(Type.String()),
	paths: Type.Array(Type.String()),
	tools: Type.Array(Type.String()),
	readRepository: Type.Boolean(),
	writeWorkspace: Type.Boolean(),
	commitBranch: Type.Boolean(),
	integrateBranch: Type.Boolean(),
});
const authoritySchema = Type.Object({
	paths: Type.Array(Type.String()),
	tools: Type.Array(Type.String()),
	readRepository: Type.Boolean(),
	writeWorkspace: Type.Boolean(),
	commitBranch: Type.Boolean(),
	integrateBranch: Type.Boolean(),
});
const approvalRuleSchema = Type.Object({
	id: Type.String(),
	effect: Type.Union([Type.Literal("auto"), Type.Literal("ask"), Type.Literal("deny")]),
	risk: Type.Union([Type.Literal("low"), Type.Literal("medium"), Type.Literal("high")]),
	match: Type.Object({
		taskKind: Type.Optional(
			Type.Union([Type.Literal("internal"), Type.Literal("ordinary"), Type.Literal("revision")]),
		),
		pathsAny: Type.Optional(Type.Array(Type.String())),
		toolsAny: Type.Optional(Type.Array(Type.String())),
		toolsAll: Type.Optional(Type.Array(Type.String())),
		writeWorkspace: Type.Optional(Type.Boolean()),
		commitBranch: Type.Optional(Type.Boolean()),
		integrateBranch: Type.Optional(Type.Boolean()),
		maxDepthMin: Type.Optional(Type.Integer({ minimum: 0 })),
		minBudgetTokens: Type.Optional(Type.Integer({ minimum: 1 })),
		maxBudgetTokens: Type.Optional(Type.Integer({ minimum: 1 })),
	}),
});
const projectSchema = Type.Object({
	projectId: Type.String(),
	revision: Type.Integer({ minimum: 1 }),
	name: Type.String(),
	goal: Type.String(),
	inScope: Type.Array(Type.String()),
	outOfScope: Type.Array(Type.String()),
	successCriteria: Type.Array(Type.String()),
	authority: authoritySchema,
	delegationPolicy: Type.Object({
		allowInternalTasks: Type.Boolean(),
		maxDepth: Type.Integer({ minimum: 0 }),
		maxConcurrent: Type.Integer({ minimum: 1 }),
	}),
	resourceLimits: Type.Object({ budgetTokens: Type.Integer({ minimum: 1 }) }),
	humanApprovalTriggers: Type.Array(Type.String()),
	approvalPolicy: Type.Object({
		version: Type.Literal(1),
		defaultEffect: Type.Union([Type.Literal("ask"), Type.Literal("deny")]),
		rules: Type.Array(approvalRuleSchema),
	}),
	prd: Type.String(),
	plan: Type.String(),
	changeReason: Type.String(),
});
const taskSchema = Type.Object({
	taskId: Type.String(),
	revision: Type.Integer({ minimum: 1 }),
	kind: Type.Optional(Type.Union([Type.Literal("container"), Type.Literal("executable")])),
	parentTaskId: Type.Optional(Type.Union([Type.String(), Type.Null()])),
	splitReason: Type.Optional(Type.String()),
	goal: Type.String(),
	scope: Type.Array(Type.String()),
	acceptance: Type.Array(Type.String()),
	owner: Type.String(),
	budgetTokens: Type.Integer({ minimum: 0 }),
	maxDepth: Type.Integer({ minimum: 0 }),
	maxConcurrent: Type.Integer({ minimum: 0 }),
	authority: authoritySchema,
	dependencies: Type.Array(Type.Object({ taskId: Type.String(), requiredState: Type.Literal("accepted") })),
});

function nativeRunId(value: unknown): string | null {
	if (typeof value !== "object" || value === null || !("runId" in value)) return null;
	return typeof value.runId === "string" ? value.runId : null;
}

/**
 * What a human has to change before a Task can be approved, in one line.
 *
 * "Awaiting human approval" on its own does not say whether the Task needs a
 * baseline revision or only a signature, so the specific excess is named.
 */
function describeDiagnosis(diagnosis: ApprovalDiagnosis | undefined): string {
	if (!diagnosis || diagnosis.baselineSubset) return "";
	const parts: string[] = [];
	if (diagnosis.exceeded.paths.length) parts.push(`paths ${diagnosis.exceeded.paths.join(", ")}`);
	if (diagnosis.exceeded.tools.length) parts.push(`tools ${diagnosis.exceeded.tools.join(", ")}`);
	if (diagnosis.exceeded.flags.length) parts.push(`flags ${diagnosis.exceeded.flags.join(", ")}`);
	if (diagnosis.exceeded.budgetTokens !== null) parts.push(`budget +${diagnosis.exceeded.budgetTokens} tokens`);
	if (diagnosis.exceeded.maxDepth !== null) parts.push(`depth +${diagnosis.exceeded.maxDepth}`);
	if (diagnosis.exceeded.maxConcurrent !== null) parts.push(`concurrency +${diagnosis.exceeded.maxConcurrent}`);
	return ` Baseline revision required: ${parts.join("; ")}.`;
}

export default function governanceBridge(pi: ExtensionAPI, adoptOnLoad?: ExtensionContext) {
	// Keyed by session id: one pi process can host several sessions, and each
	// session activates its own task. A single variable let the last activation
	// win, so a concurrent delegate in another session looked "not activated"
	// and was refused with a misleading /gov-task hint.
	const activeTasks = new Map<string, string>();
	let currentSession: string | null = null;
	let currentProject: string | null = null;
	let remote: SidecarHandle | null = null;
	let remoteLock: { release: () => void } | null = null;
	const pendingCompletions = new Map<string, unknown>();

	// A child session records one event per tool call, and every append replays the
	// whole ledger while holding the writer lock. Left unbatched, five children
	// spend their time queueing for the lock instead of working (measured: the
	// ledger refused 80% of concurrent writes before the lock learned to wait).
	// Actions are therefore buffered per ledger and written in one acquisition.
	// Flushes happen on the threshold, at each turn boundary, before any tool that
	// reads the ledger, and at shutdown, so the audit trail stays complete while a
	// crash can lose at most one partial batch.
	const OBSERVED_ACTION_BATCH = 20;
	const pendingObserved = new Map<string, GovernanceEventInput[]>();
	const flushObservedActions = (root?: string): void => {
		for (const key of root === undefined ? [...pendingObserved.keys()] : [root]) {
			const batch = pendingObserved.get(key);
			if (!batch?.length) continue;
			pendingObserved.set(key, []);
			try {
				new GovernanceStore(key).appendMany(batch);
			} catch (error) {
				// Put the batch back so a later flush retries it rather than losing the
				// audit trail; the caller still sees the failure now.
				pendingObserved.set(key, [...batch, ...(pendingObserved.get(key) ?? [])]);
				throw error;
			}
		}
	};
	const queueObservedAction = (store: GovernanceStore, input: GovernanceEventInput): void => {
		const batch = pendingObserved.get(store.root) ?? [];
		batch.push(input);
		pendingObserved.set(store.root, batch);
		if (batch.length >= OBSERVED_ACTION_BATCH) flushObservedActions(store.root);
	};

	const stopRemote = () => {
		remote?.stop();
		remoteLock?.release();
		remote = null;
		remoteLock = null;
	};
	const activateChildSession = (kernel: GovernanceKernel, ctx: ExtensionContext) => {
		if (!ctx.sessionManager.getHeader?.()?.parentSession) return;
		const origin = resolveSessionOrigin(kernel, ctx);
		if (!origin.taskId) return;
		if (activeTasks.get(origin.sessionId) !== origin.taskId) {
			activeTasks.set(origin.sessionId, origin.taskId);
			kernel.store.append({
				type: "session.task-activated",
				actor: `pi:${origin.sessionId}`,
				taskId: origin.taskId,
				runId: origin.parentRunId,
				delegationId: null,
				sessionId: origin.sessionId,
				payload: { sessionId: origin.sessionId, source: "native-child-binding" },
			});
		}
	};

	/**
	 * The repository this session is working in, or null when it is not in one.
	 *
	 * `primaryWorktree` shells out to git and throws outside a repo. A tool can let that
	 * surface as an error, but session hooks run for every session, so they need the
	 * quiet form: a plain "no governance here" rather than a crash that removes the
	 * tools for every session that follows.
	 */
	function governanceRootOf(cwd: string): string | null {
		try {
			return primaryWorktree(cwd);
		} catch {
			return null;
		}
	}

	// A session is adopted once per process. Adoption does what session_start used to
	// do inline, but the first turn can also trigger it: a session start is not
	// guaranteed to reach this handler. The extension is installed per user and loads
	// this bridge from inside its own session_start handler, so a handler registered
	// here is added during that dispatch and never runs for it. The observed result
	// was a bridge with working tools that had never observed its own session, so
	// delegation refused with "session has not been observed".
	// Remembers which session was last adopted, not which sessions must never be adopted
	// again. A restarted Pi resumes the same session ID while running different code, so
	// skipping the second adoption kept the runtime-load record at the old digest and the
	// version check reported `stale` forever. The adoption itself is idempotent on the
	// session identity triple, so repeating it costs one comparison.
	let adoptedSession: string | null = null;

	const adoptSession = (ctx: ExtensionContext): void => {
		const sessionId = ctx.sessionManager.getSessionId();
		currentSession = sessionId;
		pendingCompletions.clear();
		// Governance applies to a repository, and pi may be started anywhere. This
		// extension is installed per user so that it loads from any working directory;
		// without this guard, starting pi outside a repo would throw here and take the
		// whole extension down, including the tools that are useful nowhere else.
		const root = governanceRootOf(ctx.cwd);
		if (!root) {
			currentProject = null;
			activeTasks.delete(sessionId);
			return;
		}
		currentProject = root;
		const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(currentProject)));
		const state = kernel.getState();
		if (!state.events.some((event) => event.type === "project.initialized")) {
			activeTasks.delete(sessionId);
			return;
		}
		// Recorded before anything is observed, so the ledger always says which kernel
		// produced the events around it - the question `verified: true` cannot answer.
		try {
			recordRuntimeLoad(kernel.store, sessionId);
		} catch {
			/* a load record must never take the session down */
		}
		const runtime = checkRuntimeVersion(currentProject);
		if (runtime.state === "stale") ctx.ui.notify(`治理内核版本不一致：${runtime.detail}`, "warning");
		// A Run whose child died between sessions stays RUNNING and keeps its slot, and the
		// operator has no way to notice from inside a new session. Surface it once, here,
		// and stop at surfacing: settling frees a concurrency slot, and a wrong settlement
		// is the double-booking this whole mechanism guards against. The hint carries the
		// exact command, so acting on it is one paste.
		try {
			const orphans = scanOrphanRuns(kernel.getState());
			if (orphans.unavailable) ctx.ui.notify(`孤儿 Run 扫描不可用：${orphans.unavailable}`, "warning");
			else
				for (const hint of describeOrphanCandidates(
					orphans,
					`node ${path.join(currentProject, ".pi", "governance", "cli.ts")}`,
				))
					ctx.ui.notify(hint, "warning");
		} catch {
			/* a scan must never take the session down */
		}
		const parentSessionFile = ctx.sessionManager.getHeader?.()?.parentSession ?? null;
		const sessionFile = ctx.sessionManager.getSessionFile() ?? null;
		// Idempotent on the exact identity triple: adopting the same session again adds
		// nothing, while an adoption that now knows the file supplements the earlier
		// record instead of being skipped.
		const alreadyRecorded = state.events.some(
			(event) =>
				event.type === "agent.session-observed" &&
				event.payload.sessionId === sessionId &&
				event.payload.sessionFile === sessionFile &&
				event.payload.parentSessionFile === parentSessionFile,
		);
		if (!alreadyRecorded)
			kernel.store.append({
				type: "agent.session-observed",
				actor: `pi:${sessionId}`,
				taskId: null,
				runId: null,
				delegationId: null,
				sessionId,
				payload: {
					sessionId,
					agentInstanceId: `pi-session:${sessionId}`,
					sessionFile,
					parentSessionFile,
				},
			});
		// A new session has no file until its first message is written, so this record
		// can only say `null`. Delegation matches the file exactly, so adoption runs
		// again on the first turn and supplements the record once the file exists -
		// adding a fact, because the ledger cannot amend one.
		const mainId = `pi-session:${sessionId}`;
		if (!state.agents[mainId])
			kernel.registerAgent(
				parentSessionFile
					? { agentId: mainId, harness: "pi", role: "executor", capabilities: ["delegated-work"] }
					: {
							agentId: mainId,
							harness: "pi",
							role: "coordinator",
							capabilities: ["task-orchestration", "delegation"],
						},
				mainId,
			);
		if (parentSessionFile) {
			try {
				activateChildSession(kernel, ctx);
			} catch {
				/* Native Run may not be linked until spawn replies. */
			}
		}
		// The public panel lives only while a pi session owns this ledger.
		stopRemote();
		if (process.env.BLOG_TOKEN && process.env.GOV_REMOTE !== "0") {
			remoteLock = acquireSidecarLock(currentProject);
			if (remoteLock) {
				try {
					remote = startSidecar({ project: currentProject });
				} catch {
					remoteLock.release();
					remoteLock = null;
				}
			}
		}
		const activation = state.events
			.filter((event) => event.type === "session.task-activated" && event.payload.sessionId === sessionId)
			.at(-1);
		if (!parentSessionFile) {
			const taskId = activation?.taskId ?? null;
			if (taskId && state.approved[taskId] === state.tasks[taskId]?.revision) activeTasks.set(sessionId, taskId);
			else activeTasks.delete(sessionId);
		}
		adoptedSession = sessionId;
	};

	pi.on("session_start", (_event, ctx) => adoptSession(ctx));
	// The user-level shim imports this bridge from inside its own session_start
	// handler, so a handler registered here during that dispatch misses the event
	// that is already being delivered. Without this, the sidecar and the session
	// record wait for the first turn: a session left open never publishes, and the
	// panel shows nothing while the window is plainly running.
	if (adoptOnLoad) adoptSession(adoptOnLoad);
	pi.on("session_shutdown", (_event, ctx) => {
		try {
			flushObservedActions();
		} catch {
			/* shutdown must still release the sidecar even if the last batch failed */
		}
		const sessionId = ctx.sessionManager.getSessionId();
		if (currentProject) {
			const store = new GovernanceStore(dataRoot(primaryWorktree(ctx.cwd)));
			if (store.read().events.some((event) => event.type === "project.initialized"))
				store.append({
					type: "agent.session-ended",
					actor: `pi:${sessionId}`,
					taskId: activeTasks.get(sessionId) ?? null,
					runId: null,
					delegationId: null,
					sessionId,
					payload: { sessionId },
				});
		}
		stopRemote();
		activeTasks.delete(sessionId);
		currentSession = null;
		pendingCompletions.clear();
	});
	const observeLoop = (
		type: "agent.loop-started" | "agent.loop-settled",
		ctx: ExtensionContext,
		aborted?: boolean,
	) => {
		const store = new GovernanceStore(dataRoot(primaryWorktree(ctx.cwd)));
		// A turn boundary is the natural flush point: the batch never spans work the
		// operator would read as unfinished.
		try {
			flushObservedActions(store.root);
		} catch {
			/* the observation below should not be lost because a flush failed */
		}
		const state = store.read();
		if (!state.events.some((entry) => entry.type === "project.initialized")) return;
		const sessionId = ctx.sessionManager.getSessionId();
		const run = Object.values(state.runs).find(
			(candidate) => candidate.sessionRef === ctx.sessionManager.getSessionFile(),
		);
		store.append({
			type,
			actor: `pi:${sessionId}`,
			taskId: run?.taskId ?? activeTasks.get(sessionId) ?? null,
			runId: run?.runId ?? null,
			delegationId: run?.delegationId ?? null,
			sessionId,
			payload: {
				source: type === "agent.loop-started" ? "pi.agent_start" : "pi.agent_settled",
				...(aborted === undefined ? {} : { aborted }),
			},
		});
	};
	pi.on("agent_start", (_event, ctx) => observeLoop("agent.loop-started", ctx));
	pi.on("agent_settled", (event, ctx) => observeLoop("agent.loop-settled", ctx, event.aborted));
	pi.on("tool_call", (event, ctx) => {
		// Governance tools read the ledger and their guards may depend on the actions
		// just taken, so the buffer is drained before they run.
		if (event.toolName.startsWith("governance_")) {
			try {
				flushObservedActions(dataRoot(primaryWorktree(ctx.cwd)));
			} catch {
				/* the tool itself will report a ledger problem */
			}
		}
		if (ctx.sessionManager.getHeader?.()?.parentSession && !activeTasks.has(ctx.sessionManager.getSessionId())) {
			try {
				activateChildSession(new GovernanceKernel(new GovernanceStore(dataRoot(primaryWorktree(ctx.cwd)))), ctx);
			} catch {
				// The action remains unattributed until native session evidence is available.
			}
		}
		if (event.toolName === "subagent") {
			const project = primaryWorktree(ctx.cwd);
			const store = new GovernanceStore(dataRoot(project));
			const state = store.read();
			if (state.events.some((entry) => entry.type === "project.initialized")) {
				store.append({
					type: "delegation.unmanaged",
					actor: `pi:${ctx.sessionManager.getSessionId()}`,
					taskId: activeTasks.get(ctx.sessionManager.getSessionId()) ?? null,
					runId: null,
					delegationId: null,
					sessionId: ctx.sessionManager.getSessionId(),
					payload: {
						toolCallId: event.toolCallId || randomUUID(),
						parentToolCallId: event.parentToolCallId ?? null,
						agent: typeof event.input?.agent === "string" ? event.input.agent : null,
						outcome: "blocked",
					},
				});
			}
			return {
				block: true,
				reason:
					"Direct subagent execution is disabled. Initialize governance, approve a Task, activate it with /gov-task, and use governance_delegate.",
			};
		}
		// A session that never entered a governance project has nothing to observe;
		// calling primaryWorktree there throws instead of returning.
		const project = primaryWorktree(ctx.cwd);
		const store = new GovernanceStore(dataRoot(project));
		const state = store.read();
		const initialized = state.events.some((entry) => entry.type === "project.initialized");
		if (initialized) {
			const input = (event.input ?? {}) as Record<string, unknown>;
			const sessionId = ctx.sessionManager.getSessionId();
			const sessionFile = ctx.sessionManager.getSessionFile();
			const run = Object.values(state.runs).find((candidate) => candidate.sessionRef === sessionFile);
			const explicitTask = typeof input.taskId === "string" && state.tasks[input.taskId] ? input.taskId : null;
			const targetRun = typeof input.runId === "string" ? state.runs[input.runId] : null;
			const taskId = run?.taskId ?? explicitTask ?? targetRun?.taskId ?? activeTasks.get(sessionId) ?? null;
			const resource = (() => {
				if (
					!["read", "write", "edit", "grep", "find", "ls"].includes(event.toolName) ||
					typeof input.path !== "string"
				)
					return null;
				const relative = path.relative(project, path.resolve(ctx.cwd, input.path));
				if (relative.startsWith("..") || path.isAbsolute(relative)) return "[outside-project]";
				if (
					relative
						.split(path.sep)
						.some((part) => /(^\.env(?:\.|$)|^id_[^/]+$|secret|token|credential|private.?key)/i.test(part))
				)
					return "[sensitive-path]";
				return relative.slice(0, 300);
			})();
			const commandSha256 =
				event.toolName === "bash" && typeof input.command === "string"
					? createHash("sha256").update(input.command).digest("hex")
					: null;
			queueObservedAction(store, {
				type: "agent.action-observed",
				actor: `pi:${sessionId}`,
				taskId,
				runId: run?.runId ?? null,
				delegationId: run?.delegationId ?? null,
				sessionId,
				payload: {
					actionId: randomUUID(),
					toolCallId: event.toolCallId,
					parentToolCallId: event.parentToolCallId ?? null,
					tool: event.toolName,
					resource,
					commandSha256,
					focusTaskId: activeTasks.get(sessionId) ?? null,
					source: "pi.tool_call",
				},
			});
		}
	});
	pi.on("tool_result", (event, ctx) => {
		// The result is matched to the observed action, which is buffered until now.
		try {
			flushObservedActions(dataRoot(primaryWorktree(ctx.cwd)));
		} catch {
			/* keep recording the result even if the batch could not be written */
		}
		const project = governanceRootOf(ctx.cwd);
		if (!project) return;
		const store = new GovernanceStore(dataRoot(project));
		const state = store.read();
		if (!state.events.some((entry) => entry.type === "project.initialized")) return;
		const started = state.events
			.filter(
				(entry) =>
					entry.type === "agent.action-observed" &&
					entry.context.sessionId === ctx.sessionManager.getSessionId() &&
					entry.payload.toolCallId === event.toolCallId,
			)
			.at(-1);
		store.append({
			type: "agent.action-result",
			actor: `pi:${ctx.sessionManager.getSessionId()}`,
			taskId: started?.taskId ?? null,
			runId: started?.runId ?? null,
			delegationId: started?.delegationId ?? null,
			sessionId: ctx.sessionManager.getSessionId(),
			payload: {
				actionId: started?.payload.actionId ?? null,
				toolCallId: event.toolCallId,
				tool: event.toolName,
				outcome: event.isError ? "error" : "ok",
				source: "pi.tool_result",
				observationGap: started ? null : "tool_call_missing",
			},
		});
	});
	pi.on("before_agent_start", (event, ctx) => {
		// The backstop for a session start that never reached the handler above. Running
		// it before the request is observed means the session is always on the record
		// by the time anything is asked of governance.
		const startedSession = ctx.sessionManager.getSessionId();
		if (adoptedSession !== startedSession) adoptSession(ctx);
		const state = new GovernanceKernel(new GovernanceStore(dataRoot(ctx.cwd))).getState();
		if (!state.events.some((entry) => entry.type === "project.initialized")) return;
		new GovernanceStore(dataRoot(primaryWorktree(ctx.cwd))).append({
			type: "agent.request-observed",
			actor: `pi:${ctx.sessionManager.getSessionId()}`,
			taskId: activeTasks.get(ctx.sessionManager.getSessionId()) ?? null,
			runId: null,
			delegationId: null,
			sessionId: ctx.sessionManager.getSessionId(),
			payload: { messageType: event.messageType ?? "unknown", source: "pi.before_agent_start" },
		});
		const projectId = state.events.find((entry) => entry.type === "project.initialized")?.payload.projectId;
		let routingHint = "";
		try {
			const project = primaryWorktree(ctx.cwd);
			const { policy } = loadSubagentPolicy(project);
			const policyStatus = subagentPolicyStatus(project, state);
			routingHint =
				policy.version !== 1
					? ` Enabled child Agents: ${Object.entries(policy.agents)
							.filter(([name]) => policy.version !== 3 || policy.agents[name].enabled)
							.map(
								([name, role]) =>
									`${name} (${policy.version === 3 ? `${policy.agents[name].description}; ` : ""}${role.useFor})`,
							)
							.join(
								", ",
							)}. Choose modelProfile per role when needed. Policy approval: ${policyStatus.approved ? "current" : "required"}.`
					: ` Legacy V1 subagent model ${policy.model}; default tier ${policy.defaultTier}. contextTier is advisory, not a model window.`;
		} catch (error) {
			routingHint = ` Subagent policy is invalid: ${error instanceof Error ? error.message : String(error)}. Do not delegate until fixed.`;
		}
		return {
			message: {
				customType: "governance-project-context",
				display: false,
				content:
					state.projectApproved && state.projectStatus === "ACTIVE"
						? `Project ID ${projectId}. Project baseline r${state.projectApproved.revision} is active. Main Agent plans, coordinates and integrates work; split complex goals into Tasks, delegate code investigation and implementation to suitable child Agents, parallelize independent Tasks and respect dependencies. State each delegated goal, scope and deliverable, select the Agent explicitly from its description and useFor, then track results and organize acceptance. Direct implementation by Main is an exception, while its existing direct delivery path remains available. Use governance_task_create for internal tasks, governance_delegate for child runs, and governance_project_draft for changes. Exact inScope entries, authority ceilings and approvalPolicy decide whether a Task is auto-approved, pending or denied. Do not treat a PRD edit as approval. Read management/PROJECT.md and management/NOW.md for state. For natural-language archive, reset or decision requests, read .pi/governance/OPERATOR-GUIDE.md before acting; routine operation does not require Governance source.${routingHint}`
						: `Project ID ${projectId}. Project baseline is ${state.projectStatus}. Discuss goals, scope, exclusions, constraints, resources, approval rules and success criteria with the user. Use governance_project_draft to record PRD, contract and plan. The contract must include an ordered approvalPolicy with a default ask or deny effect. Governed Task execution and child delegation require local human approval via project approve. Basic Pi tools are observed but not blocked by this bridge. Read management/PROJECT.md and management/INBOX.md. For natural-language archive, reset or decision requests, read .pi/governance/OPERATOR-GUIDE.md before acting; routine operation does not require Governance source.`,
			},
		};
	});

	pi.registerTool({
		name: "governance_project_draft",
		label: "Draft project baseline",
		description:
			"Record a new immutable project contract revision, PRD and plan. This never approves the project. " +
			"PRD and plan must be structured multi-line Markdown with real newlines and headings: background, goals and non-goals, " +
			"current-state findings marked verified/unverified with evidence (file paths, tests), constraints, verifiable acceptance " +
			"criteria, risks and change points. Double-escaped payloads (literal backslash-n) are normalized once at the boundary; " +
			"unstructured drafts are rejected with the specific gap to fix. Define an ordered approvalPolicy for Task auto/ask/deny decisions; the human approves the whole Project baseline.",
		parameters: projectSchema,
		async execute(_id, input, _signal, _update, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			try {
				assertProjectDocumentsWritable(project);
				// `gov init --profile` supplies a default policy; the draft still
				// goes through the normal human approval of the whole baseline.
				const draft = withProfileDefault(project, input as { approvalPolicy?: ProjectContract["approvalPolicy"] });
				kernel.submitProjectDraft(draft as ProjectContract, `pi:${ctx.sessionManager.getSessionId()}`);
				renderViews(project, kernel);
				return {
					content: [
						{
							type: "text",
							text: `Project revision ${input.revision} drafted. Human must run: node .pi/governance/cli.ts project approve ${input.revision}`,
						},
					],
					details: {},
				};
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
		},
	});
	pi.registerTool({
		name: "governance_task_create",
		label: "Create project task",
		description:
			"Create or revise a Task under the approved project baseline. A container organizes child Tasks and uses zero budget, concurrency and authority; executable Tasks can be delegated. parentTaskId links work, while dependencies control order. Revisions need fresh approval.",
		parameters: taskSchema,
		async execute(_id, input, _signal, _update, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			try {
				// The bridge may only create internal work or a new revision of an
				// existing task. A revision is always judged as such by the policy,
				// so a lenient internal rule cannot auto-approve a revision.
				const evaluation = kernel.submitTask(
					input as TaskContract,
					`pi:${ctx.sessionManager.getSessionId()}`,
					input.revision > 1 ? "revision" : "internal",
				);
				renderViews(project, kernel);
				// The diagnosis travels with the result: an agent that is told only
				// "awaiting human approval" cannot tell whether the Task needs a
				// baseline revision or simply a signature.
				const remedy = describeDiagnosis(evaluation.diagnosis);
				return {
					content: [
						{
							type: "text",
							text: `Task ${input.taskId} ${evaluation.effect === "auto" ? "authorized under project baseline" : "awaiting human approval"}; rule ${evaluation.ruleId}.${remedy}`,
						},
					],
					details: evaluation,
				};
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
		},
	});
	pi.registerTool({
		name: "governance_task_activate",
		label: "Activate governed task",
		description:
			"Make an approved Task the active governance context of this Main Agent session. Required before governance_delegate and governance_main_deliver. Records the activation in the ledger, so the Main Agent does not need a human to run a slash command.",
		parameters: Type.Object({
			taskId: Type.String(),
			reason: Type.Optional(Type.String()),
		}),
		async execute(_id, input, _signal, _update, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			const state = kernel.getState();
			const fail = (reason: string) => ({
				content: [{ type: "text" as const, text: reason }],
				isError: true,
				details: {},
			});
			if (!state.events.some((event) => event.type === "project.initialized"))
				return fail("Governance is not initialized for this project");
			// Only the Main Agent activates Tasks. A child session is already bound to
			// the Task its Run was started for, and letting it pick another one would
			// break the one-level delegation model. The header answers this before
			// any Run lookup, so the refusal does not depend on the Run being linked.
			if (ctx.sessionManager.getHeader?.()?.parentSession)
				return fail("A child session is bound to its own Task and cannot activate another");
			let origin: ReturnType<typeof resolveSessionOrigin>;
			try {
				origin = resolveSessionOrigin(kernel, ctx);
			} catch (error) {
				return fail(error instanceof Error ? error.message : String(error));
			}
			if (origin.parentRunId !== null)
				return fail("A child session is bound to its own Task and cannot activate another");
			const task = state.tasks[input.taskId];
			if (!task) return fail(`Unknown task ${input.taskId}`);
			if (state.approved[input.taskId] !== task.revision) return fail(`Task ${input.taskId} is not approved`);
			if (state.projectStatus !== "ACTIVE" || !state.projectApproved)
				return fail("An active approved project baseline is required to activate a Task");
			const sessionId = ctx.sessionManager.getSessionId();
			// Activating twice is a no-op rather than a second event: the ledger should
			// show a decision, not the number of times it was repeated.
			if (isTaskActivatedForSession(state, sessionId, input.taskId)) {
				activeTasks.set(sessionId, input.taskId);
				return {
					content: [{ type: "text", text: `Task ${input.taskId} is already active in this session` }],
					details: { taskId: input.taskId, alreadyActive: true },
				};
			}
			kernel.store.append({
				type: "session.task-activated",
				actor: `pi:${sessionId}`,
				taskId: task.taskId,
				runId: null,
				delegationId: null,
				sessionId,
				payload: {
					sessionId,
					source: "main-agent-tool",
					...(input.reason ? { reason: input.reason } : {}),
				},
			});
			activeTasks.set(sessionId, task.taskId);
			currentSession = sessionId;
			return {
				content: [{ type: "text", text: `Task ${task.taskId} is now the active governed Task of this session` }],
				details: { taskId: task.taskId, revision: task.revision },
			};
		},
	});
	pi.registerTool({
		name: "governance_main_deliver",
		label: "Submit main Agent work",
		description:
			"Submit the current HEAD as direct Main Agent work for the active approved Task. Git changes are checked; independent verification and human acceptance remain required.",
		parameters: Type.Object({
			taskId: Type.String(),
			commit: Type.String(),
			summary: Type.String(),
			tests: Type.Array(
				Type.Object({
					command: Type.String(),
					passed: Type.Integer({ minimum: 0 }),
					failed: Type.Integer({ minimum: 0 }),
					logPath: Type.String(),
				}),
			),
			issues: Type.Array(Type.String()),
			logs: Type.Array(Type.String()),
		}),
		async execute(_id, input, _signal, _update, ctx) {
			try {
				const project = primaryWorktree(ctx.cwd);
				const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
				const origin = resolveSessionOrigin(kernel, ctx);
				if (
					origin.parentRunId !== null ||
					!isTaskActivatedForSession(kernel.getState(), origin.sessionId, input.taskId)
				)
					throw new Error("Direct delivery requires the Main Agent's active Task");
				const deliverable = kernel.submitMainDeliverable(input, project, origin);
				renderViews(project, kernel);
				return {
					content: [
						{
							type: "text",
							text: `Direct deliverable ${deliverable.deliverableId} submitted; independent verification and acceptance remain pending`,
						},
					],
					details: { deliverableId: deliverable.deliverableId },
				};
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
		},
	});
	const onCompletion = (payload: unknown) => {
		if (!currentProject) return;
		const native = nativeRunId(payload);
		if (!native) return;
		const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(currentProject)));
		const run = Object.values(kernel.getState().runs).find((item) => item.nativeRunId === native);
		if (!run) {
			pendingCompletions.set(native, payload);
			if (pendingCompletions.size > 100) pendingCompletions.delete(pendingCompletions.keys().next().value ?? native);
			return;
		}
		if (run.state !== "RUNNING") return;
		const record = payload as {
			success?: unknown;
			state?: unknown;
			asyncDir?: unknown;
			results?: { sessionPath?: unknown }[];
		};
		try {
			const childSession = record.results?.find((entry) => typeof entry.sessionPath === "string")?.sessionPath;
			const nativeAsyncDir = typeof record.asyncDir === "string" ? record.asyncDir : run.nativeAsyncDir;
			const nativeStatus = readNativeRunStatus({ ...run, nativeAsyncDir });
			// A completion callback is a notification, not terminal proof. Keeping the
			// Run active preserves its concurrency slot until the native process has
			// recorded a terminal outcome. A missing proof is an observable gap.
			const paused = record.state === "paused" && nativeStatus.available && nativeStatus.state === "paused";
			if (!paused && (nativeStatus.processTerminal !== "observed" || !nativeStatus.terminalOutcome)) {
				const proof = nativeStatus.statusSha256 ?? null;
				if (
					!kernel
						.getState()
						.events.some(
							(event) =>
								event.type === "run.terminal-unverified" &&
								event.runId === run.runId &&
								event.payload.statusSha256 === proof,
						)
				)
					kernel.store.append({
						type: "run.terminal-unverified",
						actor: "pi-subagents",
						taskId: run.taskId,
						runId: run.runId,
						delegationId: run.delegationId,
						payload: {
							nativeState: nativeStatus.state ?? null,
							statusSha256: proof,
							reason: nativeStatus.reason ?? "native terminal proof unavailable",
						},
					});
				renderViews(currentProject, kernel);
				return;
			}
			let next: RunState = paused ? "PAUSED" : (nativeStatus.terminalOutcome ?? "FAILED");
			const modelMatch = nativeStatus.model ? nativeStatus.model === run.routing?.model : null;
			if (modelMatch === false) next = "FAILED";
			// The approved authority is a promise about capability, so a child that
			// launched with more tools than approved must not read as SUCCEEDED.
			// `null` means the native tool set could not be read, which is unknown
			// rather than a pass.
			const approvedTools =
				run.routing?.expectedTools ?? kernel.getState().delegations[run.delegationId]?.authority.tools ?? null;
			const toolCheck = compareNativeTools(
				nativeStatus.nativeTools,
				approvedTools,
				run.routing?.pluginVersion,
				run.routing?.expectedTools !== undefined,
			);
			const toolMatch = toolCheck.match;
			const agentMatch = nativeStatus.nativeAgent ? nativeStatus.nativeAgent === run.routing?.agent : null;
			if (toolMatch === false) next = "FAILED";
			if (agentMatch === false) next = "FAILED";
			kernel.updateRun(
				run.runId,
				next,
				{
					nativeAsyncDir,
					sessionRef:
						typeof childSession === "string" ? childSession : (nativeStatus.sessionFile ?? run.sessionRef),
					usageTokens: nativeStatus.totalTokens ?? run.usageTokens,
					costUsd: nativeStatus.costUsd ?? run.costUsd,
				},
				modelMatch === false
					? "Native model differs from approved route"
					: toolMatch === false
						? `Native child tools differ from approved configuration: ${nativeStatus.nativeTools?.join(", ") ?? "unknown"}`
						: agentMatch === false
							? "Native Agent differs from delegated Agent"
							: undefined,
				"pi-subagents",
				{
					requestedModel: run.routing?.model ?? null,
					observedModel: nativeStatus.model ?? null,
					modelEvidenceSource: nativeStatus.modelEvidenceSource ?? null,
					sessionSha256: nativeStatus.sessionSha256 ?? null,
					modelMatch,
					approvedTools,
					nativeTools: nativeStatus.nativeTools ?? null,
					toolEscalation: toolMatch === false ? toolCheck.escalation : null,
					nativeInternalTools: toolCheck.internalTools,
					nativeExecutionTools: toolCheck.executionTools,
					toolMatch,
					policyDigest: run.routing?.policyDigest ?? null,
					nativeAgent: nativeStatus.nativeAgent ?? null,
					agentMatch,
					pluginVersion: run.routing?.pluginVersion ?? null,
					compliance:
						toolMatch === false || modelMatch === false || agentMatch === false
							? "mismatch"
							: toolMatch === null || modelMatch === null || agentMatch === null
								? "unknown"
								: "verified",
				},
			);
			if (next !== "PAUSED" && run.workspaceId && nativeStatus.processTerminal === "observed")
				kernel.releaseWorkspace(run.workspaceId, run.runId, "pi-subagents", `process-terminal:${native}`);
			renderViews(currentProject, kernel);
		} catch (error) {
			console.error("Governance completion reconciliation failed:", error);
		}
	};
	pi.events.on("subagent:async-complete", onCompletion);
	pi.events.on("subagent:process-terminal", (payload) => {
		// A process-terminal notification can arrive after an earlier completion
		// callback that lacked proof. Revisit the Run now that the proof may exist.
		onCompletion(payload);
		if (!currentProject) return;
		const native = nativeRunId(payload);
		if (!native) return;
		const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(currentProject)));
		const run = Object.values(kernel.getState().runs).find((entry) => entry.nativeRunId === native);
		if (!run?.workspaceId || !["SUCCEEDED", "FAILED", "CANCELLED"].includes(run.state)) return;
		if (readNativeRunStatus(run).processTerminal !== "observed") return;
		const workspace = kernel.getState().workspaces[run.workspaceId];
		if (workspace?.holderRunId !== run.runId) return;
		try {
			kernel.releaseWorkspace(run.workspaceId, run.runId, "pi-subagents", `process-terminal:${native}`);
			renderViews(currentProject, kernel);
		} catch (error) {
			console.error("Governance workspace release reconciliation failed:", error);
		}
	});

	pi.registerTool({
		name: "governance_delegate",
		label: "Governed delegation",
		description:
			"Start one child Agent from the current Main Pi session for an approved Task. Child sessions cannot delegate again. Parent identity comes from the current Pi session; a non-null parentRunId is refused. V2 requires an approved policy and allows modelProfile per Agent; V1 uses contextTier.",
		parameters: params,
		async execute(_toolCallId, input, signal, _onUpdate, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			const state = kernel.getState();
			if (!state.events.some((event) => event.type === "project.initialized"))
				return {
					content: [{ type: "text", text: "Governance is not initialized for this project" }],
					isError: true,
					details: {},
				};
			if (!state.projectApproved || state.projectStatus !== "ACTIVE")
				return {
					content: [{ type: "text", text: "An active approved project baseline is required for delegation" }],
					isError: true,
					details: {},
				};
			const task = state.tasks[input.taskId];
			if (!task || state.approved[input.taskId] !== task.revision)
				return {
					content: [{ type: "text", text: `Task ${input.taskId} is not approved` }],
					isError: true,
					details: {},
				};
			let origin: ReturnType<typeof resolveSessionOrigin>;
			try {
				origin = resolveSessionOrigin(kernel, ctx);
				if (origin.parentRunId !== null)
					throw new Error("Child Agent delegation is disabled in the one-level model");
				if (origin.taskId && origin.taskId !== input.taskId)
					throw new Error(`Child session is bound to Task ${origin.taskId}, not ${input.taskId}`);
				if (input.parentRunId !== undefined && input.parentRunId !== origin.parentRunId)
					throw new Error("Supplied parentRunId differs from the current Pi session binding");
				if (origin.taskId) activateChildSession(kernel, ctx);
			} catch (error) {
				const reason = error instanceof Error ? error.message : String(error);
				kernel.store.append({
					type: "delegation.rejected",
					actor: `pi:${ctx.sessionManager.getSessionId()}`,
					taskId: input.taskId,
					runId: null,
					delegationId: null,
					sessionId: ctx.sessionManager.getSessionId(),
					payload: { reason, requestedParentRunId: input.parentRunId ?? null, source: "session-identity" },
				});
				return { content: [{ type: "text", text: `Delegation denied: ${reason}` }], isError: true, details: {} };
			}
			if (!isTaskActivatedForSession(kernel.getState(), ctx.sessionManager.getSessionId(), input.taskId))
				return {
					content: [
						{
							type: "text",
							text: `Activate approved Task ${input.taskId} with governance_task_activate before delegating`,
						},
					],
					isError: true,
					details: {},
				};
			let routing: ReturnType<typeof loadSubagentPolicy>;
			try {
				routing = loadSubagentPolicy(project);
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
			const policyStatus = subagentPolicyStatus(project, state);
			if (
				routing.policy.version === 3 &&
				(policyStatus.mode !== "v3" || !policyStatus.synchronized || policyStatus.conflict)
			)
				return {
					content: [
						{
							type: "text",
							text: "V3 Subagent policy is not synchronized; run policy sync and inspect policy show",
						},
					],
					isError: true,
					details: {},
				};
			if (routing.policy.version !== 1 && !policyStatus.approved)
				return {
					content: [
						{
							type: "text",
							text: "Subagent policy changed or is unapproved; run policy show, then policy approve",
						},
					],
					isError: true,
					details: {},
				};
			const agent = input.agent ?? (routing.policy.version === 2 ? routing.policy.defaultAgent : "");
			let route: ReturnType<typeof resolveSubagentRoute>;
			try {
				if (!agent) throw new Error("Delegation requires an explicit Agent");
				route = resolveSubagentRoute(routing, agent, input.modelProfile, input.contextTier);
				if (routing.policy.version === 3) {
					const tools = routing.policy.agents[agent].tools;
					const projectTools = state.projectApproved?.authority.tools ?? [];
					const taskTools = task.authority.tools;
					const excess = tools.filter(
						(tool) => !projectTools.includes(tool) || !taskTools.includes(tool) || !input.tools.includes(tool),
					);
					if (excess.length)
						throw new Error(`Agent ${agent} tools exceed Task/Delegation authority: ${excess.join(", ")}`);
				}
				const available = ctx.modelRegistry
					.getAll()
					.some((model) => `${model.provider}/${model.id}` === route.model);
				if (!available) throw new Error(`Model ${route.model} is not registered in this Pi project`);
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
			try {
				renderViews(project, kernel);
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
			const authority: Authority = {
				paths: input.paths,
				tools: input.tools,
				readRepository: input.readRepository,
				writeWorkspace: input.writeWorkspace,
				commitBranch: input.commitBranch,
				integrateBranch: input.integrateBranch,
			};
			const workspace = input.workspaceId ? kernel.getState().workspaces[input.workspaceId] : undefined;
			if (input.writeWorkspace && !workspace)
				return {
					content: [{ type: "text", text: "Writable delegation requires a registered workspaceId" }],
					isError: true,
					details: {},
				};
			if (workspace) verifyTakeover(workspace, kernel);
			// Capabilities come from the role's template, not from a constant. Registering
			// every subagent as `executor / delegated-work` made worker and reviewer
			// indistinguishable in the ledger, so "may this Run verify a delivery" had no
			// answer to look up. An unknown role gets `delegated-work` only: not trusted
			// with verification just because it was named somewhere.
			const declared = capabilitiesOf(agent);
			const capabilities = declared ?? ["delegated-work"];
			const existing = kernel.getState().agents[agent];
			if (!existing)
				kernel.registerAgent(
					{
						agentId: agent,
						harness: "pi",
						role: capabilities.includes("verify") ? "reviewer" : "executor",
						capabilities,
					},
					`pi:${ctx.sessionManager.getSessionId()}`,
				);
			else if (capabilities.some((capability) => !existing.capabilities.includes(capability)))
				// Registered before capabilities came from the template. The earlier record
				// cannot be edited (append-only), so the grant is appended as its own fact and
				// readers take the latest.
				kernel.grantCapabilities(agent, capabilities, `pi:${ctx.sessionManager.getSessionId()}`);
			kernel.store.append({
				type: "delegation.requested",
				actor: `pi:${ctx.sessionManager.getSessionId()}`,
				taskId: input.taskId,
				runId: origin.parentRunId,
				delegationId: null,
				sessionId: origin.sessionId,
				payload: {
					requesterSessionFile: origin.sessionFile,
					agent,
					objective: input.objective,
					retryOf: input.retryOf ?? null,
					modelProfile: route.modelProfile,
					resolvedModel: route.model,
					policyDigest: route.policyDigest,
					maxAllocationTokens: route.maxAllocationTokens,
					timeoutMs: route.timeoutMs,
				},
			});
			let delegation: Delegation;
			try {
				if (input.retryOf) {
					const prior = kernel.getState().runs[input.retryOf];
					const previous = prior && kernel.getState().delegations[prior.delegationId];
					if (
						!previous ||
						prior.taskId !== input.taskId ||
						previous.executorId !== agent ||
						previous.parentRunId !== origin.parentRunId ||
						previous.requesterSessionId !== origin.sessionId ||
						previous.requesterSessionFile !== origin.sessionFile ||
						JSON.stringify(previous.authority) !== JSON.stringify(authority) ||
						previous.budgetTokens !== input.budgetTokens
					)
						throw new Error("Retry must reuse the same delegation contract");
					delegation = previous;
				} else {
					delegation = kernel.authorizeDelegation(
						{
							taskId: input.taskId,
							parentRunId: origin.parentRunId,
							executorId: agent,
							objective: input.objective,
							authority,
							budgetTokens: input.budgetTokens,
						},
						`pi:${ctx.sessionManager.getSessionId()}`,
						origin,
					);
				}
			} catch (error) {
				kernel.store.append({
					type: "delegation.rejected",
					actor: `pi:${ctx.sessionManager.getSessionId()}`,
					taskId: input.taskId,
					runId: origin.parentRunId,
					delegationId: null,
					payload: { reason: error instanceof Error ? error.message : String(error), agent },
				});
				if (kernel.getState().tasks[input.taskId])
					kernel.requestDecision(
						input.taskId,
						"scope",
						`Review rejected delegation to ${agent}: ${error instanceof Error ? error.message : String(error)}`,
						`pi:${ctx.sessionManager.getSessionId()}`,
					);
				return {
					content: [
						{
							type: "text",
							text: `Delegation denied: ${error instanceof Error ? error.message : String(error)}`,
						},
					],
					isError: true,
					details: {},
				};
			}
			let run: ReturnType<GovernanceKernel["createRun"]>;
			try {
				run = kernel.createRun(
					delegation.delegationId,
					"pi",
					null,
					workspace?.workspaceId ?? null,
					input.retryOf ?? null,
					origin.sessionFile,
					{
						model: route.model,
						agent,
						modelProfile: route.modelProfile,
						tier: route.legacyTier ?? undefined,
						contextTokens: route.contextTokens,
						policyDigest: route.policyDigest,
						maxConcurrent: route.maxConcurrent,
						roleMaxConcurrent: route.roleMaxConcurrent,
						maxRunsPerTask: route.maxRunsPerTask,
						maxAllocationTokens: route.maxAllocationTokens,
						timeoutMs: route.timeoutMs,
						...(routing.policy.version === 3
							? {
									expectedTools: routing.policy.agents[agent].tools,
									approvalDigest: policyStatus.mode === "v3" ? policyStatus.approvalDigest : undefined,
									pluginVersion: policyStatus.mode === "v3" ? policyStatus.pluginVersion : undefined,
								}
							: {}),
					},
				);
			} catch (error) {
				if (!input.retryOf)
					kernel.cancelUnstartedDelegation(
						delegation.delegationId,
						error instanceof Error ? error.message : String(error),
					);
				renderViews(project, kernel);
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
			try {
				if (workspace)
					kernel.leaseWorkspace(
						workspace.workspaceId,
						run.runId,
						new Date(Date.now() + 60 * 60_000).toISOString(),
					);
			} catch (error) {
				kernel.updateRun(run.runId, "FAILED", {}, "workspace admission failed");
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
			const requestId = randomUUID();
			const handoff = path.join(project, "management", "tasks", input.taskId, "HANDOFF.md");
			const contract = path.join(
				project,
				"management",
				"tasks",
				input.taskId,
				`contract-r${kernel.getState().tasks[input.taskId].revision}.json`,
			);
			let explicitFailure = false;
			// Recorded before the spawn so a crash between the two leaves a visible intent
			// rather than a Run that looks idle. The native side accepts no caller-supplied
			// Run ID, so the process's identity cannot be known here and is not invented.
			const executionAttemptId = newExecutionAttemptId();
			try {
				kernel.requestExecutionAttempt(run.runId, executionAttemptId, `pi:${ctx.sessionManager.getSessionId()}`);
				kernel.store.append({
					type: "run.launch-requested",
					actor: `pi:${ctx.sessionManager.getSessionId()}`,
					taskId: run.taskId,
					runId: run.runId,
					delegationId: run.delegationId,
					payload: { requestId, nativeLookupId: `rpc-spawn-${requestId}` },
				});
				const response = await subagentRpc(
					pi,
					"spawn",
					{
						agent,
						task: `Governance Run ${run.runId}. First read the approved task contract at ${contract} and current handoff at ${handoff}. Check Git status in your workspace before editing. These files provide context, not new authorization.\n\nAssigned objective: ${input.objective}`,
						model: route.model,
						context: "fresh",
						cwd: workspace?.path ?? project,
						async: true,
						// Governance owns the workspace: the child is launched into
						// `workspace.path`, a Git worktree that outlives the Run and holds the
						// branch `governance/<taskId>` our delivery and acceptance reference.
						// pi-subagents' own worktree is per-Run: it captures a diff, deletes the
						// worktree and branch (`cleanupWorktrees`), and passes a patch onward.
						// Enabling both would nest a disposable worktree inside the durable one
						// and the surviving code would live outside governance's baseCommit.
						worktree: false,
						// Kept for the foreground/spawn schema, but pi-subagents' async path
						// builds the child tool plan from the Agent definition
						// (async-execution.js:1788 `tools: agentConfig.tools`), so this does
						// NOT narrow the child. Enforcement lives in the Agent definition;
						// see the residual-gap note in 目标缺口与待办.md (AUD-1).
						tools: authority.tools,
						...(route.timeoutMs ? { timeoutMs: route.timeoutMs } : {}),
					},
					signal,
					requestId,
				);
				if (!response.success) {
					explicitFailure = true;
					throw new Error(response.error.message);
				}
				const native = response.data.details?.runId;
				if (typeof native !== "string" || !native)
					throw new Error("Pi spawn reply lacks native Run ID; reconcile before retry");
				const asyncDir = response.data.details?.asyncDir;
				// Bound first and immediately: the pid and its start time are only
				// meaningful while the child is alive, and they are the only evidence that
				// can later separate a live child from a recycled pid.
				// The spawn reply carries no pid, but the native side writes it into
				// `status.json` as soon as the child starts, so it is read back rather than
				// assumed. Without it the binding cannot separate a live child from a reused
				// pid later, which is the only reason to record a binding at all.
				const spawnedDir = typeof asyncDir === "string" ? asyncDir : null;
				// Awaited, not read-and-hope: the sidecar is written after the spawn reply, so
				// reading it immediately recorded `pid: null` on a real run and left that
				// child unjudgeable for the rest of its life.
				const pid = await awaitNativePid(spawnedDir);
				const binding = kernel.bindExecutionAttempt(
					run.runId,
					executionAttemptId,
					{ nativeRunId: native, pid },
					`pi:${ctx.sessionManager.getSessionId()}`,
				);
				if (!binding.bound)
					// Worth surfacing rather than ignoring: it means the intent was lost, so
					// this Run's process identity is unrecorded and any later orphan probe
					// will have to fall back to UNKNOWN.
					process.stderr.write(`governance: execution attempt not bound: ${binding.reason ?? "unknown"}\n`);
				kernel.updateRun(run.runId, "RUNNING", {
					nativeRunId: native,
					nativeAsyncDir: typeof asyncDir === "string" ? asyncDir : null,
				});
				if (routing.policy.version === 3) {
					const observed = readNativeRunStatus(kernel.getState().runs[run.runId]);
					const expectedTools = routing.policy.agents[agent].tools;
					const toolCheck = compareNativeTools(
						observed.nativeTools,
						expectedTools,
						policyStatus.mode === "v3" ? policyStatus.pluginVersion : undefined,
						true,
					);
					kernel.store.append({
						type: "run.config-observed",
						actor: "pi-subagents",
						taskId: run.taskId,
						runId: run.runId,
						delegationId: run.delegationId,
						payload: {
							pluginVersion: policyStatus.mode === "v3" ? policyStatus.pluginVersion : null,
							expectedTools,
							nativeTools: observed.nativeTools ?? null,
							nativeInternalTools: toolCheck.internalTools,
							nativeExecutionTools: toolCheck.executionTools,
							observation: observed.nativeTools ? "observed" : "unknown",
							toolMatch: toolCheck.match,
						},
					});
				}
				kernel.store.append({
					type: "agent.instance-observed",
					actor: "pi-subagents",
					taskId: run.taskId,
					runId: run.runId,
					delegationId: run.delegationId,
					sessionId: ctx.sessionManager.getSessionId(),
					payload: {
						agentInstanceId: `pi-run:${native}`,
						agentDefinitionId: agent,
						nativeRunId: native,
						parentRunId: origin.parentRunId,
					},
				});
				const earlyCompletion = pendingCompletions.get(native);
				if (earlyCompletion) {
					pendingCompletions.delete(native);
					onCompletion(earlyCompletion);
				}
				renderViews(project, kernel);
				return {
					content: [
						{
							type: "text",
							text: `Governance Run ${run.runId}; Pi Run ${native}; Agent ${agent}; model ${route.model}; profile ${route.modelProfile ?? route.legacyTier}; workspace ${workspace?.path ?? "read-only"}`,
						},
					],
					details: { runId: run.runId, nativeRunId: native, delegationId: delegation.delegationId },
				};
			} catch (error) {
				if (kernel.getState().runs[run.runId]?.state === "CREATED") {
					kernel.updateRun(run.runId, explicitFailure ? "FAILED" : "INTERRUPTED");
					if (explicitFailure && workspace)
						kernel.releaseWorkspace(
							workspace.workspaceId,
							run.runId,
							"pi-subagents",
							"RPC spawn rejected before launch",
						);
				}
				renderViews(project, kernel);
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
		},
	});

	const controlNativeRun = async (
		runId: string,
		action: "status" | "steer" | "interrupt" | "stop" | "resume",
		message: string | undefined,
		actor: string,
		ctx: ExtensionContext,
		signal?: AbortSignal,
	) => {
		const project = primaryWorktree(ctx.cwd);
		const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
		const run = kernel.getState().runs[runId];
		if (!run?.nativeRunId) throw new Error("Governed Run has no known native Pi Run ID");
		if ((action === "resume" || action === "steer") && !message?.trim())
			throw new Error(`${action} requires a message`);
		if (action !== "status") {
			if (action === "steer") {
				if (run.state !== "RUNNING") throw new Error("Only running Runs can be steered");
				kernel.store.append({
					type: "run.control-requested",
					actor,
					taskId: run.taskId,
					runId,
					delegationId: run.delegationId,
					payload: {
						action,
						messageSha256: createHash("sha256")
							.update(message ?? "")
							.digest("hex"),
					},
				});
			} else {
				kernel.controlRun(runId, action === "interrupt" ? "pause" : action === "stop" ? "cancel" : "resume", actor);
			}
		}
		let outcome: "acknowledged" | "rejected" | "unknown" = "unknown";
		try {
			const response = await subagentRpc(
				pi,
				action,
				{ id: run.nativeRunId, ...(message ? { message } : {}) },
				signal,
			);
			if (!response.success) {
				outcome = "rejected";
				throw new Error(response.error.message);
			}
			if (action === "resume") {
				const resumedNative = response.data.details?.runId;
				if (typeof resumedNative !== "string" || !resumedNative)
					throw new Error("Resume acknowledgement lacks native Run ID; reconcile before another control action");
				kernel.updateRun(runId, "RUNNING", {
					nativeRunId: resumedNative,
					nativeAsyncDir:
						typeof response.data.details?.asyncDir === "string"
							? response.data.details.asyncDir
							: run.nativeAsyncDir,
				});
			}
			outcome = "acknowledged";
			return {
				text: response.data.text ?? JSON.stringify(response.data.details ?? response.data),
				native: readNativeRunStatus(kernel.getState().runs[runId]),
			};
		} finally {
			if (action !== "status") {
				kernel.store.append({
					type: "run.control-result",
					actor: "pi-subagents",
					taskId: run.taskId,
					runId,
					delegationId: run.delegationId,
					payload: { action, outcome, nativeRunId: run.nativeRunId },
				});
				renderViews(project, kernel);
			}
		}
	};

	pi.registerTool({
		name: "governance_control",
		label: "Governed Run control",
		description: "Query, steer, interrupt, stop, or resume a governed Pi Run. Acknowledgement is not terminal proof.",
		parameters: Type.Object({
			runId: Type.String(),
			action: Type.Union([
				Type.Literal("status"),
				Type.Literal("steer"),
				Type.Literal("interrupt"),
				Type.Literal("stop"),
				Type.Literal("resume"),
			]),
			message: Type.Optional(Type.String()),
		}),
		async execute(_toolCallId, input, signal, _onUpdate, ctx) {
			try {
				const result = await controlNativeRun(
					input.runId,
					input.action,
					input.message,
					`pi:${ctx.sessionManager.getSessionId()}`,
					ctx,
					signal,
				);
				return {
					content: [{ type: "text", text: `${result.text}\n${JSON.stringify(result.native)}` }],
					details: result.native,
				};
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
		},
	});

	pi.registerTool({
		name: "governance_state",
		label: "Governance state",
		description: "Read approved tasks, Run states, workspaces, pending decisions, and verification records.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _input, _signal, _onUpdate, ctx) {
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(ctx.cwd)));
			const state = kernel.getState();
			return {
				content: [
					{
						type: "text",
						text: JSON.stringify(
							{
								agents: state.agents,
								projectDraft: state.projectDraft,
								projectApproved: state.projectApproved,
								projectStatus: state.projectStatus,
								tasks: state.tasks,
								approved: state.approved,
								runs: state.runs,
								delegations: state.delegations,
								workspaces: state.workspaces,
								pendingDecisions: Object.values(state.decisions).filter(
									(decision) => decision.result === "pending",
								),
								deliverables: state.deliverables,
								verifications: state.verifications,
								accepted: state.accepted,
							},
							null,
							2,
						),
					},
				],
				details: {},
			};
		},
	});

	// Nothing told the operator which governance tools and commands exist: the names
	// only appear in this file, so asking for one that does not exist ("governance
	// stage") looked identical to the extension having failed to load. A single
	// discoverable answer is cheaper than a directory listing in a doc nobody opens.
	pi.registerCommand("gov", {
		description: "List the governance tools and commands available in this session: /gov",
		handler: async (_args, ctx) => {
			const project = primaryWorktree(ctx.cwd);
			const state = new GovernanceKernel(new GovernanceStore(dataRoot(project))).getState();
			const projectId =
				state.events.find((event) => event.type === "project.initialized")?.payload.projectId ?? "未初始化";
			ctx.ui.notify(
				[
					`项目 ${projectId} · ${state.projectStatus}`,
					"",
					"工具（由 Agent 调用，不是斜杠命令）：",
					"  governance_state          查看项目与 Task 状态",
					"  governance_project_draft  提交项目基线草稿",
					"  governance_task_create    创建 Task（容器或可执行）",
					"  governance_task_activate  在本会话激活已批准 Task",
					"  governance_delegate       委派 Child Agent 执行 Run",
					"  governance_main_deliver   Main 直接交付",
					"  governance_control        暂停/收尾/重置/归档等项目操作",
					"",
					"命令：",
					"  /gov            本说明",
					"  /gov-task       /gov-task <task-id> 激活已批准 Task",
					"  /gov-run        /gov-run <run-id> 查看 Run",
					"  /gov-reset      /gov-reset <project-id> <reason>",
					"  /gov-archive    /gov-archive <project-id> <reason>",
					"",
					"引导命令（由用户级扩展注册，项目未安装时也可用）：",
					"  /gov-source     当前会用哪份源码；包含命中的优先级层级",
					"  /gov-init       /gov-init [源码目录] 在尚无治理的仓库初始化",
					"  /gov-upgrade    /gov-upgrade [源码目录] 升级已安装副本（需重启生效）",
					"",
					"没有 governance stage 这类名字；工具名以上面这张表为准。",
				].join("\n"),
				"info",
			);
		},
	});
	pi.registerCommand("gov-task", {
		description: "Activate an approved governed task in this Pi session: /gov-task <task-id>",
		handler: async (taskId, ctx) => {
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(ctx.cwd)));
			const origin = resolveSessionOrigin(kernel, ctx);
			if (origin.taskId && origin.taskId !== taskId.trim())
				throw new Error(`Child session is bound to Task ${origin.taskId}`);
			const task = kernel.getState().tasks[taskId.trim()];
			if (!task || kernel.getState().approved[task.taskId] !== task.revision)
				throw new Error("Task is not approved");
			const session = ctx.sessionManager.getSessionId();
			activeTasks.set(session, task.taskId);
			currentSession = session;
			kernel.store.append({
				type: "session.task-activated",
				actor: `pi:${currentSession}`,
				taskId: task.taskId,
				runId: null,
				delegationId: null,
				payload: { sessionId: currentSession },
			});
			ctx.ui.notify(`Governed task active: ${task.taskId}`, "info");
		},
	});
	// Project settings from inside Pi. Both print what they will do and require the
	// project id as an explicit second argument, mirroring the CLI: a slash command
	// with one word of confirmation is too easy to fire by accident.
	pi.registerCommand("gov-reset", {
		description:
			"Revoke the current governance baseline, authority and policy approval, keeping all history: /gov-reset <project-id> <reason>",
		handler: async (args, ctx) => {
			const [projectIdArgument, ...reasonWords] = args.trim().split(/\s+/);
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			const initialized = kernel.getState().events.find((event) => event.type === "project.initialized");
			const projectId =
				typeof initialized?.payload.projectId === "string" ? initialized.payload.projectId : "(none)";
			if (!projectIdArgument) throw new Error(`Usage: /gov-reset <project-id> <reason>. Project id: ${projectId}`);
			const event = kernel.resetProject({
				actor: `pi-ui:${ctx.sessionManager.getSessionId()}`,
				reason: reasonWords.join(" ").trim(),
				confirm: projectIdArgument,
			});
			renderViews(project, kernel);
			ctx.ui.notify(
				`Governance reset (sequence ${event.sequence}). History kept; submit a new baseline and approve it.`,
				"info",
			);
		},
	});
	pi.registerCommand("gov-archive", {
		description:
			"Archive the current Tasks, Runs, deliveries and acceptances so the workspace starts empty: /gov-archive <project-id> <reason>",
		handler: async (args, ctx) => {
			const [projectIdArgument, ...reasonWords] = args.trim().split(/\s+/);
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			const initialized = kernel.getState().events.find((event) => event.type === "project.initialized");
			const projectId =
				typeof initialized?.payload.projectId === "string" ? initialized.payload.projectId : "(none)";
			if (!projectIdArgument) throw new Error(`Usage: /gov-archive <project-id> <reason>. Project id: ${projectId}`);
			const event = kernel.archiveHistory({
				actor: `pi-ui:${ctx.sessionManager.getSessionId()}`,
				reason: reasonWords.join(" ").trim(),
				confirm: projectIdArgument,
			});
			renderViews(project, kernel);
			ctx.ui.notify(`Work archived as ${String(event.payload.archiveId)}. See management/ARCHIVE.md.`, "info");
		},
	});
	pi.registerCommand("gov-run", {
		description:
			"Inspect or control a governed child: /gov-run status|steer|interrupt|stop|resume <run-id> [message]",
		handler: async (args, ctx) => {
			const [action, runId, ...words] = args.trim().split(/\s+/);
			if (!runId || !["status", "steer", "interrupt", "stop", "resume"].includes(action))
				throw new Error("Usage: /gov-run status|steer|interrupt|stop|resume <run-id> [message]");
			const result = await controlNativeRun(
				runId,
				action as "status" | "steer" | "interrupt" | "stop" | "resume",
				words.join(" ") || undefined,
				`pi-ui:${ctx.sessionManager.getSessionId()}`,
				ctx,
			);
			ctx.ui.notify(`${runId}: ${result.native.state ?? result.text}`, "info");
		},
	});
}
