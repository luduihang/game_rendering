import { execFileSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { markRefusalRecorded, refusalOf, refusalPayload } from "./redline.ts";
import type {
	EventActor,
	EventContext,
	EventSubject,
	GovernanceEvent,
	GovernanceEventInput,
	GovernanceState,
	ProjectArchive,
	ProjectContract,
} from "./types.ts";

type GovernanceEventV1 = {
	eventId: string;
	sequence: number;
	type: string;
	time: string;
	actor: string;
	taskId: string | null;
	runId: string | null;
	delegationId: string | null;
	payload: Record<string, unknown>;
};

type StoredGovernanceEventV2 = Omit<GovernanceEvent, "type" | "time" | "taskId" | "runId" | "delegationId">;

function canonicalJson(value: unknown): string {
	if (value === undefined) return "null";
	if (value === null || typeof value !== "object") return JSON.stringify(value);
	if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
	const record = value as Record<string, unknown>;
	return `{${Object.keys(record)
		.filter((key) => record[key] !== undefined)
		.sort()
		.map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`)
		.join(",")}}`;
}

function digest(value: unknown): string {
	return `sha256:${createHash("sha256").update(canonicalJson(value)).digest("hex")}`;
}

/**
 * Read a stored actor string as an actor.
 *
 * `local:<user>` used to be returned as `kind: "human"`, which meant any writer able to
 * type that prefix - including an agent invoking the CLI - produced a record claiming a
 * human had acted. The prefix says which OS account ran the process; it says nothing about
 * whether a person was at the keyboard, so the kind is `agent` and the assurance is
 * whatever the prefix can actually support.
 *
 * `web:` stays unverified for the same reason: reaching an HTTP endpoint is not identity.
 * Historic events keep their stored strings; this only changes how they are read.
 */
function actorFromLegacy(value: string): EventActor {
	const session = value.match(/^(?:pi-session|pi|pi-ui):(.+)$/)?.[1] ?? null;
	// `agent-run:<runId>` is the identity the resolution mechanism produces for a governed
	// Run: the ledger holds that Run, so the actor is identified by an execution it recorded.
	const governedRun = value.match(/^agent-run:(.+)$/)?.[1] ?? null;
	if (governedRun)
		return {
			kind: "agent",
			id: value,
			authenticatedBy: "governance",
			agentDefinitionId: null,
			agentInstanceId: null,
			sessionId: null,
			runId: governedRun,
		};
	if (value.startsWith("local:") || value.startsWith("web:"))
		return {
			// Not `human`. The account name is real; the person behind it is not established.
			kind: "agent",
			id: value,
			authenticatedBy: value.startsWith("web:") ? "unverified" : "os-user",
			agentDefinitionId: null,
			agentInstanceId: null,
			sessionId: null,
			runId: null,
		};
	if (session)
		return {
			kind: "agent",
			id: value,
			authenticatedBy: "pi-session",
			agentDefinitionId: value.startsWith("pi-session:") ? "coordinator" : null,
			agentInstanceId: `pi-session:${session}`,
			sessionId: session,
			runId: null,
		};
	if (value === "governance")
		return {
			kind: "system",
			id: value,
			authenticatedBy: "governance",
			agentDefinitionId: null,
			agentInstanceId: null,
			sessionId: null,
			runId: null,
		};
	if (value === "pi-subagents")
		return {
			kind: "plugin",
			id: value,
			authenticatedBy: "plugin",
			agentDefinitionId: null,
			agentInstanceId: null,
			sessionId: null,
			runId: null,
		};
	return {
		kind: "unknown",
		id: value,
		authenticatedBy: "unverified",
		agentDefinitionId: null,
		agentInstanceId: null,
		sessionId: null,
		runId: null,
	};
}

function subjectFor(
	eventType: string,
	projectId: string | null,
	context: EventContext,
	payload: Record<string, unknown>,
): EventSubject {
	const value = payload.value && typeof payload.value === "object" ? (payload.value as Record<string, unknown>) : {};
	if (eventType.startsWith("governance.project.") && projectId) return { type: "project", id: projectId };
	if (
		(eventType === "governance.agent.registered" || eventType === "governance.agent.capabilities-granted") &&
		typeof value.agentId === "string"
	)
		return { type: "agent", id: value.agentId };
	if (eventType.startsWith("governance.task.") && context.taskId) return { type: "task", id: context.taskId };
	if (eventType.startsWith("governance.session.task-") && context.taskId) return { type: "task", id: context.taskId };
	if (eventType.startsWith("governance.delegation.") && context.delegationId)
		return { type: "delegation", id: context.delegationId };
	if (eventType.startsWith("governance.run.") && context.runId) return { type: "run", id: context.runId };
	if (eventType.startsWith("governance.workspace.") && typeof value.workspaceId === "string")
		return { type: "workspace", id: value.workspaceId };
	if (eventType === "governance.deliverable.submitted" && typeof value.deliverableId === "string")
		return { type: "deliverable", id: value.deliverableId };
	if (eventType === "governance.verification.recorded" && typeof value.verificationId === "string")
		return { type: "verification", id: value.verificationId };
	const candidates: [string, unknown][] = [
		["verification", value.verificationId ?? payload.verificationId],
		["deliverable", value.deliverableId],
		["decision", value.decisionId ?? payload.decisionId],
		["workspace", value.workspaceId],
		["run", context.runId],
		["delegation", context.delegationId],
		["task", context.taskId],
		["agent", value.agentId],
		["project", projectId],
	];
	for (const [type, id] of candidates) if (typeof id === "string" && id) return { type, id };
	return { type: "event", id: eventType };
}

function namespacedEventType(type: string, namespace = "governance"): string {
	return type.startsWith(`${namespace}.`) ? type : `${namespace}.${type}`;
}

function normalizeLegacyPayload(event: GovernanceEventV1): Record<string, unknown> {
	if (event.type !== "delegation.authorized" || !event.payload.value || typeof event.payload.value !== "object")
		return event.payload;
	const value = event.payload.value as Record<string, unknown>;
	return {
		...event.payload,
		value: {
			...value,
			parentDelegationId: value.parentDelegationId ?? null,
			requesterId: value.requesterId ?? event.actor,
		},
	};
}

function withCompatibilityAliases(event: StoredGovernanceEventV2): GovernanceEvent {
	const normalized = event as GovernanceEvent;
	Object.defineProperties(normalized, {
		type: {
			value: event.eventType.startsWith("governance.")
				? event.eventType.slice("governance.".length)
				: event.eventType,
			enumerable: false,
		},
		time: { value: event.recordedAt, enumerable: false },
		taskId: { value: event.context.taskId, enumerable: false },
		runId: { value: event.context.runId, enumerable: false },
		delegationId: { value: event.context.delegationId, enumerable: false },
	});
	return normalized;
}

export function dataRoot(repo: string): string {
	const common = execFileSync("git", ["rev-parse", "--path-format=absolute", "--git-common-dir"], {
		cwd: repo,
		encoding: "utf8",
	}).trim();
	return path.join(common, "agent-governance-v0.1");
}

export function primaryWorktree(repo: string): string {
	// stderr is captured rather than inherited: callers include hooks that run
	// against whatever directory a session happens to be in, and git's own
	// "not a git repository" line would otherwise print inside the TUI where it
	// looks like the application failed rather than one probe returning nothing.
	let listing: string;
	try {
		listing = execFileSync("git", ["worktree", "list", "--porcelain"], {
			cwd: repo,
			encoding: "utf8",
			stdio: ["ignore", "pipe", "pipe"],
		});
	} catch (error) {
		const reason = (error as { stderr?: string }).stderr?.trim();
		throw new Error(reason ? `No primary Git worktree found: ${reason}` : "No primary Git worktree found");
	}
	const first = listing.split("\n").find((line) => line.startsWith("worktree "));
	if (!first) throw new Error("No primary Git worktree found");
	return first.slice("worktree ".length);
}

export function emptyState(): GovernanceState {
	return {
		projectDraft: null,
		projectApproved: null,
		projectRejectedRevision: null,
		projectStatus: "DRAFT",
		agents: {},
		tasks: {},
		approved: {},
		delegations: {},
		runs: {},
		workspaces: {},
		decisions: {},
		deliverables: {},
		verifications: {},
		accepted: {},
		cancelled: {},
		archives: {},
		archiveOrder: [],
		archiveBoundary: 0,
		workspaceArchiveBoundary: 0,
		resetBoundary: 0,
		projectRevisionFloor: 0,
		events: [],
	};
}

/**
 * Record the archive operation, then move every current record into it.
 *
 * The move is what makes the archive a boundary rather than a feature flag:
 * folding is deterministic, so replaying the ledger leaves the same records on
 * the current side and the same records in the archive. Nothing is removed from
 * `state.events`; the ledger stays the complete history.
 */
function foldArchive(state: GovernanceState, event: GovernanceEvent): void {
	const archiveId = typeof event.payload.archiveId === "string" ? event.payload.archiveId : null;
	if (!archiveId || state.archives[archiveId]) return;
	const records = {
		tasks: state.tasks,
		approved: state.approved,
		delegations: state.delegations,
		runs: state.runs,
		workspaces: state.workspaces,
		decisions: state.decisions,
		deliverables: state.deliverables,
		verifications: state.verifications,
		accepted: state.accepted,
		cancelled: state.cancelled,
	};
	const { tasks, delegations, runs, workspaces, decisions, deliverables, verifications, accepted, cancelled } =
		records;
	state.archives[archiveId] = {
		archiveId,
		archivedAt: event.time,
		actor: event.actor.id,
		reason: typeof event.payload.archiveReason === "string" ? event.payload.archiveReason : "",
		boundary: event.sequence,
		...(event.type === "workspace.archived" && event.payload.snapshotReference
			? { snapshot: event.payload.snapshotReference as ProjectArchive["snapshot"] }
			: {}),
		counts: {
			tasks: Object.keys(tasks).length,
			delegations: Object.keys(delegations).length,
			runs: Object.keys(runs).length,
			workspaces: Object.keys(workspaces).length,
			decisions: Object.keys(decisions).length,
			deliverables: Object.keys(deliverables).length,
			verifications: Object.keys(verifications).length,
			accepted: Object.keys(accepted).length,
			cancelled: Object.keys(cancelled).length,
		},
		records,
	};
	state.archiveOrder.push(archiveId);
	state.tasks = {};
	state.approved = {};
	state.delegations = {};
	state.runs = {};
	state.workspaces = {};
	state.decisions = {};
	state.deliverables = {};
	state.verifications = {};
	state.accepted = {};
	state.cancelled = {};
	state.archiveBoundary = event.sequence;
	if (event.type === "workspace.archived") {
		state.projectApproved = null;
		state.projectDraft = null;
		state.projectRejectedRevision = null;
		state.projectStatus = "DRAFT";
		state.resetBoundary = event.sequence;
		state.workspaceArchiveBoundary = event.sequence;
		state.agents = {};
	}
}

export function fold(state: GovernanceState, event: GovernanceEvent): void {
	const value = event.payload.value;
	switch (event.type) {
		case "project.drafted":
			state.projectDraft = value as GovernanceState["projectDraft"];
			state.projectRejectedRevision = null;
			if (value)
				state.projectRevisionFloor = Math.max(state.projectRevisionFloor, (value as ProjectContract).revision);
			break;
		case "project.approved":
			state.projectApproved = value as GovernanceState["projectApproved"];
			state.projectRejectedRevision = null;
			state.projectStatus = "ACTIVE";
			state.projectRevisionFloor = Math.max(state.projectRevisionFloor, Number(event.payload.revision ?? 0));
			break;
		case "project.reset":
			// Clear the live authorization without touching the ledger. Historical
			// approvals and acceptances stay in the events; they stop counting as
			// current authorization because the boundary moves past them.
			state.projectApproved = null;
			state.projectDraft = null;
			state.projectRejectedRevision = null;
			state.projectStatus = "DRAFT";
			state.resetBoundary = event.sequence;
			break;
		case "project.history.archived":
		case "workspace.archived":
			foldArchive(state, event);
			break;
		case "project.rejected":
			state.projectRejectedRevision = Number(event.payload.revision);
			break;
		case "project.paused":
			state.projectStatus = "PAUSED";
			break;
		case "project.revoked":
			state.projectStatus = "REVOKED";
			break;
		case "project.resumed":
			state.projectStatus = "ACTIVE";
			break;
		case "agent.registered": {
			const agent = value as GovernanceState["agents"][string];
			state.agents[agent.agentId] = agent;
			break;
		}
		case "agent.capabilities-granted": {
			// Appended, never edited: an agent registered before capabilities were derived
			// from its template keeps its original record, and the grant supersedes it only
			// for the capabilities it names. A grant can add, never remove, because removing
			// would silently retract a permission the earlier event still claims.
			const granted = value as { agentId?: unknown; capabilities?: unknown };
			const current = typeof granted.agentId === "string" ? state.agents[granted.agentId] : undefined;
			if (current && Array.isArray(granted.capabilities)) {
				const added = granted.capabilities.filter(
					(capability): capability is string =>
						typeof capability === "string" && !current.capabilities.includes(capability),
				);
				if (added.length)
					state.agents[current.agentId] = { ...current, capabilities: [...current.capabilities, ...added] };
			}
			break;
		}
		case "task.created":
		case "task.revised": {
			const task = value as GovernanceState["tasks"][string];
			state.tasks[task.taskId] = task;
			delete state.accepted[task.taskId];
			if (event.payload.autoApproved === true) state.approved[task.taskId] = task.revision;
			break;
		}
		case "task.approved":
		case "task.auto-approved":
			state.approved[event.taskId ?? ""] = Number(event.payload.revision);
			break;
		case "delegation.authorized": {
			const delegation = value as GovernanceState["delegations"][string];
			state.delegations[delegation.delegationId] = delegation;
			break;
		}
		case "delegation.cancelled":
			delete state.delegations[event.delegationId ?? ""];
			break;
		case "run.created": {
			const run = value as GovernanceState["runs"][string];
			state.runs[run.runId] = run;
			break;
		}
		case "run.updated":
		case "run.session-bound": {
			const run = value as GovernanceState["runs"][string];
			state.runs[run.runId] = run;
			break;
		}
		case "run.started":
		case "run.paused":
		case "run.resumed":
		case "run.interrupted":
		case "run.failed": {
			const run = value as GovernanceState["runs"][string];
			state.runs[run.runId] = run;
			break;
		}
		case "task.cancelled": {
			const cancellation = value as GovernanceState["cancelled"][string];
			state.cancelled[cancellation.taskId] = cancellation;
			// A cancelled Task is not authorized to run: approval exists in the ledger
			// as history, but it no longer licenses anything.
			delete state.approved[cancellation.taskId];
			delete state.accepted[cancellation.taskId];
			break;
		}
		case "run.finished":
		case "run.cancelled": {
			const run = value as GovernanceState["runs"][string];
			state.runs[run.runId] = run;
			break;
		}
		case "workspace.registered":
		case "workspace.updated":
		case "workspace.destroyed": {
			const workspace = value as GovernanceState["workspaces"][string];
			state.workspaces[workspace.workspaceId] = workspace;
			break;
		}
		case "workspace.destroy-requested":
			// Evidence-only event: the Worktree still exists, so no workspace state
			// changes. It exists so a crash before `workspace.destroyed` leaves a
			// visible request instead of a silently missing directory.
			break;
		case "run.execution-launch-requested":
		case "run.execution-bound":
			// Evidence-only, and listed explicitly rather than left to fall through.
			//
			// The native side generates its own Run ID and accepts no substitute, so a
			// Run's process identity cannot be known before the process exists. These two
			// events bracket that gap: the first records the intent, the second the
			// identity. A Run with the first and not the second is a real state - we asked
			// for a child and never learned what became of it - and `executionAttempts`
			// reads both to say so. `Run.state` is deliberately unchanged by either: this
			// is about which process we are talking to, not whether the Run succeeded.
			break;
		case "decision.requested":
		case "decision.recorded": {
			const decision = value as GovernanceState["decisions"][string];
			state.decisions[decision.decisionId] = decision;
			break;
		}
		case "deliverable.submitted": {
			const deliverable = value as GovernanceState["deliverables"][string];
			state.deliverables[deliverable.deliverableId] = deliverable;
			delete state.accepted[deliverable.taskId];
			break;
		}
		case "verification.recorded": {
			const verification = value as GovernanceState["verifications"][string];
			state.verifications[verification.verificationId] = verification;
			break;
		}
		case "task.accepted":
			state.accepted[event.taskId ?? ""] = String(event.payload.verificationId);
			state.decisions[event.eventId] = {
				decisionId: event.eventId,
				taskId: event.taskId ?? "",
				revision: Number(event.payload.revision),
				kind: "acceptance",
				request: "Accept verified deliverable",
				requester: "governance",
				result: "approved",
				actor: event.actor.id,
				scope: String(event.payload.commit),
				expiresAt: null,
				evidence: [String(event.payload.verificationId)],
			};
			break;
	}
	state.events.push(event);
}

function readEvents(file: string, recover: boolean): GovernanceEvent[] {
	if (!fs.existsSync(file)) return [];
	const raw = fs.readFileSync(file, "utf8");
	if (raw.length === 0) return [];
	const lastNewline = raw.lastIndexOf("\n");
	if (lastNewline !== raw.length - 1) {
		if (!recover) throw new Error("Governance log has an incomplete tail; writer recovery required");
		const tail = raw.slice(lastNewline + 1);
		const backup = `${file}.partial-${Date.now()}`;
		fs.writeFileSync(backup, tail, { flag: "wx", mode: 0o600 });
		fs.truncateSync(file, Buffer.byteLength(raw.slice(0, lastNewline + 1)));
	}
	const complete = raw.slice(0, lastNewline + 1).trim();
	if (!complete) return [];
	const stored = complete.split("\n").map((line) => JSON.parse(line) as unknown);
	const events: GovernanceEvent[] = [];
	let expected = 1;
	const ids = new Set<string>();
	let previousStoredHash: string | null = null;
	let ledgerProjectId: string | null = null;
	for (const raw of stored) {
		if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("Governance event schema is corrupt");
		const record = raw as Record<string, unknown>;
		let event: GovernanceEvent;
		if (record.ledgerVersion === 2) {
			const candidate = record as StoredGovernanceEventV2;
			if (
				typeof candidate.eventId !== "string" ||
				typeof candidate.eventType !== "string" ||
				!candidate.eventType.trim() ||
				!/^([a-z][a-z0-9-]*\.)+[a-z][a-z0-9-]*$/.test(candidate.eventType) ||
				!Number.isSafeInteger(candidate.eventVersion) ||
				candidate.eventVersion < 1 ||
				(candidate.projectId !== null && typeof candidate.projectId !== "string") ||
				typeof candidate.occurredAt !== "string" ||
				!Number.isFinite(Date.parse(candidate.occurredAt)) ||
				typeof candidate.recordedAt !== "string" ||
				!Number.isFinite(Date.parse(candidate.recordedAt)) ||
				!candidate.actor ||
				typeof candidate.actor !== "object" ||
				typeof candidate.actor.id !== "string" ||
				!candidate.actor.id.trim() ||
				!["human", "agent", "system", "plugin", "unknown"].includes(candidate.actor.kind) ||
				!["os-user", "pi-session", "governance", "plugin", "unverified"].includes(
					candidate.actor.authenticatedBy,
				) ||
				![
					candidate.actor.agentDefinitionId,
					candidate.actor.agentInstanceId,
					candidate.actor.sessionId,
					candidate.actor.runId,
				].every((value) => value === null || typeof value === "string") ||
				!candidate.subject ||
				typeof candidate.subject.type !== "string" ||
				!candidate.subject.type.trim() ||
				typeof candidate.subject.id !== "string" ||
				!candidate.subject.id.trim() ||
				!candidate.context ||
				![
					candidate.context.taskId,
					candidate.context.runId,
					candidate.context.delegationId,
					candidate.context.sessionId,
				].every((value) => value === null || typeof value === "string") ||
				typeof candidate.correlationId !== "string" ||
				!candidate.correlationId.trim() ||
				(candidate.causationEventId !== null && typeof candidate.causationEventId !== "string") ||
				(candidate.commandId !== null && typeof candidate.commandId !== "string") ||
				!candidate.payload ||
				typeof candidate.payload !== "object" ||
				Array.isArray(candidate.payload) ||
				!candidate.extensions ||
				typeof candidate.extensions !== "object" ||
				Array.isArray(candidate.extensions) ||
				candidate.integrity?.algorithm !== "sha256" ||
				candidate.integrity.prevHash !== previousStoredHash ||
				typeof candidate.integrity.eventHash !== "string"
			)
				throw new Error("Governance V2 event schema or chain is corrupt");
			const { integrity, ...content } = candidate;
			if (
				integrity.eventHash !==
				digest({ ...content, integrity: { algorithm: "sha256", prevHash: integrity.prevHash } })
			)
				throw new Error("Governance V2 event hash is corrupt");
			event = withCompatibilityAliases(candidate);
		} else {
			const legacy = record as GovernanceEventV1;
			if (
				typeof legacy.eventId !== "string" ||
				typeof legacy.type !== "string" ||
				!legacy.type.trim() ||
				typeof legacy.actor !== "string" ||
				!legacy.actor.trim() ||
				typeof legacy.time !== "string" ||
				!Number.isFinite(Date.parse(legacy.time)) ||
				!legacy.payload ||
				typeof legacy.payload !== "object" ||
				Array.isArray(legacy.payload) ||
				![legacy.taskId, legacy.runId, legacy.delegationId].every(
					(value) => value === null || typeof value === "string",
				)
			)
				throw new Error("Governance V1 event schema is corrupt");
			const payload = normalizeLegacyPayload(legacy);
			const eventType = namespacedEventType(legacy.type);
			const projectId =
				legacy.type === "project.initialized" && typeof legacy.payload.projectId === "string"
					? legacy.payload.projectId
					: (events.find((entry) => entry.type === "project.initialized")?.projectId ?? null);
			const context: EventContext = {
				taskId: legacy.taskId,
				runId: legacy.runId,
				delegationId: legacy.delegationId,
				sessionId: typeof legacy.payload.sessionId === "string" ? legacy.payload.sessionId : null,
			};
			const legacyHash = digest(legacy);
			event = withCompatibilityAliases({
				ledgerVersion: 2,
				eventId: legacy.eventId,
				sequence: legacy.sequence,
				eventType,
				eventVersion: 1,
				projectId,
				occurredAt: legacy.time,
				recordedAt: legacy.time,
				actor: actorFromLegacy(legacy.actor),
				subject: subjectFor(eventType, projectId, context, payload),
				context,
				correlationId:
					legacy.runId ?? legacy.delegationId ?? legacy.taskId ?? projectId ?? `legacy:${legacy.eventId}`,
				causationEventId: null,
				commandId: null,
				payload,
				extensions: { "agent-governance/v1": { normalizedFromV1: true } },
				integrity: { algorithm: "sha256", prevHash: previousStoredHash, eventHash: legacyHash },
			});
		}
		if (event.sequence !== expected++ || ids.has(event.eventId))
			throw new Error("Governance log sequence or ID is corrupt");
		if (event.causationEventId !== null && !ids.has(event.causationEventId))
			throw new Error("Governance event causation points outside prior history");
		if (event.type === "project.initialized") {
			if (typeof event.payload.projectId !== "string" || event.projectId !== event.payload.projectId)
				throw new Error("Governance project identity is corrupt");
			ledgerProjectId = event.projectId;
		} else if (ledgerProjectId !== null && event.projectId !== ledgerProjectId) {
			throw new Error("Governance event project identity differs from the ledger");
		}
		ids.add(event.eventId);
		events.push(event);
		previousStoredHash = digest(raw);
	}
	return events;
}

/** A lock older than this whose owner is gone is treated as abandoned, not busy. */
const STALE_LOCK_MS = 30_000;
/**
 * How long a writer waits for the lock before reporting the ledger busy.
 *
 * Writers hold the lock across a full ledger replay, so the hold time grows with
 * the ledger: at 1200 events a single append takes ~35ms, and five concurrent
 * writers must queue behind each other. A budget of zero made every loser fail
 * outright (measured: 80% of writes lost at five processes), which is why this
 * is a wait rather than an immediate error.
 */
const LOCK_RETRY_BUDGET_MS = 3_000;
/**
 * The cap is deliberately near the lock hold time rather than far above it.
 * A writer that sleeps longer than a hold window wakes up after the lock has
 * already been taken again; sleeping in fractions of it keeps a retry landing
 * inside the gap. Measured hold time at 1200 events is ~35-40ms.
 */
const LOCK_MAX_DELAY_MS = 25;

/**
 * Block for `ms` without burning CPU.
 *
 * The write path is synchronous, so waiting has to be synchronous too. A busy
 * loop would hold the CPU the lock holder needs to finish, which is exactly the
 * starvation that made concurrent writers lose writes in the first place.
 */
const sleepSleeper = new Int32Array(new SharedArrayBuffer(4));
function sleepSync(ms: number): void {
	if (ms > 0) Atomics.wait(sleepSleeper, 0, 0, ms);
}

/**
 * A stale lock is only ours to report, never ours to remove: another process may
 * be paused, not dead, and deleting its lock would corrupt the chain it is
 * writing. So an abandoned-looking lock is refused loudly, while a live one is
 * waited for.
 */
function lockLooksAbandoned(lock: string): boolean {
	try {
		if (Date.now() - fs.statSync(lock).mtimeMs <= STALE_LOCK_MS) return false;
	} catch {
		// The holder released it between our failed mkdir and this stat: not stale.
		return false;
	}
	const owner = path.join(lock, "owner");
	let pid = NaN;
	try {
		pid = Number(fs.readFileSync(owner, "utf8").split("\n")[0]);
	} catch {
		pid = NaN;
	}
	if (!Number.isSafeInteger(pid) || pid <= 0) return true;
	try {
		process.kill(pid, 0);
		return false;
	} catch {
		return true;
	}
}

/**
 * Digest of the last stored record, which the next event's `prevHash` must match.
 *
 * Only the tail is read: the whole file was already parsed once to build `state`,
 * and re-reading it here doubled the cost of every append. The tail window is a
 * heuristic; when it cuts a record in half, the full read below is the fallback.
 */
function lastStoredEventHash(root: string): string | null {
	const file = path.join(root, "events.jsonl");
	let size: number;
	try {
		size = fs.statSync(file).size;
	} catch {
		return null;
	}
	if (size === 0) return null;
	const readLastLine = (): string | null => {
		const text = fs.readFileSync(file, "utf8");
		const end = text.lastIndexOf("\n");
		const start = text.lastIndexOf("\n", end - 1);
		const line = text.slice(start + 1, end);
		return line.trim() ? line : null;
	};
	const window = Math.min(size, 262_144);
	try {
		const fd = fs.openSync(file, "r");
		try {
			const buffer = Buffer.alloc(window);
			fs.readSync(fd, buffer, 0, window, size - window);
			const text = buffer.toString("utf8");
			const end = text.lastIndexOf("\n");
			const start = text.lastIndexOf("\n", end - 1);
			const line = text.slice(start + 1, end);
			if (line.trim()) return digest(JSON.parse(line) as unknown);
		} finally {
			fs.closeSync(fd);
		}
	} catch {
		/* fall through to the full read */
	}
	const line = readLastLine();
	return line ? digest(JSON.parse(line) as unknown) : null;
}

function acquireWriterLock(lock: string): void {
	const deadline = Date.now() + LOCK_RETRY_BUDGET_MS;
	let delay = 1;
	for (;;) {
		try {
			fs.mkdirSync(lock);
			return;
		} catch (error) {
			if (lockLooksAbandoned(lock))
				throw new Error(`Stale governance writer lock requires operator inspection: ${lock}`);
			if (Date.now() >= deadline) throw new Error(`Governance writer busy: ${lock}`, { cause: error });
			// Jitter matters as much as the delay: without it every waiting writer
			// wakes at the same instant and they collide all over again.
			sleepSync(delay + Math.floor(Math.random() * delay));
			delay = Math.min(delay * 2, LOCK_MAX_DELAY_MS);
		}
	}
}

export class GovernanceStore {
	readonly root: string;
	private readonly appendListeners = new Set<(event: GovernanceEvent) => void>();
	constructor(root: string) {
		this.root = root;
	}

	/**
	 * Observe persisted events. Listeners run after the ledger write; a listener
	 * failure never fails the write. The remote sidecar uses this to push fresh
	 * projections without polling the file.
	 */
	onAppend(listener: (event: GovernanceEvent) => void): () => void {
		this.appendListeners.add(listener);
		return () => this.appendListeners.delete(listener);
	}

	read(): GovernanceState {
		const state = emptyState();
		for (const event of readEvents(path.join(this.root, "events.jsonl"), false)) fold(state, event);
		return state;
	}

	/**
	 * Record a red-line refusal, then rethrow the refusal unchanged.
	 *
	 * The write happens after the writer lock is released, because the guard that
	 * refused ran inside `check` while the lock was held. Recording from inside
	 * the check would collide with the lock it already owns.
	 */
	append(input: GovernanceEventInput, check?: (state: GovernanceState) => void): GovernanceEvent {
		try {
			return this.write(input, check);
		} catch (error) {
			const refusal = refusalOf(error);
			if (!refusal || !(error instanceof Error)) throw error;
			markRefusalRecorded(error);
			try {
				this.write(
					{
						type: "redline.triggered",
						actor: "governance",
						taskId: refusal.context.taskId ?? null,
						runId: refusal.context.runId ?? null,
						delegationId: refusal.context.delegationId ?? null,
						payload: { ...refusalPayload(error) },
					},
					undefined,
				);
			} catch (recordError) {
				// Failing to record must not hide the refusal, but it must not pass as
				// if the ledger were intact either.
				throw new Error(
					`${error.message} (refusal could not be recorded: ${recordError instanceof Error ? recordError.message : String(recordError)})`,
					{ cause: error },
				);
			}
			throw error;
		}
	}

	/**
	 * Append several events under a single lock acquisition and a single ledger
	 * replay.
	 *
	 * Every write replays the whole ledger while holding the lock, and the lock is
	 * not queued, so N separate writes cost N replays and N chances to lose the
	 * race. A caller recording a burst — a child session's tool calls — batches
	 * them here instead.
	 */
	appendMany(inputs: GovernanceEventInput[], check?: (state: GovernanceState) => void): GovernanceEvent[] {
		if (!inputs.length) return [];
		return this.writeMany(inputs, check);
	}

	private write(input: GovernanceEventInput, check?: (state: GovernanceState) => void): GovernanceEvent {
		return this.writeMany([input], check)[0];
	}

	private writeMany(inputs: GovernanceEventInput[], check?: (state: GovernanceState) => void): GovernanceEvent[] {
		fs.mkdirSync(this.root, { recursive: true, mode: 0o700 });
		const lock = path.join(this.root, "writer.lock");
		acquireWriterLock(lock);
		try {
			fs.writeFileSync(path.join(lock, "owner"), `${process.pid}\n${Date.now()}\n`, { mode: 0o600 });
			const state = emptyState();
			for (const event of readEvents(path.join(this.root, "events.jsonl"), true)) fold(state, event);
			check?.(state);
			const lines: string[] = [];
			const written: GovernanceEvent[] = [];
			let previousStoredHash = lastStoredEventHash(this.root);
			const recordedAt = new Date().toISOString();
			for (const input of inputs) {
				if (input.causationEventId && !state.events.some((event) => event.eventId === input.causationEventId))
					throw new Error("Governance event causation must reference prior history");
				const eventType = namespacedEventType(input.type, input.eventNamespace);
				const projectId =
					input.projectId ??
					(input.type === "project.initialized" && typeof input.payload.projectId === "string"
						? input.payload.projectId
						: (state.events.find((event) => event.type === "project.initialized")?.projectId ?? null));
				const context: EventContext = {
					taskId: input.taskId,
					runId: input.runId,
					delegationId: input.delegationId,
					sessionId:
						input.sessionId ??
						(typeof input.payload.sessionId === "string" ? input.payload.sessionId : null) ??
						(typeof input.actor === "object" ? input.actor.sessionId : null),
				};
				let actor = typeof input.actor === "string" ? actorFromLegacy(input.actor) : input.actor;
				if (actor.kind === "unknown" && state.agents[actor.id])
					actor = {
						...actor,
						kind: "agent",
						agentDefinitionId: state.agents[actor.id].agentId,
						agentInstanceId: actor.id,
					};
				if (input.runId && actor.kind === "agent") actor = { ...actor, runId: input.runId };
				const inferredCause =
					state.events
						.filter(
							(event) =>
								(input.runId && event.context.runId === input.runId) ||
								(input.delegationId && event.context.delegationId === input.delegationId) ||
								(input.type === "delegation.authorized" &&
									event.type === "delegation.requested" &&
									event.context.taskId === input.taskId &&
									event.payload.agent ===
										(input.payload.value as Record<string, unknown> | undefined)?.executorId) ||
								(input.type === "task.accepted" &&
									event.type === "verification.recorded" &&
									(event.payload.value as Record<string, unknown> | undefined)?.verificationId ===
										input.payload.verificationId) ||
								(input.type === "project.approved" &&
									event.type === "project.drafted" &&
									(event.payload.value as Record<string, unknown> | undefined)?.revision ===
										input.payload.revision),
						)
						.at(-1) ?? null;
				const causationEventId = input.causationEventId ?? inferredCause?.eventId ?? null;
				const content = {
					ledgerVersion: 2 as const,
					eventId: randomUUID(),
					sequence: state.events.length + 1,
					eventType,
					eventVersion: input.eventVersion ?? 1,
					projectId,
					occurredAt: input.occurredAt ?? recordedAt,
					recordedAt,
					actor,
					subject: input.subject ?? subjectFor(eventType, projectId, context, input.payload),
					context,
					correlationId:
						input.correlationId ??
						inferredCause?.correlationId ??
						input.runId ??
						input.delegationId ??
						input.taskId ??
						projectId ??
						`event:${state.events.length + 1}`,
					causationEventId,
					commandId: input.commandId ?? null,
					payload: input.payload,
					extensions: input.extensions ?? {},
				};
				const stored: StoredGovernanceEventV2 = {
					...content,
					integrity: {
						algorithm: "sha256",
						prevHash: previousStoredHash,
						eventHash: digest({ ...content, integrity: { algorithm: "sha256", prevHash: previousStoredHash } }),
					},
				};
				lines.push(JSON.stringify(stored));
				// The next event in this batch links to this one, so the chain is built in
				// memory instead of by re-reading what was just written.
				previousStoredHash = digest(stored);
				const event = withCompatibilityAliases(stored);
				// Folding locally keeps `sequence` and causation inference correct for the
				// remaining inputs without another replay.
				fold(state, event);
				written.push(event);
			}
			const fd = fs.openSync(path.join(this.root, "events.jsonl"), "a", 0o600);
			try {
				const bytes = Buffer.from(`${lines.join("\n")}\n`);
				let offset = 0;
				while (offset < bytes.length) offset += fs.writeSync(fd, bytes, offset, bytes.length - offset);
				fs.fsyncSync(fd);
			} finally {
				fs.closeSync(fd);
			}
			for (const event of written) {
				for (const listener of this.appendListeners) {
					try {
						listener(event);
					} catch {
						/* observers must never break the ledger write */
					}
				}
			}
			return written;
		} finally {
			fs.rmSync(lock, { recursive: true });
		}
	}

	restore(source: string): void {
		readEvents(source, false);
		fs.mkdirSync(this.root, { recursive: true, mode: 0o700 });
		const lock = path.join(this.root, "writer.lock");
		fs.mkdirSync(lock);
		try {
			fs.copyFileSync(source, path.join(this.root, "events.jsonl"), fs.constants.COPYFILE_EXCL);
		} finally {
			fs.rmSync(lock, { recursive: true });
		}
	}

	backup(destination: string): void {
		const lock = path.join(this.root, "writer.lock");
		fs.mkdirSync(lock);
		try {
			const source = path.join(this.root, "events.jsonl");
			readEvents(source, false);
			fs.copyFileSync(source, destination, fs.constants.COPYFILE_EXCL);
			const fd = fs.openSync(destination, "r");
			try {
				fs.fsyncSync(fd);
			} finally {
				fs.closeSync(fd);
			}
		} finally {
			fs.rmSync(lock, { recursive: true });
		}
	}
}
