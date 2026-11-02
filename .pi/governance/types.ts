export type Authority = {
	paths: string[];
	tools: string[];
	readRepository: boolean;
	writeWorkspace: boolean;
	commitBranch: boolean;
	integrateBranch: boolean;
};

import type { IdentityAssurance, IdentitySource } from "./identity.ts";

export type Agent = {
	agentId: string;
	harness: string;
	role: string;
	capabilities: string[];
};

export type ApprovalEffect = "auto" | "ask" | "deny";
export type ApprovalRule = {
	id: string;
	effect: ApprovalEffect;
	risk: "low" | "medium" | "high";
	match: {
		taskKind?: "internal" | "ordinary" | "revision";
		pathsAny?: string[];
		toolsAny?: string[];
		toolsAll?: string[];
		writeWorkspace?: boolean;
		commitBranch?: boolean;
		integrateBranch?: boolean;
		maxDepthMin?: number;
		/**
		 * Matches when the Task budget is **at least** this. A lower bound, as named.
		 *
		 * Read that twice before writing a rule: a `deny` rule using it means "refuse
		 * anything this large or larger", which reads like an upper bound at the call
		 * site. The organisation policy does exactly that - `no-unbounded-budget` sets
		 * `minBudgetTokens: 2000000` with effect `deny`, so 2,000,000 is the ceiling.
		 * The threshold is not echoed in the refusal text, so an operator hitting it has
		 * to be told the number separately.
		 */
		minBudgetTokens?: number;
		/** Matches when the Task budget is **at most** this. */
		maxBudgetTokens?: number;
	};
};
export type ApprovalPolicy = { version: 1; defaultEffect: "ask" | "deny"; rules: ApprovalRule[] };
/**
 * RED-5: why a hard refusal happened.
 *
 * A refusal that leaves no trace is indistinguishable from a refusal that never
 * happened, so every red-line stop writes one of these to the ledger before it
 * throws. `code` is stable for querying; `message` is the thrown text verbatim.
 */
export type RedlineRefusal = {
	/** Which guard refused: project baseline, task gate, delegation ceiling, ... */
	code:
		| "invalid-authority"
		| "task-not-approved"
		| "project-not-active"
		| "task-outside-baseline"
		| "authority-escalation"
		| "scope-escalation"
		| "delegation-limit"
		| "dependency-unmet"
		| "deliverable-unverified"
		| "workspace-refused"
		| "org-policy";
	/** The guard's own words, unchanged, so the ledger and the error agree. */
	message: string;
	/** What was being attempted. */
	operation: string;
	/** Where the refused identity sits in the delegation chain, when known. */
	taskId: string | null;
	runId: string | null;
	delegationId: string | null;
	/** The refused quantity itself, so a reader can judge the size of the attempt. */
	detail: Record<string, unknown>;
};

/**
 * Why an approval ended where it did.
 *
 * A rule engine that answers only "auto" or "ask" is a black box: the operator
 * cannot tell a Task that was refused because of a tool from one that was refused
 * because a path sat outside the baseline. Every field here answers a question
 * somebody actually has to answer, and the ledger keeps the whole object.
 */
export type ApprovalDiagnosis = {
	/** Whether the Task fits inside the approved project baseline. */
	baselineSubset: boolean;
	/** What the Task asked for that the baseline does not allow. */
	exceeded: {
		paths: string[];
		tools: string[];
		flags: string[];
		budgetTokens: number | null;
		maxDepth: number | null;
		maxConcurrent: number | null;
	};
	/** Every rule that was tried, and why it did or did not match. */
	rules: {
		id: string;
		effect: ApprovalEffect;
		matched: boolean;
		/** The conditions that did not hold, named so the operator can fix them. */
		failedOn: string[];
		/**
		 * The numeric thresholds this rule compares against, named in plain terms.
		 * A `failedOn` entry says which condition failed but not against what, which
		 * leaves the operator guessing the number. Budget is the case that matters:
		 * `minBudgetTokens` is a lower bound, so on a `deny` rule it is the ceiling,
		 * and the refusal has to state the ceiling to be actionable.
		 */
		limits: string[];
	}[];
	/** True when the Task cannot be approved until the baseline itself is revised. */
	requiresBaselineRevision: boolean;
	/** One sentence describing the outcome. */
	summary: string;
};

export type ApprovalEvaluation = {
	effect: ApprovalEffect;
	ruleId: string;
	risk: "low" | "medium" | "high" | "unknown";
	policyDigest: string | null;
	projectRevision: number | null;
	inputs: {
		taskKind: "internal" | "ordinary" | "revision";
		paths: string[];
		tools: string[];
		writeWorkspace: boolean;
		commitBranch: boolean;
		integrateBranch: boolean;
		maxDepth: number;
		budgetTokens: number;
	};
	/**
	 * Present when the evaluation had a project baseline to compare against.
	 * Older ledger entries do not carry it, and read as "no diagnosis recorded".
	 */
	diagnosis?: ApprovalDiagnosis;
};

export type TaskContract = {
	taskId: string;
	revision: number;
	/** Omitted on earlier contracts; those tasks are executable roots. */
	kind?: "container" | "executable";
	parentTaskId?: string | null;
	/** Human-readable reason for splitting this task from its parent. */
	splitReason?: string;
	goal: string;
	scope: string[];
	acceptance: string[];
	owner: string;
	budgetTokens: number;
	maxDepth: number;
	maxConcurrent: number;
	authority: Authority;
	dependencies: { taskId: string; requiredState: "accepted" }[];
};

export type ProjectContract = {
	projectId: string;
	revision: number;
	name: string;
	goal: string;
	inScope: string[];
	outOfScope: string[];
	successCriteria: string[];
	authority: Authority;
	delegationPolicy: { allowInternalTasks: boolean; maxDepth: number; maxConcurrent: number };
	resourceLimits: { budgetTokens: number };
	humanApprovalTriggers: string[];
	/** Required for new drafts; optional only while reading existing ledger contracts. */
	approvalPolicy?: ApprovalPolicy;
	prd: string;
	plan: string;
	changeReason: string;
};

export type Delegation = {
	delegationId: string;
	taskId: string;
	parentDelegationId: string | null;
	parentRunId: string | null;
	requesterId: string;
	requesterSessionId?: string;
	requesterSessionFile?: string;
	executorId: string;
	objective: string;
	authority: Authority;
	budgetTokens: number;
	depth: number;
};

export type RunState = "CREATED" | "RUNNING" | "PAUSED" | "INTERRUPTED" | "SUCCEEDED" | "FAILED" | "CANCELLED";

export type Run = {
	runId: string;
	taskId: string;
	delegationId: string;
	executorId: string;
	harness: string;
	state: RunState;
	sessionRef: string | null;
	parentSessionRef: string | null;
	nativeRunId: string | null;
	nativeAsyncDir?: string | null;
	workspaceId: string | null;
	retryOf: string | null;
	usageTokens: number | null;
	costUsd: number | null;
	routing?: {
		model: string;
		agent?: string;
		modelProfile?: string | null;
		tier?: string;
		contextTokens?: number | null;
		policyDigest: string;
		maxConcurrent: number;
		tierMaxConcurrent?: number;
		roleMaxConcurrent?: number;
		maxRunsPerTask?: number | null;
		maxAllocationTokens?: number | null;
		timeoutMs?: number | null;
		expectedTools?: string[];
		approvalDigest?: string;
		pluginVersion?: string;
	};
};

export type Workspace = {
	workspaceId: string;
	taskId: string;
	path: string;
	branch: string;
	baseCommit: string;
	holderRunId: string | null;
	leaseUntil: string | null;
	/** Set once the Worktree and branch are gone, or the removal attempt was recorded. */
	destroyedAt?: string | null;
};

/**
 * What was verified before the Worktree was removed. Recorded on the destroy
 * event so the surviving facts outlive the directory.
 */
export type WorkspaceDestroyEvidence = {
	taskId: string;
	path: string;
	branch: string;
	baseCommit: string;
	/** Commit the branch pointed at when captured; null when the branch was already gone. */
	head: string | null;
	/** Commits on the branch that are not reachable from the base commit. */
	unmergedCommits: string[];
	/** Paths with uncommitted or untracked changes; must be empty to destroy. */
	dirtyPaths: string[];
	/** Where the archived evidence lives, relative to the workspace root. */
	archivePath: string | null;
	archiveSha256: string | null;
	taskAccepted: boolean;
};

export type WorkspaceDestroyResult = {
	worktreeRemoved: boolean;
	branchRemoved: boolean;
	pruned: boolean;
	retained: boolean;
	reason: string | null;
};

export type Decision = {
	decisionId: string;
	taskId: string;
	revision: number;
	kind: "task" | "scope" | "budget" | "operation" | "acceptance";
	request: string;
	requester: string;
	result: "pending" | "approved" | "rejected";
	actor: string | null;
	scope: string | null;
	expiresAt: string | null;
	evidence: string[];
};

export type Deliverable = {
	deliverableId: string;
	taskId: string;
	revision: number;
	/** Null only for work delivered directly from an observed main Pi session. */
	runId: string | null;
	/** Present for direct main-session delivery; historical Run deliveries omit it. */
	sessionId?: string;
	commit: string;
	summary: string;
	/**
	 * ROLE-8: test results as a claim plus the artifact that backs it.
	 *
	 * A free-text list cannot distinguish "237 tests passed" read from a runner
	 * from "237 tests passed" typed by hand. Each entry names the log file Git
	 * kept, and the kernel records whether that file was actually there.
	 */
	tests: TestReport[];
	issues: string[];
	logs: string[];
	/**
	 * Facts checked against Git when the deliverable was submitted, not values the
	 * submitter supplied. Absent on records written before verification existed.
	 */
	evidence?: DeliverableEvidence;
};

/**
 * ROLE-7 / ROLE-9: what the ledger can prove about a delivery on its own.
 *
 * The submitter names a commit; everything here is computed from the repository
 * so a delivery cannot claim changes the Git history does not contain.
 */
export type DeliverableEvidence = {
	/** Resolves to a commit object via `git cat-file -t`. */
	commitType: string;
	commitSubject: string | null;
	/** Commit the diff was measured against: the Worktree base, not the branch tip. */
	baseCommit: string;
	/** Files changed between base and deliverable commit (ROLE-9). */
	files: DeliverableFileChange[];
	/** Additions and deletions across those files. */
	additions: number;
	deletions: number;
};

/**
 * ROLE-8: what a submitter claims about the tests, and what can be checked.
 *
 * `passed`/`failed` stay claims. The checkable part is `logPath`: the file is
 * resolved inside the delivery commit, so a report cannot point at a log that
 * was never committed, and its SHA-256 is recorded so the exact bytes reviewed
 * are the ones audited.
 */
export type TestReport = {
	/** Command that produced the result, e.g. `npm test`. */
	command: string;
	passed: number;
	failed: number;
	/** Repository-relative path to the captured output, inside the delivery commit. */
	logPath: string;
	/** Recorded by the kernel after resolving the path. Never supplied by the submitter. */
	verified?: TestLogEvidence | null;
};

export type TestLogEvidence = {
	/** Path as resolved in the delivery commit. */
	path: string;
	/** Bytes of the log within the delivery commit. */
	bytes: number;
	sha256: string;
	/**
	 * Counts re-read out of the log. When they disagree with the claim, the
	 * disagreement is the finding, so both are kept.
	 */
	observed: { passed: number | null; failed: number | null } | null;
};

export type DeliverableFileChange = {
	path: string;
	/** Git porcelain status letter for the change. */
	status: "A" | "M" | "D" | "R" | "T";
	additions: number;
	deletions: number;
};

export type TaskCancellation = {
	taskId: string;
	revision: number;
	actor: string;
	at: string;
	reason: string;
	/** Runs still active when the Task was cancelled, and what happened to each. */
	cancelledRunIds: string[];
	/** Budget the Task was reserving at that moment, now released. */
	releasedTokens: number;
};

export type Verification = {
	verificationId: string;
	deliverableId: string;
	taskId: string;
	revision: number;
	commit: string;
	/** Ledger-shaped identity of whoever verified, e.g. `agent-run:R-...`. */
	verifier: string;
	criteria: { item: string; passed: boolean; evidence: string }[];
	result: "passed" | "failed";
	/**
	 * The two Runs this verification relates, recorded so independence is checkable after
	 * the fact rather than only at write time.
	 *
	 * Optional because verifications written before the identity model have neither, and
	 * the ledger cannot be rewritten to add them. A reader must treat absence as unknown.
	 */
	producerRunId?: string | null;
	verifierRunId?: string | null;
	/** Where `verifier` came from, and how far it can be trusted. See `identity.ts`. */
	identitySource?: IdentitySource;
	identityAssurance?: IdentityAssurance;
	/**
	 * Set when the acceptance criteria were not checked by an independent Run.
	 *
	 * The ruling requires that a human override never pass itself off as a reviewer
	 * verification; this field is how a reader tells the two apart without consulting the
	 * event log.
	 */
	verificationKind?: "independent-run" | "manual-unverified";
};

export type EventActor = {
	kind: "human" | "agent" | "system" | "plugin" | "unknown";
	id: string;
	authenticatedBy: "os-user" | "pi-session" | "governance" | "plugin" | "unverified";
	agentDefinitionId: string | null;
	agentInstanceId: string | null;
	sessionId: string | null;
	runId: string | null;
};

export type EventSubject = {
	type: string;
	id: string;
};

export type EventContext = {
	taskId: string | null;
	runId: string | null;
	delegationId: string | null;
	sessionId: string | null;
};

export type EventIntegrity = {
	algorithm: "sha256";
	prevHash: string | null;
	eventHash: string;
};

export type GovernanceEvent = {
	ledgerVersion: 2;
	eventId: string;
	sequence: number;
	eventType: string;
	eventVersion: number;
	projectId: string | null;
	occurredAt: string;
	recordedAt: string;
	actor: EventActor;
	subject: EventSubject;
	context: EventContext;
	correlationId: string;
	causationEventId: string | null;
	commandId: string | null;
	payload: Record<string, unknown>;
	extensions: Record<string, unknown>;
	integrity: EventIntegrity;
	/** @deprecated Compatibility alias for V1 domain code. Not serialized to the V2 ledger. */
	readonly type: string;
	/** @deprecated Compatibility alias for V1 domain code. Not serialized to the V2 ledger. */
	readonly time: string;
	/** @deprecated Use context.taskId. Not serialized to the V2 ledger. */
	readonly taskId: string | null;
	/** @deprecated Use context.runId. Not serialized to the V2 ledger. */
	readonly runId: string | null;
	/** @deprecated Use context.delegationId. Not serialized to the V2 ledger. */
	readonly delegationId: string | null;
};

export type GovernanceEventInput = {
	type: string;
	eventNamespace?: string;
	eventVersion?: number;
	projectId?: string | null;
	occurredAt?: string;
	actor: string | EventActor;
	taskId: string | null;
	runId: string | null;
	delegationId: string | null;
	sessionId?: string | null;
	subject?: EventSubject;
	correlationId?: string;
	causationEventId?: string | null;
	commandId?: string | null;
	payload: Record<string, unknown>;
	extensions?: Record<string, unknown>;
};

/**
 * Counts recorded when work history is archived. The numbers come from the
 * projection at archive time, so a later reader can tell how much was moved
 * without re-deriving it from events.
 */
export type ArchivedRecordCounts = {
	tasks: number;
	delegations: number;
	runs: number;
	workspaces: number;
	decisions: number;
	deliverables: number;
	verifications: number;
	accepted: number;
	cancelled: number;
};

/**
 * One archive operation. `boundary` is the ledger sequence the archive covers:
 * events up to and including it belong to the archive, later ones are current.
 *
 * Records are moved here rather than deleted. Every consumer of the projection
 * reads `state.tasks`, `state.runs` and so on, so moving them makes "current"
 * default-correct without teaching each call site about archiving, while the
 * ledger keeps the full history untouched.
 */
export type ProjectArchive = {
	archiveId: string;
	archivedAt: string;
	actor: string;
	reason: string;
	boundary: number;
	counts: ArchivedRecordCounts;
	/** Present for a full workspace archive; older work-only archives have no snapshot. */
	snapshot?: { path: string; ledgerSha256: string; manifestSha256: string };
	records: {
		tasks: Record<string, TaskContract>;
		approved: Record<string, number>;
		delegations: Record<string, Delegation>;
		runs: Record<string, Run>;
		workspaces: Record<string, Workspace>;
		decisions: Record<string, Decision>;
		deliverables: Record<string, Deliverable>;
		verifications: Record<string, Verification>;
		accepted: Record<string, string>;
		cancelled: Record<string, TaskCancellation>;
	};
};

export type GovernanceState = {
	projectDraft: ProjectContract | null;
	projectApproved: ProjectContract | null;
	projectRejectedRevision: number | null;
	projectStatus: "DRAFT" | "ACTIVE" | "PAUSED" | "REVOKED";
	agents: Record<string, Agent>;
	tasks: Record<string, TaskContract>;
	approved: Record<string, number>;
	delegations: Record<string, Delegation>;
	runs: Record<string, Run>;
	workspaces: Record<string, Workspace>;
	decisions: Record<string, Decision>;
	deliverables: Record<string, Deliverable>;
	verifications: Record<string, Verification>;
	accepted: Record<string, string>;
	/**
	 * Tasks that were cancelled, and why.
	 *
	 * Cancellation is a fact recorded about the Task, not a state written over it:
	 * the contract stays readable and the Run history stays intact, while the budget
	 * the Task was reserving is released because it can no longer run.
	 */
	cancelled: Record<string, TaskCancellation>;
	/** Archives by id, oldest first in `archiveOrder`. Current collections exclude them. */
	archives: Record<string, ProjectArchive>;
	archiveOrder: string[];
	/** Sequence of the last `project.history.archived`; 0 when never archived. */
	archiveBoundary: number;
	/** Last full workspace archive; generated Project and Task files before it are historical. */
	workspaceArchiveBoundary: number;
	/** Sequence of the last `project.reset`; 0 when never reset. */
	resetBoundary: number;
	/**
	 * Highest project revision ever drafted or approved. Kept apart from
	 * `projectDraft` because a reset clears the draft: the next revision must not
	 * fall back to r1 and collide with a revision a human already decided on.
	 */
	projectRevisionFloor: number;
	events: GovernanceEvent[];
};
