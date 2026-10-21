export type Authority = {
	paths: string[];
	tools: string[];
	readRepository: boolean;
	writeWorkspace: boolean;
	commitBranch: boolean;
	integrateBranch: boolean;
};

export type Agent = {
	agentId: string;
	harness: string;
	role: string;
	capabilities: string[];
};

export type TaskContract = {
	taskId: string;
	revision: number;
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
	prd: string;
	plan: string;
	changeReason: string;
};

export type Delegation = {
	delegationId: string;
	taskId: string;
	parentRunId: string | null;
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
	workspaceId: string | null;
	retryOf: string | null;
	usageTokens: number | null;
	costUsd: number | null;
};

export type Workspace = {
	workspaceId: string;
	taskId: string;
	path: string;
	branch: string;
	baseCommit: string;
	holderRunId: string | null;
	leaseUntil: string | null;
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
	runId: string;
	commit: string;
	summary: string;
	tests: string[];
	issues: string[];
	logs: string[];
};

export type Verification = {
	verificationId: string;
	deliverableId: string;
	taskId: string;
	revision: number;
	commit: string;
	verifier: string;
	criteria: { item: string; passed: boolean; evidence: string }[];
	result: "passed" | "failed";
};

export type GovernanceEvent = {
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
	events: GovernanceEvent[];
};
