import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import type { GovernanceStore } from "./store.ts";
import type {
	Agent,
	Authority,
	Decision,
	Delegation,
	Deliverable,
	GovernanceEvent,
	GovernanceState,
	ProjectContract,
	Run,
	RunState,
	TaskContract,
	Verification,
	Workspace,
} from "./types.ts";

const nonempty = (value: string, name: string) => {
	if (!value.trim()) throw new Error(`${name} is required`);
};
const id = (prefix: string) => `${prefix}-${randomUUID()}`;
const active = (state: RunState) =>
	state === "CREATED" || state === "RUNNING" || state === "PAUSED" || state === "INTERRUPTED";

export function validAuthority(authority: Authority): void {
	if (!Array.isArray(authority.paths) || !Array.isArray(authority.tools)) throw new Error("Invalid authority lists");
	for (const value of [...authority.paths, ...authority.tools]) nonempty(value, "authority item");
	if (authority.paths.some((value) => value.startsWith("/") || value.split("/").includes("..")))
		throw new Error("Authority paths must stay within the repository");
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
	if (!currentTaskApproval(state, task.taskId)) throw new Error("Task revision is not approved");
	if (state.events.some((event) => event.type === "project.initialized")) {
		if (state.projectStatus !== "ACTIVE" || !state.projectApproved)
			throw new Error("Approved active project baseline required");
		projectAdmitsTask(state.projectApproved, task);
	}
	for (const dependency of task.dependencies) {
		if (!currentAcceptance(state, dependency.taskId))
			throw new Error(`Dependency ${dependency.taskId} is not accepted`);
	}
}

function projectAdmitsTask(project: ProjectContract, task: TaskContract): void {
	if (!task.scope.every((item) => project.inScope.includes(item)))
		throw new Error("Task scope exceeds project baseline");
	if (!subset(task.authority, project.authority)) throw new Error("Task authority exceeds project baseline");
	if (task.maxDepth > project.delegationPolicy.maxDepth || task.maxConcurrent > project.delegationPolicy.maxConcurrent)
		throw new Error("Task delegation limits exceed project baseline");
}

function currentTaskApproval(state: GovernanceState, taskId: string): boolean {
	const task = state.tasks[taskId];
	if (!task || state.approved[taskId] !== task.revision) return false;
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

function currentAcceptance(state: GovernanceState, taskId: string): boolean {
	const verification = state.verifications[state.accepted[taskId]];
	const task = state.tasks[taskId];
	if (!verification || !task || verification.revision !== task.revision || verification.result !== "passed")
		return false;
	const latest = Object.values(state.deliverables)
		.filter((entry) => entry.taskId === taskId)
		.at(-1);
	if (!latest || latest.deliverableId !== verification.deliverableId) return false;
	const workspaceId = state.runs[latest.runId]?.workspaceId;
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

export class GovernanceKernel {
	readonly store: GovernanceStore;
	constructor(store: GovernanceStore) {
		this.store = store;
	}
	getState(): GovernanceState {
		const state = this.store.read();
		for (const taskId of Object.keys(state.approved)) {
			if (!currentTaskApproval(state, taskId)) {
				delete state.approved[taskId];
				continue;
			}
			if (state.events.some((event) => event.type === "project.initialized")) {
				try {
					if (state.projectStatus !== "ACTIVE" || !state.projectApproved) throw new Error("Inactive project");
					projectAdmitsTask(state.projectApproved, state.tasks[taskId]);
				} catch {
					delete state.approved[taskId];
				}
			}
		}
		for (const taskId of Object.keys(state.accepted))
			if (!currentAcceptance(state, taskId)) delete state.accepted[taskId];
		return state;
	}

	streamEvents(afterSequence = 0): GovernanceEvent[] {
		return this.store.read().events.filter((event) => event.sequence > afterSequence);
	}

	submitProjectDraft(contract: ProjectContract, actor: string): void {
		nonempty(actor, "actor");
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
		if (contract.inScope.some((item) => contract.outOfScope.includes(item)))
			throw new Error("Project scope overlaps exclusions");
		validAuthority(contract.authority);
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
		const event: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
			type: "project.drafted",
			actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: { value: contract, priorRevision: contract.revision - 1 },
		};
		this.store.append(event, (state) => {
			const identity = state.events.find((event) => event.type === "project.initialized")?.payload.projectId;
			if (identity !== contract.projectId) throw new Error("Project ID differs from initialized repository");
			if (state.projectStatus === "REVOKED") throw new Error("Project is revoked");
			if (contract.revision !== (state.projectDraft?.revision ?? 0) + 1)
				throw new Error("Project changes require a new revision");
			const previous = state.projectApproved;
			event.payload.impact = {
				affectedTasks: Object.keys(state.tasks),
				budgetDeltaTokens: contract.resourceLimits.budgetTokens - (previous?.resourceLimits.budgetTokens ?? 0),
				authorityChanged: Boolean(
					previous && JSON.stringify(previous.authority) !== JSON.stringify(contract.authority),
				),
			};
		});
	}

	approveProject(revision: number, actor: string): void {
		nonempty(actor, "actor");
		const event: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
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
			const committed = Object.values(state.tasks).reduce((sum, task) => sum + task.budgetTokens, 0);
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
		const event: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
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

	submitTask(task: TaskContract, actor: string, automatic = false): void {
		nonempty(task.taskId, "taskId");
		nonempty(task.goal, "goal");
		nonempty(task.owner, "owner");
		if (!/^[A-Za-z0-9_-]+$/.test(task.taskId)) throw new Error("Invalid task ID");
		if (
			!Array.isArray(task.scope) ||
			!Array.isArray(task.acceptance) ||
			!task.scope.length ||
			!task.acceptance.length ||
			task.scope.some((item) => typeof item !== "string" || !item.trim()) ||
			task.acceptance.some((item) => typeof item !== "string" || !item.trim())
		)
			throw new Error("Task scope and acceptance are required");
		if (!Array.isArray(task.dependencies) || task.dependencies.some((item) => item.requiredState !== "accepted"))
			throw new Error("Invalid dependencies");
		if (
			!Number.isSafeInteger(task.revision) ||
			task.revision < 1 ||
			!Number.isSafeInteger(task.budgetTokens) ||
			task.budgetTokens <= 0 ||
			!Number.isSafeInteger(task.maxDepth) ||
			task.maxDepth < 0 ||
			!Number.isSafeInteger(task.maxConcurrent) ||
			task.maxConcurrent < 1
		) {
			throw new Error("Invalid task revision or limits");
		}
		validAuthority(task.authority);
		const taskEvent: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
			type: task.revision === 1 ? "task.created" : "task.revised",
			actor,
			taskId: task.taskId,
			runId: null,
			delegationId: null,
			payload: { value: task },
		};
		this.store.append(taskEvent, (state) => {
			if (automatic) {
				if (state.projectStatus !== "ACTIVE" || !state.projectApproved?.delegationPolicy.allowInternalTasks)
					throw new Error("Project does not authorize internal tasks");
				if (task.revision !== 1 || state.tasks[task.taskId])
					throw new Error("Task revisions require human approval");
				projectAdmitsTask(state.projectApproved, task);
				const allocated = Object.values(state.tasks).reduce((sum, item) => sum + item.budgetTokens, 0);
				if (allocated + task.budgetTokens > state.projectApproved.resourceLimits.budgetTokens)
					throw new Error("Project task budget exceeded");
				taskEvent.payload.autoApproved = true;
				taskEvent.payload.projectRevision = state.projectApproved.revision;
			}
			const prior = state.tasks[task.taskId];
			if ((!prior && task.revision !== 1) || (prior && task.revision !== prior.revision + 1))
				throw new Error("Invalid task revision");
			for (const dep of task.dependencies) {
				if (dep.taskId === task.taskId || !state.tasks[dep.taskId]) throw new Error("Invalid task dependency");
				const seen = new Set<string>();
				const visit = (candidate: string): void => {
					if (candidate === task.taskId) throw new Error("Task dependency cycle");
					if (seen.has(candidate)) return;
					seen.add(candidate);
					for (const next of state.tasks[candidate]?.dependencies ?? []) visit(next.taskId);
				};
				visit(dep.taskId);
			}
		});
		if (!automatic) this.requestDecision(task.taskId, "task", `Approve task revision ${task.revision}`, actor);
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
		const event: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
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
					if (
						Object.values(fresh.tasks).reduce((sum, item) => sum + item.budgetTokens, 0) >
						fresh.projectApproved.resourceLimits.budgetTokens
					)
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

	authorizeDelegation(input: Omit<Delegation, "delegationId" | "depth">, actor: string): Delegation {
		validAuthority(input.authority);
		nonempty(input.objective, "objective");
		const delegation: Delegation = { ...input, delegationId: id("G"), depth: 0 };
		this.store.append(
			{
				type: "delegation.authorized",
				actor,
				taskId: input.taskId,
				runId: input.parentRunId,
				delegationId: delegation.delegationId,
				payload: { value: delegation },
			},
			(state) => {
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
					delegation.depth = parentDelegation.depth + 1;
					ceiling = parentDelegation.authority;
					budget = parentDelegation.budgetTokens;
				}
				if (delegation.depth > task.maxDepth || !subset(input.authority, ceiling))
					throw new Error("Delegation exceeds authority or depth");
				const allocated = Object.values(state.delegations)
					.filter((d) => d.taskId === input.taskId && d.parentRunId === input.parentRunId)
					.reduce((sum, d) => sum + d.budgetTokens, 0);
				if (
					!Number.isSafeInteger(input.budgetTokens) ||
					input.budgetTokens <= 0 ||
					allocated + input.budgetTokens > budget
				)
					throw new Error("Delegation budget exceeded");
				const concurrent = Object.values(state.runs).filter(
					(run) => run.taskId === input.taskId && active(run.state),
				).length;
				if (concurrent >= task.maxConcurrent) throw new Error("Task concurrency limit reached");
			},
		);
		return delegation;
	}

	createRun(
		delegationId: string,
		harness: string,
		sessionRef: string | null,
		workspaceId: string | null,
		retryOf: string | null,
		parentSessionRef: string | null = null,
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
			workspaceId,
			retryOf,
			usageTokens: null,
			costUsd: null,
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
				if (retryOf && (fresh.runs[retryOf]?.taskId !== run.taskId || active(fresh.runs[retryOf].state)))
					throw new Error("Invalid retry Run");
				if (workspaceId && fresh.workspaces[workspaceId]?.taskId !== run.taskId)
					throw new Error("Invalid workspace");
				if (
					Object.values(fresh.runs).filter((entry) => entry.taskId === run.taskId && active(entry.state)).length >=
					task.maxConcurrent
				)
					throw new Error("Task concurrency limit reached");
			},
		);
		return run;
	}

	updateRun(
		runId: string,
		state: RunState,
		patch: Partial<Pick<Run, "nativeRunId" | "sessionRef" | "usageTokens" | "costUsd">> = {},
		proof?: string,
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
		const event: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
			type: eventType[state],
			actor: "governance",
			taskId: null,
			runId,
			delegationId: null,
			payload: { value: null as Run | null, ...(proof ? { proof } : {}) },
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
			event.taskId = old.taskId;
			event.delegationId = old.delegationId;
			event.payload.value = updated;
		});
		if (!updated) throw new Error("Run transition failed");
		return updated;
	}

	submitDeliverable(input: Omit<Deliverable, "deliverableId" | "revision">): Deliverable {
		const state = this.getState();
		const task = state.tasks[input.taskId];
		if (!task || state.runs[input.runId]?.taskId !== input.taskId) throw new Error("Invalid deliverable task or Run");
		if (state.runs[input.runId].state !== "SUCCEEDED") throw new Error("Run must succeed before delivery");
		nonempty(input.commit, "commit");
		nonempty(input.summary, "summary");
		if (
			!Array.isArray(input.tests) ||
			!input.tests.length ||
			!Array.isArray(input.issues) ||
			!Array.isArray(input.logs) ||
			input.tests.some((entry) => typeof entry !== "string" || !entry.trim())
		)
			throw new Error("Delivery requires test results, issues, and log references");
		const workspaceId = state.runs[input.runId].workspaceId;
		if (workspaceId) {
			const workspace = state.workspaces[workspaceId];
			const head = execFileSync("git", ["rev-parse", "HEAD"], { cwd: workspace.path, encoding: "utf8" }).trim();
			if (head !== input.commit) throw new Error("Deliverable commit differs from workspace HEAD");
		}
		const deliverable: Deliverable = { ...input, revision: task.revision, deliverableId: id("A") };
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

	recordVerification(deliverableId: string, verifier: string, criteria: Verification["criteria"]): Verification {
		const state = this.getState();
		const artifact = state.deliverables[deliverableId];
		if (!artifact) throw new Error("Unknown deliverable");
		if (state.runs[artifact.runId]?.executorId === verifier || !criteria.length)
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
			verifier,
			criteria,
			result: criteria.every((entry) => entry.passed) ? "passed" : "failed",
		};
		this.store.append({
			type: "verification.recorded",
			actor: verifier,
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
		const workspaceId = state.runs[latest.runId]?.workspaceId;
		if (workspaceId) {
			const head = execFileSync("git", ["rev-parse", "HEAD"], {
				cwd: state.workspaces[workspaceId].path,
				encoding: "utf8",
			}).trim();
			if (head !== verification.commit) throw new Error("Verified commit is no longer workspace HEAD");
		}
		if (state.runs[state.deliverables[verification.deliverableId].runId]?.executorId === actor)
			throw new Error("Executor cannot accept own work");
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
				if (!state.tasks[workspace.taskId] || state.workspaces[workspace.workspaceId])
					throw new Error("Invalid workspace registration");
			},
		);
	}

	leaseWorkspace(workspaceId: string, runId: string, until: string): void {
		let workspace: Workspace | undefined;
		const event: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
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
			if (old.holderRunId && old.holderRunId !== runId)
				throw new Error("Workspace held by another Run; inspect and release it first");
			workspace = { ...old, holderRunId: runId, leaseUntil: until };
			event.taskId = old.taskId;
			event.payload.value = workspace;
		});
		if (!workspace) throw new Error("Workspace lease failed");
	}

	releaseWorkspace(workspaceId: string, runId: string, actor: string, proof: string): void {
		nonempty(proof, "terminal proof");
		const event: Omit<GovernanceEvent, "eventId" | "sequence" | "time"> = {
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
}
