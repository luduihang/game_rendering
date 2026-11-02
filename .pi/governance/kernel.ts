import { execFileSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { baselineExceeded, evaluateTaskApproval, validateApprovalPolicy } from "./approval-policy.ts";
import { verifyDeliverableCommit } from "./deliverable-evidence.ts";
import { normalizeDraftText, validateDraftDocument } from "./draft.ts";
import { captureExecutionIdentity, executionAttempts, lostRunEvidence } from "./execution-identity.ts";
import type { IdentityAssurance, IdentitySource } from "./identity.ts";
import { loadOrgApprovalPolicy, mergeOrgDeny } from "./org-policy.ts";
import { refuse } from "./redline.ts";
import type { GovernanceStore } from "./store.ts";
import { nativeRunLiveness, readNativeRunStatus } from "./subagent-supervision.ts";
import { assertStructuredTests, verifyTestLog } from "./test-evidence.ts";
import type {
	Agent,
	ApprovalEvaluation,
	Authority,
	Decision,
	Delegation,
	Deliverable,
	GovernanceEvent,
	GovernanceEventInput,
	GovernanceState,
	ProjectContract,
	Run,
	RunState,
	TaskCancellation,
	TaskContract,
	Verification,
	Workspace,
	WorkspaceDestroyEvidence,
	WorkspaceDestroyResult,
} from "./types.ts";

const nonempty = (value: string, name: string) => {
	if (!value.trim()) throw new Error(`${name} is required`);
};
const id = (prefix: string) => `${prefix}-${randomUUID()}`;
const active = (state: RunState) =>
	state === "CREATED" || state === "RUNNING" || state === "PAUSED" || state === "INTERRUPTED";
const taskKind = (task: TaskContract) => task.kind ?? "executable";
/**
 * Budget a Task contributes to the project total.
 *
 * This is the reservation, not the spend: a container organizes work and reserves
 * nothing, and an executable Task reserves only while it could still run. A Task
 * that was never approved, or that has reached a terminal state, reserves nothing
 * — otherwise a rejected or cancelled Task would hold project budget forever, which
 * is the leak this account exists to close. Actual usage is tracked separately on
 * the Run (`usageTokens`) and is never inflated into a reservation.
 */
const taskBudget = (task: TaskContract) => (taskKind(task) === "executable" ? task.budgetTokens : 0);

/**
 * Budget currently reserved against the project limit.
 *
 * `state.approved` arrives by two roads and they disagree. `getState` prunes it;
 * the store hands `append` a raw fold that has not been pruned. The budget check
 * inside `append` runs on the raw one, so an approval a reset or a baseline
 * revision has already revoked is still counted, and the project reports tokens
 * reserved for work it will refuse to run. Applying the approval rule here makes
 * the projection independent of which road the caller took.
 */
// Exported so every budget projection (CLI status, web snapshot) can count the
// same way the kernel does; a second, cheaper rule would drift from this one.
export function reservedBudget(state: GovernanceState): number {
	return Object.values(state.tasks)
		.filter((task) => state.approved[task.taskId] === task.revision && approvalStands(state, task.taskId))
		.reduce((sum, task) => sum + taskBudget(task), 0);
}

export type DelegationSessionOrigin = {
	sessionId: string;
	sessionFile: string;
	parentRunId: string | null;
};

export function validAuthority(authority: Authority): void {
	if (!Array.isArray(authority.paths) || !Array.isArray(authority.tools))
		refuse("invalid-authority", "Invalid authority lists", "validate authority");
	for (const value of [...authority.paths, ...authority.tools]) nonempty(value, "authority item");
	// Paths escaping the repository are the clearest red line: a relative `..`
	// or an absolute path would put the whole filesystem inside the authority.
	const escaping = authority.paths.filter((value) => value.startsWith("/") || value.split("/").includes(".."));
	if (escaping.length)
		refuse("invalid-authority", "Authority paths must stay within the repository", "validate authority", {
			paths: authority.paths,
			escaping,
		});
	for (const key of ["readRepository", "writeWorkspace", "commitBranch", "integrateBranch"] as const) {
		if (typeof authority[key] !== "boolean") throw new Error(`Invalid authority ${key}`);
	}
}

export function subset(child: Authority, parent: Authority): boolean {
	return (
		child.paths.every((item) =>
			parent.paths.some((allowed) => item === allowed || item.startsWith(`${allowed.replace(/\/$/, "")}/`)),
		) &&
		child.tools.every((item) => parent.tools.includes(item)) &&
		(!child.readRepository || parent.readRepository) &&
		(!child.writeWorkspace || parent.writeWorkspace) &&
		(!child.commitBranch || parent.commitBranch) &&
		(!child.integrateBranch || parent.integrateBranch)
	);
}

function taskReady(state: GovernanceState, task: TaskContract): void {
	const context = { taskId: task.taskId };
	if (taskKind(task) === "container")
		refuse("delegation-limit", "Container tasks cannot be delegated", "authorize delegation", {}, context);
	// A cancelled Task is terminal: its approval stays in the ledger as history, but
	// nothing may start work against it again.
	if (state.cancelled[task.taskId])
		refuse(
			"task-not-approved",
			"Task is cancelled",
			"authorize delegation",
			{ reason: state.cancelled[task.taskId].reason, cancelledAt: state.cancelled[task.taskId].at },
			context,
		);
	if (!currentTaskApproval(state, task.taskId))
		refuse(
			"task-not-approved",
			"Task revision is not approved",
			"authorize delegation",
			{ revision: task.revision, approvedRevision: state.approved[task.taskId] ?? null },
			context,
		);
	if (state.events.some((event) => event.type === "project.initialized")) {
		if (state.projectStatus !== "ACTIVE" || !state.projectApproved)
			refuse(
				"project-not-active",
				"Approved active project baseline required",
				"authorize delegation",
				{ projectStatus: state.projectStatus, hasBaseline: Boolean(state.projectApproved) },
				context,
			);
		projectAdmitsTask(state.projectApproved, task);
	}
	let parentId = task.parentTaskId ?? null;
	while (parentId) {
		const parent = state.tasks[parentId];
		if (!parent || taskKind(parent) !== "container" || !currentTaskApproval(state, parentId))
			refuse(
				"task-not-approved",
				`Parent task ${parentId} is missing or not approved`,
				"authorize delegation",
				{ parentTaskId: parentId },
				context,
			);
		if (state.projectApproved && state.projectStatus === "ACTIVE") projectAdmitsTask(state.projectApproved, parent);
		parentId = parent.parentTaskId ?? null;
	}
	for (const dependency of task.dependencies) {
		if (!currentAcceptance(state, dependency.taskId))
			refuse(
				"dependency-unmet",
				`Dependency ${dependency.taskId} is not accepted`,
				"authorize delegation",
				{ dependency: dependency.taskId },
				context,
			);
	}
}

// This runs in three places: task submission, task approval, and the delegated
// readiness check. Every refusal here is a baseline violation, which is exactly
// what the operator needs to see rather than a silently missing task.
//
// The refusal carries the full diagnosis, because a refusal that only says
// "scope exceeds baseline" leaves the operator to work out which path, which
// tool and which limit. The remedy is stated too: the baseline has to be revised
// before the Task can be handled.
function projectAdmitsTask(project: ProjectContract, task: TaskContract): void {
	const context = { taskId: task.taskId };
	const exceeded = baselineExceeded(project, task);
	const remedy = {
		requiresBaselineRevision: true,
		summary:
			"Revise the project baseline to cover this Task, then submit it again. Until the baseline covers it, the Task cannot be approved or delegated.",
	};
	const outside = task.scope.filter((item) => !project.inScope.includes(item));
	if (outside.length)
		refuse(
			"task-outside-baseline",
			"Task scope exceeds project baseline",
			"admit task under baseline",
			{ outside, taskScope: task.scope, inScope: project.inScope, exceeded, ...remedy },
			context,
		);
	if (!subset(task.authority, project.authority))
		refuse(
			"authority-escalation",
			"Task authority exceeds project baseline",
			"admit task under baseline",
			{
				taskAuthority: task.authority,
				projectAuthority: project.authority,
				exceeded,
				...remedy,
			},
			context,
		);
	if (task.maxDepth > project.delegationPolicy.maxDepth || task.maxConcurrent > project.delegationPolicy.maxConcurrent)
		refuse(
			"delegation-limit",
			"Task delegation limits exceed project baseline",
			"admit task under baseline",
			{
				task: { maxDepth: task.maxDepth, maxConcurrent: task.maxConcurrent },
				project: project.delegationPolicy,
				exceeded,
				...remedy,
			},
			context,
		);
}

/**
 * Does any Task-approval event land after the last reset?
 *
 * Used only when a reset happened. An approval that predates it stays in the
 * ledger as history but no longer authorizes execution; the Task has to be
 * approved again against the new baseline.
 */
function approvalAfterReset(state: GovernanceState, taskId: string): boolean {
	return state.events.some(
		(event) =>
			event.taskId === taskId &&
			event.sequence > state.resetBoundary &&
			(event.type === "task.approved" ||
				event.type === "task.auto-approved" ||
				(event.type === "task.created" && event.payload.autoApproved === true)),
	);
}

/** Whether anything live would move into an archive. */
function hasCurrentRecords(state: GovernanceState): boolean {
	return (
		Object.keys(state.tasks).length > 0 ||
		Object.keys(state.delegations).length > 0 ||
		Object.keys(state.runs).length > 0 ||
		Object.keys(state.workspaces).length > 0 ||
		Object.keys(state.deliverables).length > 0 ||
		Object.keys(state.verifications).length > 0
	);
}

function currentTaskApproval(state: GovernanceState, taskId: string): boolean {
	const task = state.tasks[taskId];
	if (!task || state.approved[taskId] !== task.revision) return false;
	// A reset revokes current authorization without rewriting history: the
	// approval event stays in the ledger and stays readable, but an approval
	// granted before the boundary is not a license to run now.
	if (state.resetBoundary > 0 && !approvalAfterReset(state, taskId)) return false;
	const approval = state.events.filter((event) => event.type === "task.approved" && event.taskId === taskId).at(-1);
	const automatic = state.events
		.filter(
			(event) =>
				(event.type === "task.auto-approved" ||
					(event.type === "task.created" && event.payload.autoApproved === true)) &&
				event.taskId === taskId,
		)
		.at(-1);
	if (automatic && (!approval || automatic.sequence > approval.sequence))
		return state.projectStatus === "ACTIVE" && state.projectApproved?.revision === automatic.payload.projectRevision;
	const decisionId = approval?.payload.decisionId;
	const decision = typeof decisionId === "string" ? state.decisions[decisionId] : undefined;
	return Boolean(
		decision &&
			decision.result === "approved" &&
			decision.revision === task.revision &&
			(decision.expiresAt === null || Date.parse(decision.expiresAt) > Date.now()),
	);
}

/**
 * Whether an approval is still a license to run: approved at the current revision, not
 * revoked by a reset, and still admitted by the approved baseline.
 *
 * The baseline half is easy to forget, and forgetting it is not cosmetic. `getState`
 * prunes with this rule, so a Task dropped here is not approved as far as every caller
 * is concerned; if the budget projection used a cheaper rule, the project would report
 * tokens as reserved for work it will refuse to run.
 */
function approvalStands(state: GovernanceState, taskId: string): boolean {
	if (!currentTaskApproval(state, taskId)) return false;
	if (!state.events.some((event) => event.type === "project.initialized")) return true;
	// Inactive project or exceeded baseline: the approval is history, not standing.
	if (state.projectStatus !== "ACTIVE" || !state.projectApproved) return false;
	try {
		projectAdmitsTask(state.projectApproved, state.tasks[taskId]);
		return true;
	} catch {
		return false;
	}
}

function currentAcceptance(state: GovernanceState, taskId: string, visiting = new Set<string>()): boolean {
	if (visiting.has(taskId)) return false;
	const task = state.tasks[taskId];
	if (!task) return false;
	// Same rule as approval: a historical acceptance remains an auditable fact
	// (the event is untouched) but does not survive a reset as current standing.
	if (state.resetBoundary > 0) {
		const accepted = state.events.filter((event) => event.type === "task.accepted" && event.taskId === taskId).at(-1);
		if (!accepted || accepted.sequence <= state.resetBoundary) return false;
	}
	if (taskKind(task) === "container") {
		if (!currentTaskApproval(state, taskId)) return false;
		const children = Object.values(state.tasks).filter((child) => child.parentTaskId === taskId);
		if (!children.length) return false;
		visiting.add(taskId);
		const accepted =
			task.dependencies.every((dependency) => currentAcceptance(state, dependency.taskId, visiting)) &&
			children.every((child) => currentAcceptance(state, child.taskId, visiting));
		visiting.delete(taskId);
		return accepted;
	}
	const verification = state.verifications[state.accepted[taskId]];
	if (!verification || verification.revision !== task.revision || verification.result !== "passed") return false;
	const latest = Object.values(state.deliverables)
		.filter((entry) => entry.taskId === taskId)
		.at(-1);
	if (!latest || latest.deliverableId !== verification.deliverableId) return false;
	const workspaceId = latest.runId ? state.runs[latest.runId]?.workspaceId : null;
	if (!workspaceId) return true;
	try {
		return (
			execFileSync("git", ["rev-parse", "HEAD"], {
				cwd: state.workspaces[workspaceId].path,
				encoding: "utf8",
			}).trim() === verification.commit
		);
	} catch {
		return false;
	}
}

/**
 * Whether this session activated this task.
 *
 * The activation is read from the ledger rather than from an in-memory pointer,
 * because the pointer can only hold one task per session while the ledger can
 * record every task a session worked on. Authorization therefore survives a
 * pointer being overwritten, and a reset still revokes it: an activation before
 * the boundary is history, not standing.
 */
export function isTaskActivatedForSession(state: GovernanceState, sessionId: string, taskId: string): boolean {
	return state.events.some(
		(event) =>
			event.type === "session.task-activated" &&
			event.payload.sessionId === sessionId &&
			event.taskId === taskId &&
			event.sequence > state.resetBoundary,
	);
}

export class GovernanceKernel {
	readonly store: GovernanceStore;
	constructor(store: GovernanceStore) {
		this.store = store;
	}
	getState(): GovernanceState {
		const state = this.store.read();
		for (const taskId of Object.keys(state.approved))
			if (!approvalStands(state, taskId)) delete state.approved[taskId];
		for (const taskId of Object.keys(state.accepted))
			if (!currentAcceptance(state, taskId)) delete state.accepted[taskId];
		return state;
	}

	streamEvents(afterSequence = 0): GovernanceEvent[] {
		return this.store.read().events.filter((event) => event.sequence > afterSequence);
	}

	submitProjectDraft(input: ProjectContract, actor: string): void {
		nonempty(actor, "actor");
		// GOV-001: normalize double-escaped model output once at the draft
		// boundary, before anything is stored. The ledger is never rewritten.
		const draft = (value: string): string => normalizeDraftText(value).text;
		const contract: ProjectContract = {
			...input,
			goal: draft(input.goal),
			prd: draft(input.prd),
			plan: draft(input.plan),
			changeReason: draft(input.changeReason),
			inScope: input.inScope.map(draft),
			outOfScope: input.outOfScope.map(draft),
			successCriteria: input.successCriteria.map(draft),
			humanApprovalTriggers: input.humanApprovalTriggers.map(draft),
		};
		const normalizedFields: string[] = [];
		for (const field of ["prd", "plan", "goal", "changeReason"] as const)
			if (normalizeDraftText(String(input[field] ?? "")).normalized) normalizedFields.push(field);
		for (const field of ["inScope", "outOfScope", "successCriteria", "humanApprovalTriggers"] as const)
			if ((input[field] ?? []).some((item) => normalizeDraftText(item).normalized)) normalizedFields.push(field);
		nonempty(contract.name, "project name");
		nonempty(contract.goal, "project goal");
		nonempty(contract.prd, "PRD");
		nonempty(contract.plan, "implementation plan");
		nonempty(contract.changeReason, "change reason");
		for (const [name, items] of [
			["inScope", contract.inScope],
			["outOfScope", contract.outOfScope],
			["successCriteria", contract.successCriteria],
			["humanApprovalTriggers", contract.humanApprovalTriggers],
		] as const) {
			if (!Array.isArray(items) || !items.length || items.some((item) => typeof item !== "string" || !item.trim()))
				throw new Error(`Invalid project ${name}`);
		}
		// GOV-002: structural quality gate. Rejected drafts are not stored;
		// the caller receives the specific gap to fix.
		validateDraftDocument("PRD", contract.prd);
		validateDraftDocument("plan", contract.plan);
		if (contract.inScope.some((item) => contract.outOfScope.includes(item)))
			throw new Error("Project scope overlaps exclusions");
		validAuthority(contract.authority);
		validateApprovalPolicy(contract.approvalPolicy);
		if (
			!Number.isSafeInteger(contract.revision) ||
			contract.revision < 1 ||
			!Number.isSafeInteger(contract.resourceLimits?.budgetTokens) ||
			contract.resourceLimits.budgetTokens <= 0 ||
			!Number.isSafeInteger(contract.delegationPolicy?.maxDepth) ||
			contract.delegationPolicy.maxDepth < 0 ||
			!Number.isSafeInteger(contract.delegationPolicy?.maxConcurrent) ||
			contract.delegationPolicy.maxConcurrent < 1 ||
			typeof contract.delegationPolicy.allowInternalTasks !== "boolean"
		)
			throw new Error("Invalid project revision or limits");
		const event: GovernanceEventInput = {
			type: "project.drafted",
			actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: { value: contract, priorRevision: contract.revision - 1, normalized: normalizedFields },
		};
		this.store.append(event, (state) => {
			const identity = state.events.find((event) => event.type === "project.initialized")?.payload.projectId;
			if (identity !== contract.projectId) throw new Error("Project ID differs from initialized repository");
			if (state.projectStatus === "REVOKED") throw new Error("Project is revoked");
			// The floor spans resets: clearing the pending draft must not send the next
			// revision back to r1, because a human already decided on r1 once.
			const nextRevision = Math.max(state.projectRevisionFloor, state.projectDraft?.revision ?? 0) + 1;
			if (contract.revision !== nextRevision)
				throw new Error(`Project changes require a new revision: r${nextRevision}`);
			const previous = state.projectApproved;
			event.payload.impact = {
				affectedTasks: Object.keys(state.tasks),
				// Delta against the currently approved baseline only; a first
				// draft has no approved baseline to compare with.
				budgetDeltaTokens: previous
					? contract.resourceLimits.budgetTokens - previous.resourceLimits.budgetTokens
					: null,
				authorityChanged: Boolean(
					previous && JSON.stringify(previous.authority) !== JSON.stringify(contract.authority),
				),
				approvalPolicyChanged: Boolean(
					previous && JSON.stringify(previous.approvalPolicy) !== JSON.stringify(contract.approvalPolicy),
				),
			};
		});
	}

	approveProject(revision: number, actor: string): void {
		nonempty(actor, "actor");
		const event: GovernanceEventInput = {
			type: "project.approved",
			actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: { value: null as ProjectContract | null, revision },
		};
		this.store.append(event, (state) => {
			const draft = state.projectDraft;
			if (
				!draft ||
				draft.revision !== revision ||
				state.projectApproved?.revision === revision ||
				state.projectRejectedRevision === revision ||
				state.projectStatus === "REVOKED"
			)
				throw new Error("Current unapproved project revision required");
			const committed = reservedBudget(state);
			if (committed > draft.resourceLimits.budgetTokens)
				throw new Error("Existing task budgets exceed proposed project limit");
			if (Object.values(state.runs).some((run) => active(run.state)))
				throw new Error("Reconcile active Runs before changing the approved baseline");
			event.payload.value = draft;
			event.payload.priorRevision = state.projectApproved?.revision ?? null;
		});
	}

	rejectProject(revision: number, actor: string, reason: string): void {
		nonempty(actor, "actor");
		nonempty(reason, "rejection reason");
		this.store.append(
			{
				type: "project.rejected",
				actor,
				taskId: null,
				runId: null,
				delegationId: null,
				payload: { revision, reason },
			},
			(state) => {
				if (
					state.projectDraft?.revision !== revision ||
					state.projectApproved?.revision === revision ||
					state.projectRejectedRevision === revision
				)
					throw new Error("Current pending project revision required");
			},
		);
	}

	controlProject(action: "pause" | "resume" | "revoke", actor: string): void {
		const event: GovernanceEventInput = {
			type: `project.${action === "revoke" ? "revoked" : action === "pause" ? "paused" : "resumed"}`,
			actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: {},
		};
		this.store.append(event, (state) => {
			if (
				(action === "resume" && state.projectStatus !== "PAUSED") ||
				(action !== "resume" && state.projectStatus !== "ACTIVE")
			)
				throw new Error("Invalid project transition");
			const activeRuns = Object.values(state.runs)
				.filter((run) => active(run.state))
				.map((run) => run.runId);
			if (action === "revoke" && activeRuns.length)
				throw new Error("Active Runs must be reconciled before revoking project");
			event.payload.activeRunIds = activeRuns;
		});
	}

	/**
	 * Revoke the current project authorization and go back to needing a baseline.
	 *
	 * Only derived state changes: the ledger keeps every historical approval,
	 * acceptance, Task and Run. Because `resetBoundary` moves past them, those
	 * facts remain readable but stop authorizing execution, which is the
	 * difference between "was approved" and "is approved now".
	 *
	 * Confirmation is the project id rather than a boolean. A boolean is easy to
	 * pass by accident from a script or a web handler; retyping the identity is
	 * not, and it also proves the caller knows which project it is resetting.
	 */
	resetProject(input: { actor: string; reason: string; confirm: string }): GovernanceEvent {
		nonempty(input.actor, "actor");
		nonempty(input.reason, "reset reason");
		nonempty(input.confirm, "confirmation");
		const state = this.getState();
		const projectId = state.events.find((event) => event.type === "project.initialized")?.payload.projectId;
		if (typeof projectId !== "string") throw new Error("Governance is not initialized for this project");
		if (input.confirm !== projectId) throw new Error(`Confirmation must be the project id: ${projectId}`);
		// Unknown execution state counts as live: a Run whose terminal state was
		// never recorded must be reconciled, not invalidated by a reset.
		const activeRuns = Object.values(state.runs)
			.filter((run) => active(run.state))
			.map((run) => run.runId);
		if (activeRuns.length)
			throw new Error(`Active Runs must be reconciled before resetting: ${activeRuns.join(", ")}`);
		if (state.projectStatus === "DRAFT" && !state.projectApproved && !state.projectDraft)
			throw new Error("Nothing to reset: no approved baseline or pending draft");
		const lastApproved = state.events.filter((event) => event.type === "project.approved").at(-1);
		const previousRevision = state.projectApproved?.revision ?? state.projectDraft?.revision ?? null;
		const backup = this.backupBefore("reset");
		const event: GovernanceEventInput = {
			type: "project.reset",
			actor: input.actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: {
				projectId,
				previousRevision,
				lastApprovedRevision:
					typeof lastApproved?.payload.revision === "number" ? lastApproved.payload.revision : null,
				// Named explicitly so a reader can tell what the reset actually revoked
				// without diffing two projections.
				affectedConfiguration: [
					...(state.projectApproved ? [`project.baseline:r${state.projectApproved.revision}`] : []),
					...(state.projectApproved ? ["project.authority", "project.approval"] : []),
					...(state.projectDraft ? [`project.draft:r${state.projectDraft.revision}`] : []),
					"subagent.policy-approval",
				],
				resetReason: input.reason,
				backupReference: backup,
			},
		};
		return this.store.append(event, (fresh) => {
			if (fresh.events.find((entry) => entry.type === "project.initialized")?.payload.projectId !== projectId)
				throw new Error("Project identity changed during reset");
			if (fresh.projectStatus === "DRAFT" && !fresh.projectApproved && !fresh.projectDraft)
				throw new Error("Nothing to reset: no approved baseline or pending draft");
			const live = Object.values(fresh.runs)
				.filter((run) => active(run.state))
				.map((run) => run.runId);
			if (live.length) throw new Error(`Active Runs must be reconciled before resetting: ${live.join(", ")}`);
		});
	}

	/**
	 * Move the current work records into an archive without resetting governance.
	 *
	 * The event records the boundary and the counts; the projection does the move,
	 * so the ledger is untouched and replay reproduces the same split. A second
	 * call with nothing current to move is refused rather than writing an empty
	 * archive, which keeps "one archive per Start Fresh" true.
	 */
	archiveHistory(input: { actor: string; reason: string; confirm: string }): GovernanceEvent {
		nonempty(input.actor, "actor");
		nonempty(input.reason, "archive reason");
		nonempty(input.confirm, "confirmation");
		const state = this.getState();
		const projectId = state.events.find((event) => event.type === "project.initialized")?.payload.projectId;
		if (typeof projectId !== "string") throw new Error("Governance is not initialized for this project");
		if (input.confirm !== projectId) throw new Error(`Confirmation must be the project id: ${projectId}`);
		const activeRuns = Object.values(state.runs)
			.filter((run) => active(run.state))
			.map((run) => run.runId);
		if (activeRuns.length)
			throw new Error(`Active Runs must be reconciled before archiving: ${activeRuns.join(", ")}`);
		if (!hasCurrentRecords(state)) throw new Error("Nothing to archive: the current workspace is already empty");
		const archiveId = `A-${randomUUID()}`;
		const boundary = (state.events.at(-1)?.sequence ?? 0) + 1;
		const backup = this.backupBefore("archive");
		const event: GovernanceEventInput = {
			type: "project.history.archived",
			actor: input.actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: {
				projectId,
				archiveId,
				archivedRecordCounts: {
					tasks: Object.keys(state.tasks).length,
					delegations: Object.keys(state.delegations).length,
					runs: Object.keys(state.runs).length,
					workspaces: Object.keys(state.workspaces).length,
					decisions: Object.keys(state.decisions).length,
					deliverables: Object.keys(state.deliverables).length,
					verifications: Object.keys(state.verifications).length,
					accepted: Object.keys(state.accepted).length,
				},
				archiveBoundary: boundary,
				archiveReason: input.reason,
				backupReference: backup,
			},
		};
		return this.store.append(event, (fresh) => {
			if (!hasCurrentRecords(fresh)) throw new Error("Nothing to archive: the current workspace is already empty");
			const live = Object.values(fresh.runs)
				.filter((run) => active(run.state))
				.map((run) => run.runId);
			if (live.length) throw new Error(`Active Runs must be reconciled before archiving: ${live.join(", ")}`);
		});
	}

	/**
	 * Copy the ledger before an irreversible-looking operation.
	 *
	 * The reset and the archive are both additive, so the backup is not needed to
	 * restore correctness; it exists so an operator who dislikes the outcome can
	 * compare or rebuild from the exact bytes the decision was made against. The
	 * digest is recorded in the event, so the file can be checked later.
	 */
	private backupBefore(kind: "reset" | "archive"): { path: string; sha256: string } {
		const directory = path.join(this.store.root, "backups");
		fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
		const file = path.join(directory, `pre-${kind}-${new Date().toISOString().replace(/[:.]/g, "-")}.jsonl`);
		this.store.backup(file);
		return { path: file, sha256: createHash("sha256").update(fs.readFileSync(file)).digest("hex") };
	}

	handoff(taskId: string) {
		const state = this.getState();
		const task = state.tasks[taskId];
		if (!task) throw new Error("Unknown task");
		return {
			task,
			approvedRevision: state.approved[taskId] ?? null,
			runs: Object.values(state.runs).filter((run) => run.taskId === taskId),
			workspace: Object.values(state.workspaces).find((entry) => entry.taskId === taskId) ?? null,
			decisions: Object.values(state.decisions).filter(
				(entry) => entry.taskId === taskId && entry.result === "pending",
			),
			deliverable:
				Object.values(state.deliverables)
					.filter((entry) => entry.taskId === taskId)
					.at(-1) ?? null,
			verification: this.getVerification(taskId),
		};
	}

	getVerification(taskId: string): { record: Verification | null; current: boolean } {
		const state = this.getState();
		const artifact = Object.values(state.deliverables)
			.filter((entry) => entry.taskId === taskId)
			.at(-1);
		const record = artifact
			? (Object.values(state.verifications)
					.filter((entry) => entry.deliverableId === artifact.deliverableId)
					.at(-1) ?? null)
			: null;
		return {
			record,
			current: Boolean(
				record &&
					record.revision === state.tasks[taskId]?.revision &&
					currentAcceptance(
						{ ...state, accepted: { ...state.accepted, [taskId]: record.verificationId } },
						taskId,
					),
			),
		};
	}

	controlRun(runId: string, action: "pause" | "resume" | "cancel", actor: string): GovernanceEvent {
		const state = this.getState();
		const run = state.runs[runId];
		if (!run) throw new Error("Unknown Run");
		if (action === "pause" && run.state !== "RUNNING") throw new Error("Only running Runs can pause");
		if (action === "resume" && run.state !== "PAUSED" && run.state !== "INTERRUPTED")
			throw new Error("Run is not resumable");
		if (action === "cancel" && !active(run.state)) throw new Error("Run is already terminal");
		return this.store.append({
			type: "run.control-requested",
			actor,
			taskId: run.taskId,
			runId,
			delegationId: run.delegationId,
			payload: { action },
		});
	}

	registerAgent(agent: Agent, actor: string): void {
		nonempty(agent.agentId, "agentId");
		nonempty(agent.harness, "harness");
		nonempty(agent.role, "role");
		if (!Array.isArray(agent.capabilities)) throw new Error("Agent capabilities must be a list");
		this.store.append(
			{ type: "agent.registered", actor, taskId: null, runId: null, delegationId: null, payload: { value: agent } },
			(state) => {
				if (state.agents[agent.agentId]) throw new Error("Agent already registered");
			},
		);
	}

	/**
	 * Add capabilities to an already-registered agent.
	 *
	 * Exists because registration is immutable: an agent registered before capabilities
	 * were derived from its template would otherwise stay without them for the life of the
	 * ledger. Adding is a separate, later fact rather than a correction of the earlier one.
	 */
	grantCapabilities(agentId: string, capabilities: string[], actor: string): void {
		nonempty(agentId, "agentId");
		if (!Array.isArray(capabilities) || !capabilities.length)
			throw new Error("capabilities must be a non-empty list");
		for (const capability of capabilities) nonempty(capability, "capability");
		this.store.append(
			{
				type: "agent.capabilities-granted",
				actor,
				taskId: null,
				runId: null,
				delegationId: null,
				payload: { value: { agentId, capabilities } },
			},
			(state) => {
				if (!state.agents[agentId]) throw new Error("Unknown agent");
			},
		);
	}

	submitTask(
		task: TaskContract,
		actor: string,
		kind: ApprovalEvaluation["inputs"]["taskKind"] = "ordinary",
	): ApprovalEvaluation {
		nonempty(task.taskId, "taskId");
		nonempty(task.goal, "goal");
		nonempty(task.owner, "owner");
		if (!/^[A-Za-z0-9_-]+$/.test(task.taskId)) throw new Error("Invalid task ID");
		if (
			!Array.isArray(task.scope) ||
			!Array.isArray(task.acceptance) ||
			!task.scope.length ||
			(taskKind(task) === "executable" && !task.acceptance.length) ||
			task.scope.some((item) => typeof item !== "string" || !item.trim()) ||
			task.acceptance.some((item) => typeof item !== "string" || !item.trim())
		)
			throw new Error("Task scope and acceptance are required");
		if (task.kind !== undefined && task.kind !== "container" && task.kind !== "executable")
			throw new Error("Invalid task kind");
		if (task.splitReason !== undefined && (typeof task.splitReason !== "string" || !task.splitReason.trim()))
			throw new Error("Invalid task split reason");
		if (
			task.parentTaskId !== undefined &&
			task.parentTaskId !== null &&
			(typeof task.parentTaskId !== "string" || !/^[A-Za-z0-9_-]+$/.test(task.parentTaskId))
		)
			throw new Error("Invalid parent task ID");
		if (!Array.isArray(task.dependencies) || task.dependencies.some((item) => item.requiredState !== "accepted"))
			throw new Error("Invalid dependencies");
		if (
			!Number.isSafeInteger(task.revision) ||
			task.revision < 1 ||
			!Number.isSafeInteger(task.budgetTokens) ||
			(taskKind(task) === "executable" ? task.budgetTokens <= 0 : task.budgetTokens !== 0) ||
			!Number.isSafeInteger(task.maxDepth) ||
			task.maxDepth < 0 ||
			!Number.isSafeInteger(task.maxConcurrent) ||
			(taskKind(task) === "executable" ? task.maxConcurrent < 1 : task.maxConcurrent !== 0)
		) {
			throw new Error("Invalid task revision or limits");
		}
		validAuthority(task.authority);
		if (
			taskKind(task) === "container" &&
			(task.acceptance.length !== 0 ||
				task.maxDepth !== 0 ||
				task.authority.paths.length !== 0 ||
				task.authority.tools.length !== 0 ||
				task.authority.readRepository ||
				task.authority.writeWorkspace ||
				task.authority.commitBranch ||
				task.authority.integrateBranch)
		)
			throw new Error("Container task cannot hold execution authority");
		const taskEvent: GovernanceEventInput = {
			type: task.revision === 1 ? "task.created" : "task.revised",
			actor,
			taskId: task.taskId,
			runId: null,
			delegationId: null,
			payload: { value: task },
		};
		let evaluation: ApprovalEvaluation | undefined;
		this.store.append(taskEvent, (state) => {
			if (kind === "internal") {
				// Only an active, human-approved baseline may create internal work,
				// and internal work is always a fresh revision-1 task.
				if (state.projectStatus !== "ACTIVE" || !state.projectApproved?.delegationPolicy.allowInternalTasks)
					throw new Error("Project does not authorize internal tasks");
				if (task.revision !== 1 || state.tasks[task.taskId])
					throw new Error("Task revisions require human approval");
			}
			if (
				kind === "revision" &&
				(!state.tasks[task.taskId] || task.revision !== state.tasks[task.taskId].revision + 1)
			)
				throw new Error("Task revisions require an existing task and the next revision");
			if (state.projectStatus === "ACTIVE" && state.projectApproved) {
				// A Task outside the baseline is refused here and the refusal is written
				// to the ledger, so the attempt is visible rather than silently missing.
				// The refusal carries the diagnosis of what exceeds the baseline, which
				// is what a human needs in order to decide: revise the baseline first,
				// or drop the Task. Nothing is created, so there is nothing that could
				// be mistaken for approved work.
				projectAdmitsTask(state.projectApproved, task);
			}
			const prior = state.tasks[task.taskId];
			if ((!prior && task.revision !== 1) || (prior && task.revision !== prior.revision + 1))
				throw new Error("Invalid task revision");
			if (prior && taskKind(prior) !== taskKind(task)) throw new Error("Task kind cannot change after creation");
			const parent = task.parentTaskId ? state.tasks[task.parentTaskId] : null;
			if (task.parentTaskId && (!parent || taskKind(parent) !== "container"))
				throw new Error("Parent must be an existing container task");
			if (parent && task.scope.some((item) => !parent.scope.includes(item)))
				throw new Error("Child task scope exceeds parent scope");
			if (
				taskKind(task) === "container" &&
				Object.values(state.tasks).some(
					(child) => child.parentTaskId === task.taskId && child.scope.some((item) => !task.scope.includes(item)),
				)
			)
				throw new Error("Existing child task scope exceeds revised parent scope");
			const proposed = { ...state.tasks, [task.taskId]: task };
			const visiting = new Set<string>();
			const visited = new Set<string>();
			const checkGraph = (candidateId: string): void => {
				if (visiting.has(candidateId)) throw new Error("Task hierarchy or dependency cycle");
				if (visited.has(candidateId)) return;
				visiting.add(candidateId);
				const candidate = proposed[candidateId];
				for (const dependency of candidate.dependencies) {
					if (!proposed[dependency.taskId]) throw new Error("Invalid task dependency");
					checkGraph(dependency.taskId);
				}
				if (taskKind(candidate) === "container")
					for (const child of Object.values(proposed).filter((entry) => entry.parentTaskId === candidateId))
						checkGraph(child.taskId);
				visiting.delete(candidateId);
				visited.add(candidateId);
			};
			for (const candidateId of Object.keys(proposed)) checkGraph(candidateId);
			// Org deny rules are evaluated first and can never be out-voted by a
			// project rule. A broken org file fails closed: the task is refused.
			let effectivePolicy: ReturnType<typeof mergeOrgDeny>;
			try {
				effectivePolicy = mergeOrgDeny(
					loadOrgApprovalPolicy(),
					state.projectStatus === "ACTIVE" ? state.projectApproved?.approvalPolicy : undefined,
				);
			} catch (error) {
				throw new Error(`Org approval policy invalid: ${error instanceof Error ? error.message : String(error)}`);
			}
			evaluation = evaluateTaskApproval(
				effectivePolicy,
				state.projectStatus === "ACTIVE" ? (state.projectApproved?.revision ?? null) : null,
				task,
				kind,
				// The approved baseline is the yardstick: a Task inside it needs no
				// second signature, and a Task outside it is told exactly what to fix.
				state.projectStatus === "ACTIVE" ? (state.projectApproved ?? null) : null,
			);
			taskEvent.payload.approvalEvaluation = evaluation;
			// Budget is a reservation, not a spend, and only a reserving Task holds one.
			// A Task that would not fit even once approved is refused now: leaving it to
			// wait for a human who can only reject it wastes their attention.
			//
			// A revision replaces the reservation of the revision it supersedes rather
			// than adding a second one, so the previous revision's share is subtracted
			// before the new one is checked.
			if (state.projectStatus === "ACTIVE" && state.projectApproved && evaluation.effect !== "deny") {
				const superseded = state.approved[task.taskId] !== undefined ? taskBudget(task) : 0;
				const allocated = reservedBudget(state) - superseded;
				if (allocated + taskBudget(task) > state.projectApproved.resourceLimits.budgetTokens)
					throw new Error("Project task budget exceeded");
			}
			if (evaluation.effect === "deny") {
				taskEvent.type = "task.creation-denied";
				taskEvent.payload = { approvalEvaluation: evaluation, requestedTask: task };
			} else if (evaluation.effect === "auto") {
				taskEvent.payload.autoApproved = true;
				taskEvent.payload.projectRevision = evaluation.projectRevision;
			}
		});
		if (!evaluation) throw new Error("Task approval evaluation failed");
		if (evaluation.effect === "deny") throw new Error(`Task denied by approval rule ${evaluation.ruleId}`);
		if (evaluation.effect === "ask")
			this.requestDecision(task.taskId, "task", `Approve task revision ${task.revision}`, actor);
		return evaluation;
	}

	requestDecision(taskId: string, kind: Decision["kind"], request: string, requester: string): Decision {
		const state = this.getState();
		const task = state.tasks[taskId];
		if (!task) throw new Error("Unknown task");
		const decision: Decision = {
			decisionId: id("D"),
			taskId,
			revision: task.revision,
			kind,
			request,
			requester,
			result: "pending",
			actor: null,
			scope: null,
			expiresAt: null,
			evidence: [],
		};
		this.store.append({
			type: "decision.requested",
			actor: requester,
			taskId,
			runId: null,
			delegationId: null,
			payload: { value: decision },
		});
		return decision;
	}

	recordDecision(
		decisionId: string,
		result: "approved" | "rejected",
		actor: string,
		scope: string,
		expiresAt: string | null,
		evidence: string[],
	): Decision {
		nonempty(actor, "actor");
		nonempty(scope, "scope");
		if (expiresAt !== null && (!Number.isFinite(Date.parse(expiresAt)) || Date.parse(expiresAt) <= Date.now()))
			throw new Error("Decision expiry must be a future timestamp");
		let recorded: Decision | undefined;
		const event: GovernanceEventInput = {
			type: "decision.recorded",
			actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: { value: null as Decision | null },
		};
		this.store.append(event, (state) => {
			const prior = state.decisions[decisionId];
			if (!prior || prior.result !== "pending") throw new Error("Decision is not pending");
			if (state.tasks[prior.taskId]?.revision !== prior.revision) throw new Error("Decision task revision is stale");
			recorded = { ...prior, result, actor, scope, expiresAt, evidence };
			event.taskId = prior.taskId;
			event.payload.value = recorded;
		});
		if (!recorded) throw new Error("Decision transition failed");
		return recorded;
	}

	approveTask(taskId: string, decisionId: string, actor: string): void {
		const state = this.getState();
		const task = state.tasks[taskId];
		const decision = state.decisions[decisionId];
		if (
			!task ||
			!decision ||
			decision.taskId !== taskId ||
			decision.revision !== task.revision ||
			decision.kind !== "task" ||
			decision.scope !== "task revision" ||
			decision.result !== "approved" ||
			(decision.expiresAt !== null && Date.parse(decision.expiresAt) <= Date.now())
		)
			throw new Error("Valid task approval is required");
		this.store.append(
			{
				type: "task.approved",
				actor,
				taskId,
				runId: null,
				delegationId: null,
				payload: { revision: task.revision, decisionId },
			},
			(fresh) => {
				if (fresh.events.some((event) => event.type === "project.initialized")) {
					if (fresh.projectStatus !== "ACTIVE" || !fresh.projectApproved)
						throw new Error("Approved active project baseline required");
					projectAdmitsTask(fresh.projectApproved, task);
					// Approval is where the reservation begins, so this is where the limit
					// is enforced for Tasks that waited for a human. A revision replaces the
					// reservation of the revision it supersedes instead of adding a second.
					const superseded = fresh.approved[taskId] !== undefined ? taskBudget(task) : 0;
					const committed = reservedBudget(fresh) - superseded;
					if (committed + taskBudget(task) > fresh.projectApproved.resourceLimits.budgetTokens)
						throw new Error("Project task budget exceeded");
				}
				if (
					fresh.tasks[taskId]?.revision !== task.revision ||
					fresh.decisions[decisionId]?.result !== "approved" ||
					(fresh.decisions[decisionId]?.expiresAt !== null &&
						Date.parse(fresh.decisions[decisionId].expiresAt ?? "") <= Date.now())
				)
					throw new Error("Stale task approval");
			},
		);
	}

	bindRunSession(runId: string, sessionId: string, sessionFile: string, parentSessionFile: string): Run {
		nonempty(sessionId, "session ID");
		nonempty(sessionFile, "session file");
		nonempty(parentSessionFile, "parent session file");
		const current = this.getState();
		const bound = current.events.some(
			(event) =>
				event.type === "run.session-bound" &&
				event.runId === runId &&
				event.payload.sessionId === sessionId &&
				event.payload.sessionFile === sessionFile &&
				event.payload.parentSessionFile === parentSessionFile,
		);
		if (bound && current.runs[runId]?.sessionRef === sessionFile) return current.runs[runId];
		let updated: Run | undefined;
		const event: GovernanceEventInput = {
			type: "run.session-bound",
			actor: `pi:${sessionId}`,
			taskId: null,
			runId,
			delegationId: null,
			sessionId,
			payload: { value: null, sessionId, sessionFile, parentSessionFile },
		};
		this.store.append(event, (state) => {
			const run = state.runs[runId];
			const observed = state.events
				.filter(
					(entry) =>
						entry.type === "agent.session-observed" &&
						entry.payload.sessionId === sessionId &&
						entry.payload.sessionFile === sessionFile &&
						entry.payload.parentSessionFile === parentSessionFile,
				)
				.at(-1);
			const native = run ? readNativeRunStatus(run) : null;
			if (
				!run ||
				!run.nativeRunId ||
				!observed ||
				run.parentSessionRef !== parentSessionFile ||
				!native?.available ||
				native.sessionFile !== sessionFile ||
				(run.sessionRef !== null && run.sessionRef !== sessionFile) ||
				Object.values(state.runs).some(
					(candidate) => candidate.runId !== runId && candidate.sessionRef === sessionFile,
				) ||
				state.events.some(
					(entry) =>
						entry.type === "run.session-bound" &&
						(entry.payload.sessionId === sessionId || entry.payload.sessionFile === sessionFile) &&
						entry.runId !== runId,
				)
			)
				refuse(
					"authority-escalation",
					"Child session cannot be bound to this Run",
					"bind child session",
					{ sessionId, sessionFile, parentSessionFile, nativeReason: native?.reason ?? null },
					{ taskId: run?.taskId ?? null, runId },
				);
			updated = { ...run, sessionRef: sessionFile };
			event.taskId = run.taskId;
			event.delegationId = run.delegationId;
			event.payload.value = updated;
			event.payload.nativeRunId = run.nativeRunId;
			event.payload.evidence = { source: "native-status", statusSha256: native.statusSha256 ?? null };
		});
		if (!updated) throw new Error("Child session binding failed");
		return updated;
	}

	authorizeDelegation(
		input: Omit<
			Delegation,
			"delegationId" | "depth" | "parentDelegationId" | "requesterId" | "requesterSessionId" | "requesterSessionFile"
		>,
		actor: string,
		origin?: DelegationSessionOrigin,
	): Delegation {
		if (input.parentRunId !== null) throw new Error("Child Agent delegation is disabled in the one-level model");
		validAuthority(input.authority);
		nonempty(input.objective, "objective");
		const delegation: Delegation = {
			...input,
			delegationId: id("G"),
			parentDelegationId: null,
			requesterId: actor,
			...(origin ? { requesterSessionId: origin.sessionId, requesterSessionFile: origin.sessionFile } : {}),
			depth: 0,
		};
		this.store.append(
			{
				type: "delegation.authorized",
				actor,
				taskId: input.taskId,
				runId: input.parentRunId,
				delegationId: delegation.delegationId,
				sessionId: origin?.sessionId ?? null,
				payload: { value: delegation },
			},
			(state) => {
				if (actor.startsWith("pi:") || origin) {
					const observed =
						origin &&
						state.events
							.filter(
								(entry) =>
									entry.type === "agent.session-observed" &&
									entry.payload.sessionId === origin.sessionId &&
									entry.payload.sessionFile === origin.sessionFile,
							)
							.at(-1);
					const bound =
						origin?.parentRunId &&
						state.events.some(
							(entry) =>
								entry.type === "run.session-bound" &&
								entry.runId === origin.parentRunId &&
								entry.payload.sessionId === origin.sessionId &&
								entry.payload.sessionFile === origin.sessionFile,
						);
					if (
						!origin ||
						actor !== `pi:${origin.sessionId}` ||
						!observed ||
						origin.parentRunId !== input.parentRunId ||
						(origin.parentRunId
							? !bound ||
								observed.payload.parentSessionFile !== state.runs[origin.parentRunId]?.parentSessionRef ||
								state.runs[origin.parentRunId]?.sessionRef !== origin.sessionFile
							: observed.payload.parentSessionFile !== null ||
								Object.values(state.runs).some(
									(run) =>
										run.sessionRef === origin.sessionFile ||
										readNativeRunStatus(run).sessionFile === origin.sessionFile,
								))
					)
						refuse(
							"authority-escalation",
							"Delegation requester session is not bound to parent Run",
							"authorize delegation",
							{ actor, origin: origin ?? null },
							{ taskId: input.taskId, runId: input.parentRunId },
						);
				}
				const task = state.tasks[input.taskId];
				if (!task) throw new Error("Unknown task");
				taskReady(state, task);
				let ceiling = task.authority;
				let budget = task.budgetTokens;
				if (input.parentRunId) {
					const parent = state.runs[input.parentRunId];
					if (!parent || parent.taskId !== input.taskId || !active(parent.state))
						throw new Error("Invalid parent Run");
					const parentDelegation = state.delegations[parent.delegationId];
					delegation.parentDelegationId = parentDelegation.delegationId;
					delegation.depth = parentDelegation.depth + 1;
					ceiling = parentDelegation.authority;
					budget = parentDelegation.budgetTokens;
				}
				if (delegation.depth > task.maxDepth || !subset(input.authority, ceiling))
					refuse(
						"authority-escalation",
						"Delegation exceeds authority or depth",
						"authorize delegation",
						{
							depth: delegation.depth,
							maxDepth: task.maxDepth,
							requestedAuthority: input.authority,
							ceiling,
						},
						{ taskId: input.taskId, runId: input.parentRunId, delegationId: delegation.delegationId },
					);
				const allocated = Object.values(state.delegations)
					.filter((d) => d.taskId === input.taskId && d.parentRunId === input.parentRunId)
					// A delegation reserves capacity until its attempt settles. Keep an
					// unstarted delegation reserved; a completed attempt releases it.
					.filter((d) => {
						const attempts = Object.values(state.runs).filter((run) => run.delegationId === d.delegationId);
						return attempts.length === 0 || attempts.some((run) => active(run.state));
					})
					.reduce((sum, d) => sum + d.budgetTokens, 0);
				if (
					!Number.isSafeInteger(input.budgetTokens) ||
					input.budgetTokens <= 0 ||
					allocated + input.budgetTokens > budget
				)
					refuse(
						"delegation-limit",
						"Delegation budget exceeded",
						"authorize delegation",
						{ requested: input.budgetTokens, allocated, ceiling: budget },
						{ taskId: input.taskId, runId: input.parentRunId, delegationId: delegation.delegationId },
					);
				const concurrent = Object.values(state.runs).filter(
					(run) => run.taskId === input.taskId && active(run.state),
				).length;
				if (concurrent >= task.maxConcurrent)
					refuse(
						"delegation-limit",
						"Task concurrency limit reached",
						"authorize delegation",
						{ concurrent, maxConcurrent: task.maxConcurrent },
						{ taskId: input.taskId, runId: input.parentRunId, delegationId: delegation.delegationId },
					);
			},
		);
		return delegation;
	}

	cancelUnstartedDelegation(delegationId: string, reason: string): void {
		nonempty(reason, "cancellation reason");
		this.store.append(
			{
				type: "delegation.cancelled",
				actor: "governance",
				taskId: null,
				runId: null,
				delegationId,
				payload: { reason },
			},
			(state) => {
				const delegation = state.delegations[delegationId];
				if (!delegation || Object.values(state.runs).some((run) => run.delegationId === delegationId))
					throw new Error("Only an unstarted delegation can be cancelled");
			},
		);
	}

	createRun(
		delegationId: string,
		harness: string,
		sessionRef: string | null,
		workspaceId: string | null,
		retryOf: string | null,
		parentSessionRef: string | null = null,
		routing?: NonNullable<Run["routing"]>,
	): Run {
		const state = this.getState();
		const delegation = state.delegations[delegationId];
		if (!delegation) throw new Error("Unknown delegation");
		const run: Run = {
			runId: id("R"),
			taskId: delegation.taskId,
			delegationId,
			executorId: delegation.executorId,
			harness,
			state: "CREATED",
			sessionRef,
			parentSessionRef,
			nativeRunId: null,
			nativeAsyncDir: null,
			workspaceId,
			retryOf,
			usageTokens: null,
			costUsd: null,
			...(routing ? { routing: { ...routing } } : {}),
		};
		this.store.append(
			{
				type: "run.created",
				actor: delegation.executorId,
				taskId: run.taskId,
				runId: run.runId,
				delegationId,
				payload: { value: run },
			},
			(fresh) => {
				if (!fresh.delegations[delegationId]) throw new Error("Delegation missing");
				const task = fresh.tasks[run.taskId];
				if (!task) throw new Error("Task missing");
				taskReady(fresh, task);
				// A settled delegation releases its reservation. Starting another Run
				// under that same delegation reserves it again, so recheck the Task cap
				// against other unstarted and active delegations before admitting it.
				const allocated = Object.values(fresh.delegations)
					.filter((entry) => entry.taskId === run.taskId && entry.parentRunId === delegation.parentRunId)
					.filter((entry) => {
						if (entry.delegationId === delegationId) return true;
						const attempts = Object.values(fresh.runs).filter(
							(attempt) => attempt.delegationId === entry.delegationId,
						);
						return attempts.length === 0 || attempts.some((attempt) => active(attempt.state));
					})
					.reduce((sum, entry) => sum + entry.budgetTokens, 0);
				if (allocated > task.budgetTokens) throw new Error("Task delegation budget exceeded by retry");
				if (retryOf && (fresh.runs[retryOf]?.taskId !== run.taskId || active(fresh.runs[retryOf].state)))
					throw new Error("Invalid retry Run");
				if (workspaceId && fresh.workspaces[workspaceId]?.taskId !== run.taskId)
					throw new Error("Invalid workspace");
				if (
					Object.values(fresh.runs).filter((entry) => entry.taskId === run.taskId && active(entry.state)).length >=
					task.maxConcurrent
				)
					throw new Error("Task concurrency limit reached");
				if (routing) {
					if (routing.agent && routing.agent !== fresh.delegations[delegationId].executorId)
						throw new Error("Run route Agent differs from authorized delegation");
					if (
						routing.maxAllocationTokens !== null &&
						routing.maxAllocationTokens !== undefined &&
						fresh.delegations[delegationId].budgetTokens > routing.maxAllocationTokens
					)
						throw new Error("Agent allocation exceeds subagent policy limit");
					if (
						routing.maxRunsPerTask !== null &&
						routing.maxRunsPerTask !== undefined &&
						Object.values(fresh.runs).filter((entry) => entry.taskId === run.taskId).length >=
							routing.maxRunsPerTask
					)
						throw new Error("Task cumulative Run limit reached");
					const activeRuns = Object.values(fresh.runs).filter((entry) => active(entry.state));
					const projectLimit = fresh.projectApproved?.delegationPolicy.maxConcurrent ?? Infinity;
					if (activeRuns.length >= Math.min(routing.maxConcurrent, projectLimit))
						throw new Error("Project subagent concurrency limit reached");
					if (
						activeRuns.filter((entry) =>
							routing.agent ? entry.routing?.agent === routing.agent : entry.routing?.tier === routing.tier,
						).length >= (routing.roleMaxConcurrent ?? routing.tierMaxConcurrent ?? Infinity)
					)
						throw new Error(
							routing.agent
								? `Subagent ${routing.agent} concurrency limit reached`
								: `Subagent tier ${routing.tier} concurrency limit reached`,
						);
				}
			},
		);
		return run;
	}

	updateRun(
		runId: string,
		state: RunState,
		patch: Partial<Pick<Run, "nativeRunId" | "nativeAsyncDir" | "sessionRef" | "usageTokens" | "costUsd">> = {},
		proof?: string,
		actor = "governance",
		evidence?: Record<string, unknown>,
	): Run {
		let updated: Run | undefined;
		const eventType: Record<RunState, string> = {
			CREATED: "run.created",
			RUNNING: "run.started",
			PAUSED: "run.paused",
			INTERRUPTED: "run.interrupted",
			SUCCEEDED: "run.finished",
			FAILED: "run.failed",
			CANCELLED: "run.cancelled",
		};
		const event: GovernanceEventInput = {
			type: eventType[state],
			actor,
			taskId: null,
			runId,
			delegationId: null,
			payload: { value: null as Run | null, ...(proof ? { proof } : {}), ...(evidence ? { evidence } : {}) },
		};
		this.store.append(event, (snapshot) => {
			const old = snapshot.runs[runId];
			if (!old) throw new Error("Unknown Run");
			const allowed: Record<RunState, RunState[]> = {
				CREATED: ["RUNNING", "FAILED", "CANCELLED", "INTERRUPTED"],
				RUNNING: ["PAUSED", "INTERRUPTED", "SUCCEEDED", "FAILED", "CANCELLED"],
				PAUSED: ["RUNNING", "CANCELLED", "INTERRUPTED"],
				INTERRUPTED: ["RUNNING", "FAILED", "CANCELLED"],
				SUCCEEDED: [],
				FAILED: [],
				CANCELLED: [],
			};
			if (!allowed[old.state].includes(state)) throw new Error(`Invalid Run transition ${old.state} -> ${state}`);
			if (state === "RUNNING" && (old.state === "PAUSED" || old.state === "INTERRUPTED")) event.type = "run.resumed";
			updated = { ...old, ...patch, state };
			if (old.sessionRef && patch.sessionRef && old.sessionRef !== patch.sessionRef)
				throw new Error("Run session binding cannot change");
			event.taskId = old.taskId;
			event.delegationId = old.delegationId;
			event.payload.value = updated;
		});
		if (!updated) throw new Error("Run transition failed");
		return updated;
	}

	/**
	 * Cancel a Task: stop what is running, record why, release what it reserved.
	 *
	 * Nothing is deleted. The contract, the Runs and the approvals stay in the ledger
	 * as history; what changes is that the Task no longer reserves budget and no
	 * longer authorizes a delegation. `cancelRun` has to succeed first for every
	 * active Run, so a Task is never marked cancelled while a child is still working
	 * — "cancel requested" and "execution stopped" are different facts.
	 */
	cancelTask(taskId: string, reason: string, actor: string, options: { cancelRuns?: boolean } = {}): TaskCancellation {
		nonempty(reason, "reason");
		const state = this.getState();
		const task = state.tasks[taskId];
		if (!task) throw new Error("Unknown task");
		if (taskKind(task) === "container") throw new Error("Container tasks cannot be cancelled directly");
		if (state.cancelled[taskId]) throw new Error("Task is already cancelled");
		if (state.accepted[taskId]) throw new Error("Task is already accepted; acceptance is a terminal outcome");
		const activeRuns = Object.values(state.runs).filter((run) => run.taskId === taskId && active(run.state));
		if (activeRuns.length && !options.cancelRuns)
			throw new Error(
				`Task has ${activeRuns.length} active Run(s). Stop each with \`gov run cancel\`, which confirms the process ` +
					"exited before the cancellation is recorded, then cancel the Task.",
			);
		// The runs must already be stopped. Cancelling them here would fail anyway,
		// because `cancelRun` refuses while the native process is alive - the refusal
		// is the point: a cancelled Task must not free slots still in use.
		for (const run of activeRuns) this.cancelRun(run.runId, `Task ${taskId} cancelled: ${reason}`, actor);
		const releasedTokens = state.approved[taskId] === task.revision ? taskBudget(task) : 0;
		let recorded: TaskCancellation | undefined;
		const event: GovernanceEventInput = {
			type: "task.cancelled",
			actor,
			taskId,
			runId: null,
			delegationId: null,
			payload: { value: null as TaskCancellation | null },
		};
		this.store.append(event, (fresh) => {
			if (!fresh.tasks[taskId]) throw new Error("Unknown task");
			if (fresh.cancelled[taskId]) throw new Error("Task is already cancelled");
			if (fresh.accepted[taskId]) throw new Error("Task is already accepted");
			if (Object.values(fresh.runs).some((run) => run.taskId === taskId && active(run.state)))
				throw new Error("Task still has an active Run");
			recorded = {
				taskId,
				revision: fresh.tasks[taskId].revision,
				actor,
				at: new Date().toISOString(),
				reason,
				cancelledRunIds: activeRuns.map((run) => run.runId),
				releasedTokens,
			};
			event.payload.value = recorded;
		});
		if (!recorded) throw new Error("Task cancellation failed");
		return recorded;
	}

	/**
	 * Record a cancelled Run, but only once nothing is still running.
	 *
	 * Ordering is the point. Recording `CANCELLED` before the process stopped is what
	 * let a child keep working for ten more minutes - 853,137 tokens - while the kernel
	 * believed its concurrency slot was free. A ledger that says stopped while the child
	 * still writes is worse than no cancellation: it hides the cost and miscounts
	 * capacity.
	 *
	 * Stopping the process is the caller's job because it is asynchronous (pi-subagents
	 * exposes it over RPC), and this method is deliberately synchronous so that a wrong
	 * order cannot be expressed. A caller that cannot stop must not free the slot, so a
	 * Run still proven running is refused rather than recorded.
	 */
	cancelRun(runId: string, reason: string, actor: string): Run {
		nonempty(reason, "reason");
		const run = this.getState().runs[runId];
		if (!run) throw new Error("Unknown Run");
		if (!active(run.state)) throw new Error(`Run is already ${run.state}`);
		if (nativeRunLiveness(run) === "running")
			throw new Error(
				`Run ${runId} is still running natively. Stop the process first (control it over RPC), then record the ` +
					"cancellation; recording it now would free a concurrency slot that is still in use.",
			);
		const terminal = readNativeRunStatus(run);
		if (terminal.terminalOutcome)
			throw new Error(
				`Run ${runId} already has native outcome ${terminal.terminalOutcome}; reconcile that outcome instead of recording cancellation`,
			);
		// Captured while the sidecar still exists: once the process is gone the figure is
		// unavailable, which is how 3,293,360 tokens were once recorded as null.
		let usage = run.usageTokens;
		let cost = run.costUsd;
		try {
			const native = readNativeRunStatus(run);
			if (native.available) {
				usage = native.totalTokens ?? usage;
				cost = native.costUsd ?? cost;
			}
		} catch {
			/* an unreadable figure stays null, which `gov status` reports as unknown */
		}
		return this.updateRun(
			runId,
			"CANCELLED",
			usage === run.usageTokens && cost === run.costUsd ? {} : { usageTokens: usage, costUsd: cost },
			`Cancelled: ${reason}`,
			actor,
		);
	}

	submitDeliverable(
		input: Omit<Deliverable, "deliverableId" | "revision" | "evidence" | "runId" | "sessionId"> & { runId: string },
		repo: string,
	): Deliverable {
		const state = this.getState();
		const task = state.tasks[input.taskId];
		if (!task || state.runs[input.runId]?.taskId !== input.taskId || taskKind(task) === "container")
			throw new Error("Invalid deliverable task or Run");
		if (state.runs[input.runId].state !== "SUCCEEDED") throw new Error("Run must succeed before delivery");
		nonempty(input.commit, "commit");
		nonempty(input.summary, "summary");
		assertStructuredTests(input.tests);
		if (!Array.isArray(input.issues) || !Array.isArray(input.logs))
			throw new Error("Delivery requires test results, issues, and log references");
		const workspaceId = state.runs[input.runId].workspaceId;
		// Verification happens before the event so a rejected delivery leaves no
		// record claiming success. The facts are read from Git, not from `input`.
		// It runs before the Workspace HEAD comparison so an unknown commit is
		// reported as unknown instead of as a mismatch.
		const evidence = verifyDeliverableCommit(
			repo,
			input.commit,
			workspaceId ? state.workspaces[workspaceId].baseCommit : null,
		);
		if (workspaceId) {
			const workspace = state.workspaces[workspaceId];
			const head = execFileSync("git", ["rev-parse", "HEAD"], { cwd: workspace.path, encoding: "utf8" }).trim();
			if (head !== input.commit)
				refuse(
					"deliverable-unverified",
					"Deliverable commit differs from workspace HEAD",
					"submit deliverable",
					{ named: input.commit, workspaceHead: head },
					{ taskId: input.taskId, runId: input.runId, delegationId: state.runs[input.runId].delegationId },
				);
		}
		// Verify every named log before the event, so a report pointing at a log that
		// was never committed is refused instead of recorded as if it passed.
		const tests = input.tests.map((report) => {
			const verified = verifyTestLog(repo, input.commit, report);
			return verified ? { ...report, verified } : report;
		});
		const deliverable: Deliverable = {
			...input,
			tests,
			revision: task.revision,
			deliverableId: id("A"),
			evidence,
		};
		this.store.append(
			{
				type: "deliverable.submitted",
				actor: state.runs[input.runId].executorId,
				taskId: input.taskId,
				runId: input.runId,
				delegationId: state.runs[input.runId].delegationId,
				payload: { value: deliverable },
			},
			(fresh) => {
				if (
					fresh.tasks[input.taskId]?.revision !== deliverable.revision ||
					fresh.runs[input.runId]?.state !== "SUCCEEDED"
				)
					throw new Error("Deliverable source changed");
				if (workspaceId) {
					const head = execFileSync("git", ["rev-parse", "HEAD"], {
						cwd: fresh.workspaces[workspaceId].path,
						encoding: "utf8",
					}).trim();
					if (head !== input.commit) throw new Error("Deliverable commit changed");
				}
			},
		);
		return deliverable;
	}

	submitMainDeliverable(
		input: Omit<Deliverable, "deliverableId" | "revision" | "evidence" | "runId" | "sessionId">,
		repo: string,
		origin: DelegationSessionOrigin,
	): Deliverable {
		if (origin.parentRunId !== null) throw new Error("Only a main Pi session may deliver directly");
		const state = this.getState();
		const task = state.tasks[input.taskId];
		if (!task || taskKind(task) !== "executable") throw new Error("Executable Task required for direct delivery");
		if (!task.authority.commitBranch) throw new Error("Task does not authorize a direct Git delivery");
		if (
			!state.events.some(
				(event) =>
					event.type === "agent.session-observed" &&
					event.payload.sessionId === origin.sessionId &&
					event.payload.sessionFile === origin.sessionFile &&
					event.payload.parentSessionFile === null,
			)
		)
			throw new Error("Main Pi session has not been observed");
		const activation = state.events
			.filter((event) => event.type === "session.task-activated" && event.payload.sessionId === origin.sessionId)
			.at(-1);
		if (activation?.taskId !== input.taskId) throw new Error("Current main session is not activated for this Task");
		taskReady(state, task);
		nonempty(input.commit, "commit");
		nonempty(input.summary, "summary");
		assertStructuredTests(input.tests);
		if (!Array.isArray(input.issues) || !Array.isArray(input.logs))
			throw new Error("Delivery requires test results, issues, and log references");
		const evidence = verifyDeliverableCommit(repo, input.commit, null);
		const head = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo, encoding: "utf8" }).trim();
		if (head !== input.commit) throw new Error("Direct deliverable must be the current repository HEAD");
		if (
			evidence.files.some(
				(file) =>
					!task.authority.paths.some(
						(allowed) => file.path === allowed || file.path.startsWith(`${allowed.replace(/\/$/, "")}/`),
					),
			)
		)
			throw new Error("Direct deliverable changes files outside Task authority");
		const tests = input.tests.map((report) => {
			const verified = verifyTestLog(repo, input.commit, report);
			return verified ? { ...report, verified } : report;
		});
		const deliverable: Deliverable = {
			...input,
			runId: null,
			sessionId: origin.sessionId,
			tests,
			revision: task.revision,
			deliverableId: id("A"),
			evidence,
		};
		this.store.append(
			{
				type: "deliverable.submitted",
				actor: `pi:${origin.sessionId}`,
				taskId: input.taskId,
				runId: null,
				delegationId: null,
				sessionId: origin.sessionId,
				payload: { value: deliverable, source: "main-session" },
			},
			(fresh) => {
				if (
					fresh.tasks[input.taskId]?.revision !== deliverable.revision ||
					fresh.approved[input.taskId] !== deliverable.revision ||
					fresh.events
						.filter(
							(event) => event.type === "session.task-activated" && event.payload.sessionId === origin.sessionId,
						)
						.at(-1)?.taskId !== input.taskId
				)
					throw new Error("Direct delivery source changed");
			},
		);
		return deliverable;
	}

	/**
	 * Record that someone checked a delivery against its acceptance criteria.
	 *
	 * The ruling separates two questions that one string used to answer together: who is
	 * verifying, and what makes that independent. Both are now read from the ledger.
	 *
	 * A delivery produced by an agent Run must be verified by a *different* Run that
	 * finished successfully, belongs to the same Task, has a different executor identity,
	 * and whose role carries the `verify` capability. Comparing Run IDs alone would pass
	 * two executions of the same agent off as independent; comparing executor identities
	 * alone would forbid an agent from ever verifying twice, which is not the point. Both
	 * must differ.
	 *
	 * A Run that names no `verifierRunId` is a manual verification. It is accepted only
	 * when the delivery has no producing Run, and it is recorded with the assurance the
	 * identity mechanism could actually prove - never as an independent review.
	 */
	recordVerification(
		deliverableId: string,
		verifier: string,
		criteria: Verification["criteria"],
		verifierRunId?: string,
		identity?: { source: IdentitySource; assurance: IdentityAssurance },
	): Verification {
		const state = this.getState();
		const artifact = state.deliverables[deliverableId];
		if (!artifact) throw new Error("Unknown deliverable");
		const producerRun = artifact.runId ? state.runs[artifact.runId] : undefined;
		// The producing identity: the Run's executor when there is one, otherwise whoever
		// submitted the delivery. A submission with neither is not verifiable at all.
		const producerIdentity = producerRun
			? producerRun.executorId
			: artifact.sessionId
				? `pi-session:${artifact.sessionId}`
				: null;
		if (!producerIdentity) throw new Error("Deliverable has no identifiable producer");

		let identity_: string;
		let kind: "independent-run" | "manual-unverified";
		let recordedSource: IdentitySource;
		let recordedAssurance: IdentityAssurance;
		if (verifierRunId) {
			const run = state.runs[verifierRunId];
			if (!run) throw new Error("Unknown verifier Run");
			// Only a finished Run can say what it found; a failed one found nothing usable.
			if (run.state !== "SUCCEEDED") throw new Error(`Verifier Run is ${run.state}, not SUCCEEDED`);
			if (run.taskId !== artifact.taskId) throw new Error("Verifier Run belongs to a different Task");
			// Same execution cannot check itself.
			if (run.runId === artifact.runId)
				throw new Error("Verifier Run produced this deliverable, so it cannot verify it");
			// Same executor identity cannot check itself either, even from another Run.
			if (run.executorId === producerRun?.executorId)
				throw new Error(
					"Verifier Run has the same executor identity as the Run that produced this deliverable, " +
						"so a different Run ID does not make the verification independent",
				);
			// The capability, not the name. A reviewer's authority is a fact recorded about
			// its role, and a role registered without it cannot verify however it is called.
			const role = state.agents[run.executorId];
			if (!role?.capabilities.includes("verify"))
				throw new Error(
					`Agent ${run.executorId} does not carry the verify capability, so its Run cannot verify a delivery`,
				);
			identity_ = `agent-run:${run.runId}`;
			kind = "independent-run";
			recordedSource = "governance-run";
			recordedAssurance = "governed";
		} else {
			// Manual path. A delivery an agent produced must not be waved through by a string
			// the agent itself can type, which is the whole defect being repaired here.
			if (artifact.runId)
				throw new Error(
					"Deliverable was produced by a Run; it must be verified by an independent Run, " +
						"not by a manual verification",
				);
			identity_ = verifier;
			kind = "manual-unverified";
			recordedSource = identity?.source ?? "unknown";
			recordedAssurance = identity?.assurance ?? "unverified";
		}
		if (producerIdentity === identity_ || !criteria.length)
			throw new Error("Independent verifier and criteria required");
		const task = state.tasks[artifact.taskId];
		if (!task || task.revision !== artifact.revision) throw new Error("Stale task revision");
		if (
			criteria.length !== task.acceptance.length ||
			criteria.some((entry, i) => entry.item !== task.acceptance[i] || !entry.evidence)
		)
			throw new Error("Verification does not cover acceptance criteria");
		const verification: Verification = {
			verificationId: id("V"),
			deliverableId,
			taskId: artifact.taskId,
			revision: artifact.revision,
			commit: artifact.commit,
			verifier: identity_,
			criteria,
			result: criteria.every((entry) => entry.passed) ? "passed" : "failed",
			producerRunId: artifact.runId,
			verifierRunId: verifierRunId ?? null,
			identitySource: recordedSource,
			identityAssurance: recordedAssurance,
			verificationKind: kind,
		};
		this.store.append({
			type: "verification.recorded",
			actor: identity_,
			taskId: artifact.taskId,
			runId: artifact.runId,
			delegationId: null,
			payload: { value: verification },
		});
		return verification;
	}

	acceptTask(taskId: string, verificationId: string, actor: string): void {
		const state = this.getState();
		const verification = state.verifications[verificationId];
		const task = state.tasks[taskId];
		if (task && taskKind(task) === "container") throw new Error("Container task is accepted through its children");
		if (
			!task ||
			!verification ||
			verification.taskId !== taskId ||
			verification.revision !== task.revision ||
			verification.result !== "passed"
		)
			throw new Error("Current passing verification required");
		const latest = Object.values(state.deliverables)
			.filter((entry) => entry.taskId === taskId)
			.at(-1);
		if (!latest || latest.deliverableId !== verification.deliverableId)
			throw new Error("Verification is not for the latest deliverable");
		const workspaceId = latest.runId ? state.runs[latest.runId]?.workspaceId : null;
		if (workspaceId) {
			const head = execFileSync("git", ["rev-parse", "HEAD"], {
				cwd: state.workspaces[workspaceId].path,
				encoding: "utf8",
			}).trim();
			if (head !== verification.commit) throw new Error("Verified commit is no longer workspace HEAD");
		}
		const source = state.deliverables[verification.deliverableId];
		const executorId = source.runId ? state.runs[source.runId]?.executorId : `pi:${source.sessionId}`;
		if (executorId === actor)
			refuse(
				"authority-escalation",
				"Executor cannot accept own work",
				"accept task",
				{
					executorId: actor,
					deliveredBy: executorId,
				},
				{ taskId },
			);
		this.store.append(
			{
				type: "task.accepted",
				actor,
				taskId,
				runId: null,
				delegationId: null,
				payload: { verificationId, commit: verification.commit, revision: task.revision },
			},
			(fresh) => {
				const current = fresh.verifications[verificationId];
				if (
					!current ||
					current.result !== "passed" ||
					current.revision !== fresh.tasks[taskId]?.revision ||
					!currentAcceptance({ ...fresh, accepted: { ...fresh.accepted, [taskId]: verificationId } }, taskId)
				)
					throw new Error("Acceptance evidence is stale");
			},
		);
	}

	registerWorkspace(workspace: Workspace, actor: string): void {
		this.store.append(
			{
				type: "workspace.registered",
				actor,
				taskId: workspace.taskId,
				runId: null,
				delegationId: null,
				payload: { value: workspace },
			},
			(state) => {
				if (
					!state.tasks[workspace.taskId] ||
					taskKind(state.tasks[workspace.taskId]) === "container" ||
					state.workspaces[workspace.workspaceId]
				)
					throw new Error("Invalid workspace registration");
			},
		);
	}

	leaseWorkspace(workspaceId: string, runId: string, until: string): void {
		let workspace: Workspace | undefined;
		const event: GovernanceEventInput = {
			type: "workspace.updated",
			actor: "governance",
			taskId: null,
			runId,
			delegationId: null,
			payload: { value: null as Workspace | null },
		};
		this.store.append(event, (state) => {
			const old = state.workspaces[workspaceId];
			const run = state.runs[runId];
			if (!old || !run || old.taskId !== run.taskId || !active(run.state))
				throw new Error("Invalid workspace lease");
			// A second Run entering a live Worktree would make "which Run wrote this
			// file" unanswerable, so the lease is a hard stop.
			if (old.holderRunId && old.holderRunId !== runId)
				refuse(
					"workspace-refused",
					"Workspace held by another Run; inspect and release it first",
					"lease workspace",
					{ holderRunId: old.holderRunId, leaseUntil: old.leaseUntil },
					{ taskId: old.taskId, runId },
				);
			workspace = { ...old, holderRunId: runId, leaseUntil: until };
			event.taskId = old.taskId;
			event.payload.value = workspace;
		});
		if (!workspace) throw new Error("Workspace lease failed");
	}

	releaseWorkspace(workspaceId: string, runId: string, actor: string, proof: string): void {
		nonempty(proof, "terminal proof");
		const event: GovernanceEventInput = {
			type: "workspace.updated",
			actor,
			taskId: null,
			runId,
			delegationId: null,
			payload: { value: null },
		};
		this.store.append(event, (state) => {
			const old = state.workspaces[workspaceId];
			const run = state.runs[runId];
			if (!old || old.holderRunId !== runId || !run || active(run.state))
				throw new Error("Workspace holder is not terminal");
			event.taskId = old.taskId;
			event.payload = { value: { ...old, holderRunId: null, leaseUntil: null }, proof };
		});
	}

	/**
	 * Records the captured evidence before anything is deleted. If the process dies
	 * after this event and before `finishWorkspaceDestroy`, the ledger shows a
	 * request with no outcome: destroy state is unknown, not silently complete.
	 */
	/**
	 * Record that a child is about to be launched, before it exists.
	 *
	 * The native side mints its own Run ID and accepts no substitute, so the process's
	 * identity cannot be written at creation time. This event exists to make the gap
	 * visible: a Run with this and no matching `bindExecutionAttempt` is a known unknown -
	 * we asked for a child and never learned what became of it - rather than a Run that
	 * looks idle. Guessing in either direction here has been expensive; the ledger says
	 * what happened and `probeExecutionAttempt` says what can be proven.
	 *
	 * Writes only what is known. `nativeRunId` and `pid` are deliberately absent: filling
	 * them with placeholders would make an unbound attempt look bound.
	 */
	requestExecutionAttempt(runId: string, executionAttemptId: string, actor: string): void {
		const run = this.getState().runs[runId];
		if (!run) throw new Error("Unknown Run");
		if (!active(run.state)) throw new Error(`Run is ${run.state}; only an active Run can launch a child`);
		// Idempotent: a retry of the same attempt must not produce a second intent, or a
		// later probe would see two attempts where only one was ever made.
		if (executionAttempts(this.getState(), runId).some((entry) => entry.executionAttemptId === executionAttemptId))
			return;
		this.store.append(
			{
				type: "run.execution-launch-requested",
				actor,
				taskId: run.taskId,
				runId,
				delegationId: run.delegationId,
				payload: { value: { executionAttemptId, at: Date.now() }, evidence: { executionAttemptId } },
			},
			() => {
				/* evidence-only: the Run's own state is untouched */
			},
		);
	}

	/**
	 * Record which native process an attempt turned out to be.
	 *
	 * Called as soon as the native Run ID is known and not later - the identity captured
	 * here (pid, PID namespace, process start time, boot id) is the only thing that can
	 * later distinguish a live child from a recycled pid. Capturing it late means capturing
	 * it after the process may already be gone.
	 */
	bindExecutionAttempt(
		runId: string,
		executionAttemptId: string,
		native: { nativeRunId: string; pid?: number },
		actor: string,
	): { bound: boolean; reason?: string } {
		const run = this.getState().runs[runId];
		if (!run) throw new Error("Unknown Run");
		const attempt = executionAttempts(this.getState(), runId).find(
			(entry) => entry.executionAttemptId === executionAttemptId,
		);
		// Binding an attempt that was never announced is a caller bug worth refusing: the
		// intent is what makes the binding meaningful, and inventing one here would hide
		// the ordering mistake rather than surface it.
		if (!attempt) return { bound: false, reason: "no matching run.execution-launch-requested" };
		if (attempt.bound) return { bound: true, reason: "already bound" }; // idempotent
		const identity = captureExecutionIdentity(native.pid);
		this.store.append(
			{
				type: "run.execution-bound",
				actor,
				taskId: run.taskId,
				runId,
				delegationId: run.delegationId,
				payload: {
					value: { executionAttemptId, nativeRunId: native.nativeRunId, at: Date.now(), ...identity },
					evidence: { executionAttemptId, nativeRunId: native.nativeRunId },
				},
			},
			() => {
				/* evidence-only: the binding describes which process, not how the Run went */
			},
		);
		return { bound: true };
	}

	/**
	 * Declare a Run lost: its child is provably gone, its outcome never learned.
	 *
	 * The verdict is required rather than inferred, because this is the one operation that
	 * frees a concurrency slot without knowing what happened. Inferring "dead" from the
	 * absence of evidence is what let a child run ten minutes under a freed slot; here the
	 * caller must have looked and found a positive sign of death.
	 *
	 * `usageTokens` is left null. The spend of a vanished child is unknown, and writing zero
	 * would make it look free in every projection.
	 */
	markExecutionLost(runId: string, verdict: "dead", reason: string, actor: string): Run {
		nonempty(reason, "reason");
		if (verdict !== "dead") throw new Error("markExecutionLost requires positive evidence of death");
		const run = this.getState().runs[runId];
		if (!run) throw new Error("Unknown Run");
		if (!active(run.state)) throw new Error(`Run is already ${run.state}`);
		const attempt = executionAttempts(this.getState(), runId).at(-1) ?? null;
		return this.updateRun(runId, "FAILED", {}, `Lost: ${reason}`, actor, { ...lostRunEvidence(attempt), reason });
	}

	requestWorkspaceDestroy(workspace: Workspace, evidence: WorkspaceDestroyEvidence, actor: string): void {
		this.store.append(
			{
				type: "workspace.destroy-requested",
				actor,
				taskId: workspace.taskId,
				runId: null,
				delegationId: null,
				payload: { value: workspace, evidence },
			},
			(state) => {
				const current = state.workspaces[workspace.workspaceId];
				if (!current) throw new Error("Unknown workspace");
				if (current.destroyedAt)
					refuse(
						"workspace-refused",
						"Workspace is already destroyed",
						"destroy workspace",
						{ destroyedAt: current.destroyedAt },
						{ taskId: current.taskId, runId: workspace.holderRunId },
					);
				if (current.holderRunId)
					refuse(
						"workspace-refused",
						`Workspace is still held by Run ${current.holderRunId}; release it first`,
						"destroy workspace",
						{ holderRunId: current.holderRunId },
						{ taskId: current.taskId, runId: current.holderRunId },
					);
				// Destroying before archiving loses the only copy of what was there.
				if (!evidence.archivePath || !evidence.archiveSha256)
					refuse(
						"workspace-refused",
						"Destroy evidence must be archived before removal",
						"destroy workspace",
						{ hasArchivePath: Boolean(evidence.archivePath), hasHash: Boolean(evidence.archiveSha256) },
						{ taskId: current.taskId, runId: current.holderRunId },
					);
			},
		);
	}

	finishWorkspaceDestroy(
		workspaceId: string,
		evidence: WorkspaceDestroyEvidence,
		result: WorkspaceDestroyResult,
		actor: string,
	): Workspace {
		let updated: Workspace | undefined;
		const event: GovernanceEventInput = {
			type: "workspace.destroyed",
			actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: { value: null, evidence, result },
		};
		this.store.append(event, (state) => {
			const current = state.workspaces[workspaceId];
			if (!current) throw new Error("Unknown workspace");
			if (current.destroyedAt) throw new Error("Workspace is already destroyed");
			// A retained Worktree keeps a live path, so it is not marked destroyed.
			updated = result.retained
				? { ...current, holderRunId: null, leaseUntil: null }
				: { ...current, holderRunId: null, leaseUntil: null, destroyedAt: new Date().toISOString() };
			event.taskId = current.taskId;
			event.payload = { value: updated, evidence, result };
		});
		if (!updated) throw new Error("Workspace destroy failed");
		return updated;
	}
}
