// Remote governance sidecar.
//
// Pushes a live projection of one project's governance ledger to the public
// relay site (note.litearch.cn) and executes approval commands sent back from
// the browser. The ledger stays authoritative and local: this module never
// writes governance state except through GovernanceKernel on the machine that
// owns the ledger.
//
// Transport: POST for state (client -> site), SSE for commands (site -> client)
// and for browser refresh. No polling.
import * as fs from "node:fs";
import * as http from "node:http";
import * as https from "node:https";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import {
	type ActivityPage,
	type MainAgentStatus,
	queryActivityTimeline,
	queryMainAgentStatuses,
} from "./activity-timeline.ts";
import { type AgentTree, queryAgentTree } from "./agent-tree.ts";
import { type ArchiveAuditRecord, queryArchives } from "./audit-query.ts";
import { GovernanceKernel, reservedBudget, subset } from "./kernel.ts";
import { observeRun } from "./native-observability.ts";
import { reconcileNativeRun } from "./run-reconciliation.ts";
import { dataRoot, GovernanceStore } from "./store.ts";
import {
	approveSubagentPolicy,
	saveSubagentPolicy,
	subagentPolicyStatus,
	validateSubagentPolicy,
} from "./subagent-policy.ts";
import { readNativeRunStatus } from "./subagent-supervision.ts";
import { queryTaskTree, type TaskTreeNode } from "./task-tree.ts";
import { queryTaskWorkStatuses, type TaskWorkStatus } from "./task-work-status.ts";
import type { GovernanceState, ProjectContract, Verification } from "./types.ts";
import { renderViews } from "./views.ts";

export const REMOTE_ACTOR = "web:kipley";
export const DEFAULT_API_URL = "https://note.litearch.cn";
export const PUSH_DEBOUNCE_MS = 100;
export const PUSH_MIN_INTERVAL_MS = 500;
export const NATIVE_OBSERVATION_INTERVAL_MS = 15_000;

const DECISION_KIND_LABEL: Record<string, string> = {
	task: "任务创建",
	scope: "范围变更",
	budget: "预算变更",
	operation: "操作授权",
	acceptance: "验收",
};

export type RemoteTaskSummary = {
	taskId: string;
	revision: number;
	goal: string;
	budgetTokens: number;
	state: "draft" | "approved" | "accepted" | "cancelled";
	kind: "container" | "executable";
	parentTaskId: string | null;
	splitReason: string | null;
	owner: string;
	scope: string[];
	acceptance: string[];
	dependencies: string[];
	work: TaskWorkStatus;
	deliverables: {
		deliverableId: string;
		commit: string;
		runId: string | null;
		sessionId: string | null;
		verification: string | null;
	}[];
};

export type RemoteDecisionSummary = {
	decisionId: string;
	taskId: string;
	revision: number;
	kind: string;
	request: string;
	result: "pending" | "approved" | "rejected";
	ruleId: string | null;
	risk: string | null;
	reasons: string[];
	/** Which delegation level this approval belongs to. */
	layer: RemoteAuditLayer;
};

export type RemoteToolObservation = {
	name: string;
	projectPath: string | null;
	at: number | null;
	result: "success" | "error" | null;
};

export type RemoteRunSummary = {
	runId: string;
	taskId: string;
	delegationId: string;
	executorId: string;
	state: string;
	model: string | null;
	usageTokens: number | null;
	retryOf: string | null;
	nativeLinked: boolean;
	costUsd: number | null;
	observation: {
		source: "pi-subagents-native";
		observedAt: number;
		available: boolean;
		nativeState: string | null;
		nativeOutcome: "SUCCEEDED" | "FAILED" | null;
		activityState: string | null;
		actualModel: string | null;
		turns: number | null;
		toolCount: number | null;
		outputTokens: number | null;
		windowTokens: number | null;
		lastOutputAt: number | null;
		lastTool: RemoteToolObservation | null;
		recentTools: RemoteToolObservation[];
		gap: string | null;
	} | null;
};

/**
 * Admission gates live outside the approval policy: they decide whether a task
 * can even be submitted, before any rule matching. The panel shows them
 * explicitly because "AI cannot create a task at all" looks identical to
 * "approval is pending" when only the decision list is visible.
 */
/** One human decision point. The layer says *which* delegation level asks. */
export type RemoteAuditLayer = "project" | "task" | "delegation";

export type RemoteCheck = {
	label: string;
	ok: boolean;
	detail: string;
};

export type RemoteAuditItem = {
	id: string;
	layer: RemoteAuditLayer;
	title: string;
	subtitle: string;
	checks: RemoteCheck[];
	status: "ok" | "attention" | "blocked";
	actions: RemoteAction[];
	children: RemoteAuditItem[];
};

/** One raw ledger line, with the fields the operator needs to audit it. */
export type RemoteEventRow = {
	sequence: number;
	eventType: string;
	actorId: string;
	actorKind: string;
	subject: string;
	taskId: string | null;
	runId: string | null;
	delegationId: string | null;
	recordedAt: string;
	layer: RemoteAuditLayer | "other";
	payload: string;
	eventHash: string;
	prevHash: string;
};

export type RemoteGates = {
	allowInternalTasks: boolean | null;
	maxDepth: number | null;
	maxConcurrent: number | null;
	approvalDefault: string | null;
	approvalRules: string[];
	authorityPaths: string[];
	authorityTools: string[];
	writeWorkspace: boolean | null;
	commitBranch: boolean | null;
	integrateBranch: boolean | null;
	budgetTokens: number | null;
	allocatedTokens: number;
	activeRuns: number;
};

export type RemoteAction = {
	action: string;
	label: string;
	args: Record<string, unknown>;
	needsReason?: boolean;
};

export type RemoteSnapshot = {
	projectId: string;
	name: string;
	cwd: string;
	sequence: number;
	projectStatus: string;
	/** Terminal: REVOKED means the project is closed and should disappear. */
	closed: boolean;
	baselineRevision: number | null;
	draftRevision: number | null;
	tasks: RemoteTaskSummary[];
	pendingDecisions: RemoteDecisionSummary[];
	runs: RemoteRunSummary[];
	gates: RemoteGates;
	audit: RemoteAuditItem[];
	/** Read-only Agent lineage projected from this project's JSONL ledger. */
	agentTree: AgentTree;
	mainAgents: MainAgentStatus[];
	taskTree: TaskTreeNode[];
	activity: ActivityPage;
	/** Level 4: the raw ledger rows, newest last. */
	events: RemoteEventRow[];
	actions: RemoteAction[];
	nowMarkdown: string;
	inboxMarkdown: string;
	tasksMarkdown: string;
	projectMarkdown: string;
	/** Archived work, newest last. Read-only; nothing here can be resumed. */
	archives: ArchiveAuditRecord[];
	archiveMarkdown: string;
	/** Ledger boundaries that separate current records from history. */
	resetBoundary: number;
	archiveBoundary: number;
	projectRevisionFloor: number;
	contract: ProjectContract | null;
	subagentConfig: ReturnType<typeof subagentPolicyStatus> | null;
	updatedAt: string;
};

export type RemoteCommand = {
	id?: string;
	action: string;
	args?: Record<string, unknown>;
	expectedSequence?: number;
};

export type RemoteCommandResult = {
	state: "accepted" | "rejected" | "stale";
	message: string;
};

/**
 * Translate the matched policy inputs into short human reasons. The panel shows
 * them next to the approve button so a decision is never a blind yes.
 */
export function reasonsFor(inputs: Record<string, unknown> | undefined): string[] {
	if (!inputs) return [];
	const reasons: string[] = [];
	const list = (value: unknown): string[] => (Array.isArray(value) ? value.map(String) : []);
	if (inputs.writeWorkspace === true) reasons.push("需要写代码");
	if (inputs.commitBranch === true) reasons.push("需要提交到分支");
	if (inputs.integrateBranch === true) reasons.push("需要合并分支");
	if (typeof inputs.maxDepth === "number" && inputs.maxDepth > 0) reasons.push(`可开 ${inputs.maxDepth} 层子 Agent`);
	const paths = list(inputs.paths);
	if (paths.length) reasons.push(`路径 ${paths.join(", ")}`);
	const tools = list(inputs.tools);
	if (tools.length) reasons.push(`工具 ${tools.join(", ")}`);
	if (typeof inputs.budgetTokens === "number") reasons.push(`预算 ${inputs.budgetTokens}`);
	return reasons;
}

function check(label: string, ok: boolean, detail: string): RemoteCheck {
	return { label, ok, detail };
}

function statusOf(checks: RemoteCheck[]): RemoteAuditItem["status"] {
	if (checks.some((entry) => !entry.ok)) return "blocked";
	return "ok";
}

/**
 * Render the audit tree the operator actually reviews. There are three levels
 * (project → task → delegation), and every human approval is attached to the
 * level it belongs to: a project draft is a level-1 decision, a task revision a
 * level-2 decision, a delegation that was refused for scope a level-3 decision.
 * The old flat action list is derived from this so the two can never disagree.
 */
export function buildAudit(project: string, kernel: GovernanceKernel): RemoteAuditItem[] {
	const state = kernel.getState();
	// The confirmation token for a reset or an archive is the project identity, so
	// this layer needs the same id the ledger recorded at initialization.
	const projectId =
		typeof state.events.find((event) => event.type === "project.initialized")?.payload.projectId === "string"
			? (state.events.find((event) => event.type === "project.initialized")?.payload.projectId as string)
			: path.basename(project);
	const baseline = state.projectApproved;
	const draft = state.projectDraft;
	const pendingDraft =
		draft && draft.revision !== baseline?.revision && state.projectRejectedRevision !== draft.revision ? draft : null;
	const decisions = Object.values(state.decisions);

	const layerOfDecision = (_taskId: string, kind: string): RemoteAuditLayer => {
		if (kind === "scope" || kind === "operation") return "delegation";
		return "task";
	};

	const taskDecisions = (taskId: string) =>
		decisions
			.filter((entry) => entry.taskId === taskId && entry.result === "pending")
			.map(
				(entry): RemoteDecisionSummary => ({
					decisionId: entry.decisionId,
					taskId: entry.taskId,
					revision: entry.revision,
					kind: entry.kind,
					request: entry.request,
					result: entry.result,
					ruleId: null,
					risk: null,
					reasons: [],
					layer: layerOfDecision(entry.taskId, entry.kind),
				}),
			);

	// ---- level 1: project baseline ----
	const projectChecks: RemoteCheck[] = [];
	if (!baseline) projectChecks.push(check("已批准基线", false, "尚无批准的项目基线，不能创建任务或委派"));
	else projectChecks.push(check("已批准基线", true, `r${baseline.revision} · ${state.projectStatus}`));
	if (state.projectStatus !== "ACTIVE" && state.projectStatus !== "DRAFT")
		projectChecks.push(check("项目状态", false, `当前 ${state.projectStatus}，新准入已停止`));
	const activeRuns = Object.values(state.runs).filter((run) =>
		["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"].includes(run.state),
	);
	if (pendingDraft && activeRuns.length)
		projectChecks.push(check("改基线前置条件", false, `存在 ${activeRuns.length} 个活跃 Run，改基线前必须先对账`));
	// The kernel's reservation rule, not the sum of every Task ever created:
	// cancelled and unapproved Tasks would otherwise hold budget the project
	// will refuse to run, and the panel would disagree with `gov state show`.
	const allocated = reservedBudget(state);
	if (baseline)
		projectChecks.push(
			check(
				"预算",
				allocated <= baseline.resourceLimits.budgetTokens,
				`已分配 ${allocated} / 上限 ${baseline.resourceLimits.budgetTokens}`,
			),
		);
	if (pendingDraft)
		projectChecks.push(
			check("待审核草稿", false, `r${pendingDraft.revision} 未授权（${pendingDraft.changeReason}）`),
		);

	// A standing red-line count belongs at the top: an operator scanning the tree
	// should not have to open each task to learn that attempts were stopped.
	const redlineEvents = state.events.filter(
		(event) => event.type === "redline.triggered" && event.sequence > state.archiveBoundary,
	);
	if (redlineEvents.length) {
		const codes = [...new Set(redlineEvents.map((event) => String(event.payload.code ?? "unknown")))];
		projectChecks.push(
			check("红线拒绝", false, `${redlineEvents.length} 次被拒 · ${codes.join(", ")}（明细见对应任务）`),
		);
	}

	const projectActions: RemoteAction[] = [];
	if (pendingDraft) {
		projectActions.push({
			action: "project.approve",
			label: `批准契约 r${pendingDraft.revision}`,
			args: { revision: pendingDraft.revision },
		});
		projectActions.push({
			action: "project.reject",
			label: `拒绝草稿 r${pendingDraft.revision}`,
			args: { revision: pendingDraft.revision },
			needsReason: true,
		});
	}
	if (state.projectStatus === "ACTIVE") projectActions.push({ action: "project.pause", label: "暂停项目", args: {} });
	if (state.projectStatus === "PAUSED") projectActions.push({ action: "project.resume", label: "恢复项目", args: {} });
	// Closing a project is terminal: the panel stops listing it once the ledger
	// says REVOKED. Offered only when no Run is still alive, because a half-run
	// project must be reconciled first (the kernel enforces this too).
	if (state.projectStatus === "ACTIVE" || state.projectStatus === "PAUSED")
		projectActions.push({
			action: "project.revoke",
			label: activeRuns.length ? "收尾项目（先对账活跃 Run）" : "收尾项目（撤销基线）",
			args: {},
			needsReason: activeRuns.length > 0,
		});

	// Two independent settings. Reset revokes authorization; Start Fresh moves
	// work into the archive. Neither implies the other, so they are separate
	// actions with separate confirmations, and the panel never chains them.
	const hasRecords =
		Object.keys(state.tasks).length > 0 ||
		Object.keys(state.runs).length > 0 ||
		Object.keys(state.deliverables).length > 0;
	if (state.projectStatus !== "REVOKED") {
		const nothingToReset = state.projectStatus === "DRAFT" && !state.projectApproved && !state.projectDraft;
		projectActions.push({
			action: "project.reset",
			label: activeRuns.length
				? "重置治理（先对账活跃 Run）"
				: nothingToReset
					? "重置治理（已无基线）"
					: "重置治理（撤销基线，保留历史）",
			// The project id is the second confirmation: it is what the kernel
			// checks, so the panel cannot offer a one-click reset.
			args: { confirm: typeof projectId === "string" ? projectId : "" },
			needsReason: true,
		});
		projectActions.push({
			action: "project.archive",
			label: activeRuns.length
				? "开始新的工作区（先对账活跃 Run）"
				: hasRecords
					? "开始新的工作区（归档当前工作）"
					: "开始新的工作区（当前为空）",
			args: { confirm: typeof projectId === "string" ? projectId : "" },
			needsReason: true,
		});
	}

	const projectItem: RemoteAuditItem = {
		id: "layer:project",
		layer: "project",
		title: `第 1 层 · 项目基线${baseline ? ` r${baseline.revision}` : ""}`,
		subtitle: pendingDraft
			? `待审核草稿 r${pendingDraft.revision}`
			: baseline
				? `已授权 · ${state.projectStatus}`
				: "尚无基线",
		checks: projectChecks,
		status: statusOf(projectChecks),
		actions: projectActions,
		children: [],
	};

	// ---- level 2: tasks (and level 3: delegations nested inside) ----
	const delegationsByTask = new Map<string, (typeof state.delegations)[string][]>();
	for (const delegation of Object.values(state.delegations)) {
		const list = delegationsByTask.get(delegation.taskId) ?? [];
		list.push(delegation);
		delegationsByTask.set(delegation.taskId, list);
	}

	const taskItems: RemoteAuditItem[] = Object.values(state.tasks).map((task) => {
		const checks: RemoteCheck[] = [];
		const approved = state.approved[task.taskId] === task.revision;
		const accepted = Boolean(state.accepted[task.taskId]);
		checks.push(
			approved
				? check("任务已批准", true, `revision ${task.revision}`)
				: check("任务已批准", false, `revision ${task.revision} 待批准`),
		);
		if (baseline) {
			const outOfScope = task.scope.filter((item) => !baseline.inScope.includes(item));
			checks.push(
				check(
					"范围属于 inScope",
					outOfScope.length === 0,
					outOfScope.length ? `越界：${outOfScope.join(", ")}` : task.scope.join(", "),
				),
			);
			const authorityOk = subset(task.authority, baseline.authority);
			checks.push(check("authority 是基线子集", authorityOk, authorityOk ? "通过" : "超出项目 authority 上限"));
			const withinBudget = allocated <= baseline.resourceLimits.budgetTokens;
			checks.push(check("预算在项目上限内", withinBudget, `${task.budgetTokens} tokens`));
		}
		checks.push(
			check(
				"验收标准可核对",
				task.acceptance.length > 0,
				`${task.acceptance.length} 项${accepted ? " · 已验收" : ""}`,
			),
		);
		const pendingDeps = task.dependencies.filter((dep) => !state.accepted[dep.taskId]);
		checks.push(
			check(
				"依赖已验收",
				pendingDeps.length === 0,
				pendingDeps.length ? `未验收：${pendingDeps.map((dep) => dep.taskId).join(", ")}` : "无阻塞依赖",
			),
		);

		const pending = taskDecisions(task.taskId).filter((entry) => entry.layer === "task");
		const actions: RemoteAction[] = pending.flatMap((entry) => [
			{
				action: "decision.approve",
				label: `批准 ${task.taskId} · ${DECISION_KIND_LABEL[entry.kind] ?? entry.kind}`,
				args: { decisionId: entry.decisionId },
			},
			{
				action: "decision.reject",
				label: `拒绝 ${task.taskId} · ${DECISION_KIND_LABEL[entry.kind] ?? entry.kind}`,
				args: { decisionId: entry.decisionId },
				needsReason: true,
			},
		]);
		const approvedDecision = decisions.find(
			(entry) =>
				entry.taskId === task.taskId &&
				entry.kind === "task" &&
				entry.revision === task.revision &&
				entry.result === "approved",
		);
		if (!approved && !accepted && approvedDecision)
			actions.push({
				action: "task.approve",
				label: `绑定批准 ${task.taskId}（决策已通过）`,
				args: { taskId: task.taskId, decisionId: approvedDecision.decisionId },
			});

		// ---- level 3: delegations under this task ----
		const delegationItems: RemoteAuditItem[] = (delegationsByTask.get(task.taskId) ?? []).map((delegation) => {
			const dChecks: RemoteCheck[] = [];
			if (task.authority) {
				const authorityOk = subset(delegation.authority, task.authority);
				dChecks.push(check("权限是任务子集", authorityOk, authorityOk ? "通过" : "超出任务 authority"));
			}
			dChecks.push(
				check(
					"预算",
					delegation.budgetTokens > 0 && (!baseline || delegation.budgetTokens <= task.budgetTokens),
					`${delegation.budgetTokens} / 任务 ${task.budgetTokens}`,
				),
			);
			dChecks.push(
				check(
					"深度",
					!baseline || delegation.depth <= baseline.delegationPolicy.maxDepth,
					`${delegation.depth} / 上限 ${baseline?.delegationPolicy.maxDepth ?? "-"}`,
				),
			);
			const runs = Object.values(state.runs).filter((run) => run.delegationId === delegation.delegationId);
			const running = runs.filter((run) => ["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"].includes(run.state));
			dChecks.push(
				check(
					"Run",
					running.length === 0 ? runs.length > 0 : true,
					runs.length ? runs.map((run) => `${run.runId.slice(0, 8)}=${run.state}`).join(", ") : "尚未启动",
				),
			);
			if (delegation.parentDelegationId)
				dChecks.push(check("子委派", true, `上级 ${delegation.parentDelegationId.slice(0, 12)}`));
			const scopeDecisions = pendingDecisionsFor(state, delegation.taskId, "scope");
			const dActions: RemoteAction[] = scopeDecisions.flatMap((entry) => [
				{
					action: "decision.approve",
					label: `批准 ${entry.decisionId.slice(0, 10)}（委派范围）`,
					args: { decisionId: entry.decisionId },
				},
				{
					action: "decision.reject",
					label: `拒绝 ${entry.decisionId.slice(0, 10)}（委派范围）`,
					args: { decisionId: entry.decisionId },
					needsReason: true,
				},
			]);
			return {
				id: delegation.delegationId,
				layer: "delegation" as const,
				title: `${delegation.executorId} → ${delegation.objective.slice(0, 60)}`,
				subtitle: `${delegation.delegationId.slice(0, 12)} · 深度 ${delegation.depth} · ${delegation.budgetTokens} tokens`,
				checks: dChecks,
				status: statusOf(dChecks),
				actions: dActions,
				children: [],
			};
		});

		return {
			id: task.taskId,
			layer: "task",
			title: `${task.taskId} · ${task.goal.slice(0, 70)}`,
			subtitle: `${approved ? "已批准" : "待批准"}${accepted ? " · 已验收" : ""} · ${task.budgetTokens} tokens`,
			checks,
			status: statusOf(checks),
			actions,
			children: delegationItems,
		};
	});

	// A task-level decision whose kind says "delegation" still has to be visible
	// somewhere; attach it under the task it belongs to as a level-3 item without
	// a matching delegation record.
	for (const task of taskItems) {
		const orphan = decisions.filter(
			(entry) =>
				entry.taskId === task.id &&
				entry.result === "pending" &&
				layerOfDecision(entry.taskId, entry.kind) === "delegation" &&
				!task.children.some((child) =>
					child.actions.some((action) => JSON.stringify(action.args).includes(entry.decisionId)),
				),
		);
		for (const entry of orphan)
			task.children.push({
				id: entry.decisionId,
				layer: "delegation",
				title: `待审 ${DECISION_KIND_LABEL[entry.kind] ?? entry.kind} · ${entry.request.slice(0, 60)}`,
				subtitle: `${entry.decisionId.slice(0, 12)} · 无对应委派记录`,
				checks: [check("委派已授权", false, "该决策由委派被拒产生，批准后需重新提交任务修订")],
				status: "blocked",
				actions: [
					{
						action: "decision.approve",
						label: `批准 ${entry.decisionId.slice(0, 10)}`,
						args: { decisionId: entry.decisionId },
					},
					{
						action: "decision.reject",
						label: `拒绝 ${entry.decisionId.slice(0, 10)}`,
						args: { decisionId: entry.decisionId },
						needsReason: true,
					},
				],
				children: [],
			});
	}

	// RED-5: refused attempts belong in the tree, not only in the raw JSONL.
	// They are the level where "what was tried and stopped" becomes visible; a
	// refusal that only exists in log line 187 is a refusal nobody reviews.
	const refusals = state.events.filter(
		(event) => event.type === "redline.triggered" && event.sequence > state.archiveBoundary,
	);
	for (const task of taskItems) {
		const mine = refusals.filter((event) => event.taskId === task.id);
		if (!mine.length) continue;
		task.checks.push(
			check(
				"红线拒绝记录",
				false,
				`${mine.length} 次被拒：${[...new Set(mine.map((event) => String(event.payload.code ?? "unknown")))].join(", ")}`,
			),
		);
		for (const event of mine) {
			task.children.push({
				id: event.eventId,
				layer: "delegation",
				title: `被拒 · ${String(event.payload.operation ?? "unknown")}`,
				subtitle: `${String(event.payload.code ?? "unknown")} · ${String(event.payload.message ?? "")}`,
				checks: [
					check("已记录拒绝", true, `${event.recordedAt.slice(0, 19).replace("T", " ")}`),
					check("红线拦截", false, String(event.payload.message ?? "")),
				],
				status: "blocked",
				actions: [],
				children: [],
			});
		}
	}
	// A refused task never enters `state.tasks`, so there is no task node to hang
	// it under. Those attempts still have to be visible somewhere, and level 1 is
	// the honest place: what was rejected was the task against the baseline. Same
	// for a delegation refused before its task existed.
	const knownTasks = new Set(taskItems.map((item) => item.id));
	const orphanRefusals = refusals.filter((event) => !event.taskId || !knownTasks.has(event.taskId));
	for (const event of orphanRefusals)
		projectItem.children.push({
			id: event.eventId,
			layer: "project",
			title: `被拒 · ${String(event.payload.operation ?? "unknown")}${event.taskId ? ` · ${event.taskId}` : ""}`,
			subtitle: `${String(event.payload.code ?? "unknown")} · ${String(event.payload.message ?? "")}`,
			checks: [check("红线拦截", false, String(event.payload.message ?? ""))],
			status: "blocked",
			actions: [],
			children: [],
		});

	// Task levels first, then the refused attempts, because that is the order an
	// operator reads: what exists, then what was stopped.
	projectItem.children = [...taskItems, ...projectItem.children.filter((item) => !taskItems.includes(item))];
	return [projectItem];
}

export function eventLayer(eventType: string): RemoteAuditLayer | "other" {
	const type = eventType.replace(/^governance\./, "");
	if (type.startsWith("project") || type.startsWith("policy") || type.startsWith("agent")) return "project";
	// A red-line attempt is judged at the level that refused it: a task that
	// escapes the baseline is a level-2 finding, a delegation that exceeds its
	// ceiling is level-3. The taskId, not the event name, decides which.
	if (type === "redline.triggered") return "task";
	if (type.startsWith("task") || type.startsWith("decision")) return "task";
	if (
		type.startsWith("delegation") ||
		type.startsWith("run") ||
		type.startsWith("workspace") ||
		type.startsWith("session")
	)
		return "delegation";
	return "other";
}

const MAX_EVENTS = Number(process.env.GOV_EVENT_ROWS ?? 500);
const MAX_PAYLOAD_CHARS = 1200;

function shortHash(value: unknown): string {
	return typeof value === "string" ? value.replace(/^sha256:/, "").slice(0, 12) : "";
}

/**
 * Level 4 of the audit: the ledger lines themselves. The operator has to be
 * able to read the exact fields a decision came from, not only a summary.
 */
export function buildEventRows(state: GovernanceState, limit = MAX_EVENTS): RemoteEventRow[] {
	return state.events
		.filter((event) => event.sequence > state.archiveBoundary)
		.slice(-limit)
		.map((event) => {
			// The relay is outside the trusted ledger host. Never upload raw tool
			// arguments, prompts, free-text summaries, or environment material.
			const safePayload = {
				sourceEventId: event.eventId,
				...(typeof event.payload.tool === "string" ? { tool: event.payload.tool } : {}),
				...(typeof event.payload.outcome === "string" ? { outcome: event.payload.outcome } : {}),
				...(typeof event.payload.revision === "number" ? { revision: event.payload.revision } : {}),
				...(typeof event.payload.verificationId === "string"
					? { verificationId: event.payload.verificationId }
					: {}),
			};
			const payload = JSON.stringify(safePayload);
			return {
				sequence: event.sequence,
				eventType: event.eventType,
				actorId: event.actor.id,
				actorKind: event.actor.kind,
				subject: `${event.subject.type}:${event.subject.id}`,
				taskId: event.context.taskId,
				runId: event.context.runId,
				delegationId: event.context.delegationId,
				recordedAt: event.recordedAt,
				layer: eventLayer(event.eventType),
				payload: payload.length > MAX_PAYLOAD_CHARS ? `${payload.slice(0, MAX_PAYLOAD_CHARS)}…` : payload,
				eventHash: shortHash(event.integrity.eventHash),
				prevHash: shortHash(event.integrity.prevHash),
			};
		});
}

function pendingDecisionsFor(state: GovernanceState, taskId: string, kind: string) {
	return Object.values(state.decisions).filter(
		(entry) => entry.taskId === taskId && entry.kind === kind && entry.result === "pending",
	);
}

function readProjectFile(project: string, relative: string): string {
	try {
		return fs.readFileSync(path.join(project, relative), "utf8");
	} catch {
		return "";
	}
}

/**
 * Render the ledger into the payload the site displays. Views are regenerated
 * first so the page never shows a projection older than the ledger; a view
 * failure is advisory and never blocks the snapshot.
 */
export function buildSnapshot(project: string, kernel: GovernanceKernel): RemoteSnapshot {
	const state = kernel.getState();
	const initialized = state.events.find((event) => event.type === "project.initialized");
	const projectId =
		typeof initialized?.payload.projectId === "string" ? initialized.payload.projectId : path.basename(project);
	try {
		renderViews(project, kernel);
	} catch {
		/* views are read-only projections; a refusal to overwrite user docs is fine */
	}

	const workStatuses = queryTaskWorkStatuses(state);
	const tasks: RemoteTaskSummary[] = Object.values(state.tasks).map((task) => ({
		kind: task.kind ?? "executable",
		parentTaskId: task.parentTaskId ?? null,
		splitReason: task.splitReason ?? null,
		owner: task.owner,
		scope: task.scope,
		acceptance: task.acceptance,
		dependencies: task.dependencies.map((entry) => entry.taskId),
		work: workStatuses[task.taskId],
		deliverables: Object.values(state.deliverables)
			.filter((entry) => entry.taskId === task.taskId)
			.map((entry) => ({
				deliverableId: entry.deliverableId,
				commit: entry.commit,
				runId: entry.runId,
				sessionId: entry.sessionId ?? null,
				verification:
					Object.values(state.verifications)
						.filter((item) => item.deliverableId === entry.deliverableId)
						.at(-1)?.result ?? null,
			})),
		taskId: task.taskId,
		revision: task.revision,
		goal: task.goal,
		budgetTokens: task.budgetTokens,
		state: state.accepted[task.taskId]
			? "accepted"
			: state.cancelled[task.taskId]?.revision === task.revision
				? "cancelled"
				: state.approved[task.taskId] === task.revision
					? "approved"
					: "draft",
	}));
	const pendingDecisions: RemoteDecisionSummary[] = Object.values(state.decisions)
		.filter((decision) => decision.result === "pending")
		.map((decision) => {
			// Surface why this needs a human: rule id, risk and the matched inputs
			// are already in the ledger, so the operator does not have to guess.
			const evaluation = state.events
				.filter((event) => event.taskId === decision.taskId && event.payload.approvalEvaluation)
				.at(-1)?.payload.approvalEvaluation as
				| { ruleId?: string; risk?: string; effect?: string; inputs?: Record<string, unknown> }
				| undefined;
			return {
				decisionId: decision.decisionId,
				taskId: decision.taskId,
				revision: decision.revision,
				kind: decision.kind,
				request: decision.request,
				result: decision.result,
				ruleId: typeof evaluation?.ruleId === "string" ? evaluation.ruleId : null,
				risk: typeof evaluation?.risk === "string" ? evaluation.risk : null,
				reasons: reasonsFor(evaluation?.inputs),
				layer: decision.kind === "scope" || decision.kind === "operation" ? "delegation" : ("task" as const),
			};
		});
	// Keep a small recent terminal window so finishing a child does not erase its
	// last observable action from the work view. Older history remains available
	// through the ledger and local Run inspection without rescanning every log.
	const recentTerminalRunIds = new Set(
		Object.values(state.runs)
			.filter((run) => ["SUCCEEDED", "FAILED", "CANCELLED"].includes(run.state))
			.slice(-5)
			.map((run) => run.runId),
	);
	const runs: RemoteRunSummary[] = Object.values(state.runs).map((run) => ({
		runId: run.runId,
		taskId: run.taskId,
		delegationId: run.delegationId,
		executorId: run.executorId,
		state: run.state,
		model: run.routing?.model ?? null,
		usageTokens: run.usageTokens,
		retryOf: run.retryOf,
		nativeLinked: run.nativeRunId !== null,
		costUsd: run.costUsd,
		observation: (() => {
			if (
				run.state !== "RUNNING" &&
				run.state !== "CREATED" &&
				run.state !== "PAUSED" &&
				run.state !== "INTERRUPTED" &&
				!recentTerminalRunIds.has(run.runId)
			)
				return null;
			const observed = observeRun(run);
			const recentTools: RemoteToolObservation[] = observed.activity.tools.slice(-5).map((tool) => {
				let projectPath: string | null = null;
				if (
					tool.target &&
					tool.target.length < 200 &&
					!/[\r\n\0]/.test(tool.target) &&
					["read", "write", "edit"].includes(tool.tool)
				) {
					const relative = path.relative(project, path.resolve(project, tool.target));
					if (
						relative &&
						relative !== ".." &&
						!relative.startsWith(`..${path.sep}`) &&
						!path.isAbsolute(relative) &&
						!/(?:^|\/)(?:\.|[^/]*(?:secret|credential|token|password|private[-_]?key)[^/]*)/i.test(relative)
					)
						projectPath = relative.slice(0, 160);
				}
				return { name: tool.tool, projectPath, at: tool.at, result: tool.result };
			});
			return {
				source: "pi-subagents-native" as const,
				observedAt: observed.observedAt,
				available: observed.native.state !== null || observed.activity.unavailable === null,
				nativeState: observed.native.state,
				nativeOutcome: observed.native.outcome,
				activityState: observed.native.activityState,
				actualModel: observed.native.model,
				turns: observed.native.turns,
				toolCount: observed.native.tools,
				outputTokens: observed.native.outputTokens,
				windowTokens: observed.native.windowTokens,
				lastOutputAt: observed.activity.lastOutputAt,
				lastTool: recentTools.at(-1) ?? null,
				recentTools,
				gap:
					observed.native.state === null
						? "原生状态不可读取"
						: observed.activity.unavailable
							? "原生工具事件不可读取"
							: null,
			};
		})(),
	}));

	const draft = state.projectDraft;
	const baseline = state.projectApproved;
	const contract = baseline ?? draft ?? null;
	// Same rule as the kernel: only Tasks with a standing approval reserve.
	const allocatedTokens = reservedBudget(state);
	const gates: RemoteGates = {
		allowInternalTasks: contract?.delegationPolicy.allowInternalTasks ?? null,
		maxDepth: contract?.delegationPolicy.maxDepth ?? null,
		maxConcurrent: contract?.delegationPolicy.maxConcurrent ?? null,
		approvalDefault: contract?.approvalPolicy?.defaultEffect ?? null,
		approvalRules: contract?.approvalPolicy?.rules.map((rule) => `${rule.id}:${rule.effect}`) ?? [],
		authorityPaths: contract ? [...contract.authority.paths] : [],
		authorityTools: contract ? [...contract.authority.tools] : [],
		writeWorkspace: contract?.authority.writeWorkspace ?? null,
		commitBranch: contract?.authority.commitBranch ?? null,
		integrateBranch: contract?.authority.integrateBranch ?? null,
		budgetTokens: contract?.resourceLimits.budgetTokens ?? null,
		allocatedTokens,
		activeRuns: Object.values(state.runs).filter((run) =>
			["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"].includes(run.state),
		).length,
	};

	// The audit tree owns the approvals: a project draft is a level-1 decision,
	// a task revision a level-2 one, a refused delegation a level-3 one. The flat
	// action list is derived from the same tree so the panel cannot show an
	// approval in a layer it does not belong to.
	const audit = buildAudit(project, kernel);
	const events = buildEventRows(state);
	const flatten = (items: RemoteAuditItem[]): RemoteAction[] =>
		items.flatMap((item) => [...item.actions, ...flatten(item.children)]);
	const actions: RemoteAction[] = flatten(audit);
	// Verification acceptance has no ledger decision to hang on yet, so it is the
	// only action still appended outside the tree.
	for (const verification of Object.values(state.verifications) as Verification[]) {
		if (verification.result !== "passed" || state.accepted[verification.taskId]) continue;
		actions.push({
			action: "task.accept",
			label: `验收 ${verification.taskId}`,
			args: { taskId: verification.taskId, verificationId: verification.verificationId },
		});
	}

	return {
		projectId,
		name: path.basename(project),
		cwd: project,
		sequence: state.events.at(-1)?.sequence ?? 0,
		projectStatus: state.projectStatus,
		closed: state.projectStatus === "REVOKED",
		baselineRevision: baseline?.revision ?? null,
		draftRevision: draft?.revision ?? null,
		tasks,
		pendingDecisions,
		runs,
		gates,
		audit,
		agentTree: queryAgentTree(state),
		mainAgents: queryMainAgentStatuses(state),
		taskTree: queryTaskTree(state),
		activity: queryActivityTimeline(state, { limit: 200 }),
		events,
		actions,
		nowMarkdown: readProjectFile(project, "management/NOW.md"),
		inboxMarkdown: readProjectFile(project, "management/INBOX.md"),
		tasksMarkdown: readProjectFile(project, "management/views/TASKS.md"),
		projectMarkdown: readProjectFile(project, "management/PROJECT.md"),
		archives: queryArchives(state),
		archiveMarkdown: readProjectFile(project, "management/ARCHIVE.md"),
		resetBoundary: state.resetBoundary,
		archiveBoundary: state.archiveBoundary,
		projectRevisionFloor: state.projectRevisionFloor,
		contract: baseline ?? draft ?? null,
		subagentConfig: (() => {
			try {
				return subagentPolicyStatus(project, state);
			} catch {
				return null;
			}
		})(),
		updatedAt: new Date().toISOString(),
	};
}

function numberArg(args: Record<string, unknown>, key: string): number {
	const value = args[key];
	if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${key} 必须是数字`);
	return value;
}

function stringArg(args: Record<string, unknown>, key: string): string {
	const value = args[key];
	if (typeof value !== "string" || !value.trim()) throw new Error(`${key} 必须是非空字符串`);
	return value;
}

/**
 * Execute one browser command against the local ledger. The expected sequence
 * guard makes a stale page harmless: the command is refused before any write.
 */
export function applyCommand(
	kernel: GovernanceKernel,
	command: RemoteCommand,
	actor: string = REMOTE_ACTOR,
	project?: string,
): RemoteCommandResult {
	const args = command.args ?? {};
	const current = kernel.getState();
	const sequence = current.events.at(-1)?.sequence ?? 0;
	if (typeof command.expectedSequence === "number" && command.expectedSequence !== sequence)
		return {
			state: "stale",
			message: `状态已变（页面基于 #${command.expectedSequence}，当前 #${sequence}），请刷新后重试`,
		};
	try {
		switch (command.action) {
			case "policy.validate": {
				validateSubagentPolicy(args.policy);
				return { state: "accepted", message: "Subagent configuration is structurally valid" };
			}
			case "policy.save": {
				if (!project) throw new Error("Local project path is required");
				const expectedDigest = stringArg(args, "expectedDigest");
				const result = saveSubagentPolicy(project, kernel, args.policy, expectedDigest, actor);
				return { state: "accepted", message: `Subagent configuration saved and synchronized: ${result.digest}` };
			}
			case "policy.approve": {
				if (!project) throw new Error("Local project path is required");
				if (subagentPolicyStatus(project, current).digest !== stringArg(args, "expectedDigest"))
					throw new Error("Subagent policy changed; reload before approval");
				approveSubagentPolicy(project, kernel, actor);
				return { state: "accepted", message: "Subagent configuration approved" };
			}
			case "project.approve":
				kernel.approveProject(numberArg(args, "revision"), actor);
				return { state: "accepted", message: `已批准项目契约 r${args.revision}` };
			case "project.reject":
				kernel.rejectProject(numberArg(args, "revision"), actor, stringArg(args, "reason"));
				return { state: "accepted", message: `已拒绝项目草稿 r${args.revision}` };
			case "project.pause":
				kernel.controlProject("pause", actor);
				return { state: "accepted", message: "项目已暂停" };
			case "project.resume":
				kernel.controlProject("resume", actor);
				return { state: "accepted", message: "项目已恢复" };
			case "project.revoke":
				kernel.controlProject("revoke", actor);
				return { state: "accepted", message: "项目已收尾，面板将不再显示" };
			case "project.reset": {
				const event = kernel.resetProject({
					actor,
					reason: stringArg(args, "reason"),
					confirm: stringArg(args, "confirm"),
				});
				return {
					state: "accepted",
					message: `治理已重置（序号 ${event.sequence}）；历史保留，需重新提交并批准基线`,
				};
			}
			case "project.archive": {
				const event = kernel.archiveHistory({
					actor,
					reason: stringArg(args, "reason"),
					confirm: stringArg(args, "confirm"),
				});
				return {
					state: "accepted",
					message: `已归档 ${String(event.payload.archiveId)}；当前工作区为空，历史见 ARCHIVE.md`,
				};
			}
			case "decision.approve":
			case "decision.reject": {
				const decisionId = stringArg(args, "decisionId");
				const decision = current.decisions[decisionId];
				const approving = command.action === "decision.approve";
				// Task decisions are only actionable when their scope matches what
				// approveTask validates ("task revision"); reuse it instead of the
				// web label so the binding step can run.
				const scope = decision?.kind === "task" ? "task revision" : "web";
				const reason = typeof args.reason === "string" ? args.reason.trim() : "";
				// A rejection reason is evidence, not decoration: keep it in the ledger.
				kernel.recordDecision(
					decisionId,
					approving ? "approved" : "rejected",
					actor,
					scope,
					null,
					reason ? [reason] : [],
				);
				if (approving && decision?.kind === "task") {
					try {
						kernel.approveTask(decision.taskId, decisionId, actor);
						return { state: "accepted", message: `已批准任务 ${decision.taskId}` };
					} catch (error) {
						return {
							state: "rejected",
							message: `决策已记录，但任务未绑定：${error instanceof Error ? error.message : String(error)}`,
						};
					}
				}
				return { state: "accepted", message: `已记录决策 ${decisionId}` };
			}
			case "task.approve": {
				const taskId = stringArg(args, "taskId");
				const decisionId = stringArg(args, "decisionId");
				if (current.decisions[decisionId]?.result === "pending")
					kernel.recordDecision(decisionId, "approved", actor, "task revision", null, []);
				kernel.approveTask(taskId, decisionId, actor);
				return { state: "accepted", message: `已批准任务 ${taskId}` };
			}
			case "task.accept":
				kernel.acceptTask(stringArg(args, "taskId"), stringArg(args, "verificationId"), actor);
				return { state: "accepted", message: `已验收任务 ${args.taskId}` };
			default:
				return { state: "rejected", message: `未知动作：${command.action}` };
		}
	} catch (error) {
		return { state: "rejected", message: error instanceof Error ? error.message : String(error) };
	}
}

type Timer = ReturnType<typeof setTimeout>;

/**
 * Debounce ledger churn and enforce a minimum gap between pushes. Dense events
 * (a delegation writes several) collapse into one request.
 */
export function createPushScheduler(
	push: () => void | Promise<void>,
	options: { debounceMs?: number; minIntervalMs?: number } = {},
): { schedule: () => void; stop: () => void } {
	const debounceMs = options.debounceMs ?? PUSH_DEBOUNCE_MS;
	const minIntervalMs = options.minIntervalMs ?? PUSH_MIN_INTERVAL_MS;
	let debounceTimer: Timer | null = null;
	let gapTimer: Timer | null = null;
	let lastPushAt = 0;
	let stopped = false;

	const fire = () => {
		if (stopped) return;
		lastPushAt = Date.now();
		try {
			void push();
		} catch {
			/* a failed push is retried by the next ledger change */
		}
	};

	const schedule = () => {
		if (stopped) return;
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			debounceTimer = null;
			const wait = Math.max(0, minIntervalMs - (Date.now() - lastPushAt));
			if (wait === 0) {
				fire();
				return;
			}
			if (gapTimer) return;
			gapTimer = setTimeout(() => {
				gapTimer = null;
				fire();
			}, wait);
		}, debounceMs);
	};

	const stop = () => {
		stopped = true;
		if (debounceTimer) clearTimeout(debounceTimer);
		if (gapTimer) clearTimeout(gapTimer);
		debounceTimer = null;
		gapTimer = null;
	};

	return { schedule, stop };
}

export type JsonResponse = { status: number; body: unknown };

export function requestJson(
	url: string,
	options: { method?: string; headers?: Record<string, string>; body?: unknown; timeoutMs?: number } = {},
): Promise<JsonResponse> {
	return new Promise((resolve, reject) => {
		const target = new URL(url);
		const transport = target.protocol === "https:" ? https : http;
		const payload = options.body === undefined ? null : Buffer.from(JSON.stringify(options.body));
		const headers: Record<string, string> = { ...(options.headers ?? {}) };
		if (payload) {
			headers["content-type"] = "application/json";
			headers["content-length"] = String(payload.length);
		}
		const request = transport.request(target, { method: options.method ?? "GET", headers }, (response) => {
			let raw = "";
			response.setEncoding("utf8");
			response.on("data", (chunk) => {
				raw += chunk;
			});
			response.on("end", () => {
				let body: unknown = raw;
				try {
					body = raw ? JSON.parse(raw) : null;
				} catch {
					/* keep the raw body */
				}
				resolve({ status: response.statusCode ?? 0, body });
			});
		});
		request.setTimeout(options.timeoutMs ?? 15_000, () => request.destroy(new Error("timeout")));
		request.on("error", reject);
		if (payload) request.write(payload);
		request.end();
	});
}

export type RemoteEvent = { type: string; data: string; id?: string };

export function openEventStream(
	url: string,
	options: {
		headers?: Record<string, string>;
		onEvent: (event: RemoteEvent) => void;
		onOpen?: () => void;
		onClose?: (error?: Error) => void;
	},
): { close: () => void } {
	const target = new URL(url);
	const transport = target.protocol === "https:" ? https : http;
	let closed = false;
	const request = transport.request(
		target,
		{ method: "GET", headers: { accept: "text/event-stream", ...(options.headers ?? {}) } },
		(response) => {
			if ((response.statusCode ?? 0) !== 200) {
				response.resume();
				options.onClose?.(new Error(`stream status ${response.statusCode}`));
				return;
			}
			options.onOpen?.();
			response.setEncoding("utf8");
			let buffer = "";
			response.on("data", (chunk: string) => {
				buffer += chunk;
				let boundary = buffer.indexOf("\n\n");
				while (boundary >= 0) {
					const block = buffer.slice(0, boundary);
					buffer = buffer.slice(boundary + 2);
					let type = "message";
					let id: string | undefined;
					const data: string[] = [];
					for (const line of block.split("\n")) {
						const clean = line.endsWith("\r") ? line.slice(0, -1) : line;
						if (clean.startsWith(":")) continue;
						if (clean.startsWith("event:")) type = clean.slice(6).trim();
						else if (clean.startsWith("data:")) data.push(clean.slice(5).trimStart());
						else if (clean.startsWith("id:")) id = clean.slice(3).trim();
					}
					if (data.length) options.onEvent({ type, data: data.join("\n"), id });
					boundary = buffer.indexOf("\n\n");
				}
			});
			response.on("end", () => options.onClose?.());
			response.on("error", (error: Error) => options.onClose?.(error));
		},
	);
	request.on("error", (error: Error) => {
		if (!closed) options.onClose?.(error);
	});
	request.end();
	return {
		close: () => {
			closed = true;
			request.destroy();
		},
	};
}

/** A lock older than this is treated as abandoned even if the PID is alive. */
export const SIDECAR_LOCK_MAX_AGE_MS = 24 * 60 * 60 * 1000;

/**
 * The lock lives next to the ledger, not in `.pi/`, because `.pi/` is per
 * worktree while the ledger (git common dir) is shared. Two worktrees of the
 * same repository must contend for the same lock: they share one ledger and
 * one command stream. The name is `remote.pid` to keep it distinct from the
 * short-lived `writer.lock` that arbitrates individual ledger appends.
 */
export function sidecarLockPath(project: string): string {
	return path.join(dataRoot(project), "remote.pid");
}

/**
 * One sidecar per ledger. A second pi session in the same repository (or a
 * worktree, which shares the ledger) must not open a second command stream:
 * the server broadcasts each command to every subscriber, so two sidecars
 * would execute the same approval twice and can collide on `writer.lock`.
 */
export function acquireSidecarLock(project: string): { release: () => void } | null {
	let file: string;
	try {
		file = sidecarLockPath(project);
		fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
	} catch {
		return null;
	}
	try {
		if (fs.existsSync(file)) {
			const [pidLine, timeLine] = fs.readFileSync(file, "utf8").split("\n");
			const pid = Number(pidLine);
			const acquiredAt = Number(timeLine);
			// PID reuse is real: a live PID is not proof the sidecar is alive when
			// the record is older than the cap, so age wins over the liveness probe.
			const expired = Number.isFinite(acquiredAt) && Date.now() - acquiredAt > SIDECAR_LOCK_MAX_AGE_MS;
			if (!expired && Number.isSafeInteger(pid) && pid > 0) {
				try {
					process.kill(pid, 0);
					return null;
				} catch {
					/* previous owner is gone: take over */
				}
			}
		}
		fs.writeFileSync(file, `${process.pid}\n${Date.now()}\n`, { mode: 0o600 });
	} catch {
		return null;
	}
	return {
		release: () => {
			try {
				const pid = Number(fs.readFileSync(file, "utf8").split("\n")[0]);
				// Only delete the record if it still belongs to this process.
				if (pid === process.pid) fs.rmSync(file, { force: true });
			} catch {
				/* nothing to release */
			}
		},
	};
}

export type SidecarOptions = {
	project: string;
	apiUrl?: string;
	token?: string;
	actor?: string;
	log?: (message: string) => void;
	reconnectMinMs?: number;
	reconnectMaxMs?: number;
};

export type SidecarHandle = {
	projectId: string;
	stop: () => void;
	pushNow: () => Promise<void>;
	snapshot: () => RemoteSnapshot;
};

/**
 * Start the sidecar for one project. Resolves to a handle whose `stop()` closes
 * the SSE stream, the ledger watcher and any pending timers.
 */
export function startSidecar(options: SidecarOptions): SidecarHandle {
	const project = fs.realpathSync(path.resolve(options.project));
	const apiUrl = (options.apiUrl ?? process.env.GOV_API_URL ?? process.env.BLOG_API_URL ?? DEFAULT_API_URL).replace(
		/\/+$/,
		"",
	);
	const token = options.token ?? process.env.BLOG_TOKEN ?? "";
	const actor = options.actor ?? REMOTE_ACTOR;
	const log = options.log ?? ((message: string) => console.error(`[gov-remote] ${message}`));
	const reconnectMinMs = options.reconnectMinMs ?? 1_000;
	const reconnectMaxMs = options.reconnectMaxMs ?? 30_000;

	const store = new GovernanceStore(dataRoot(project));
	const kernel = new GovernanceKernel(store);
	let snapshot = buildSnapshot(project, kernel);
	const projectId = snapshot.projectId;

	let stopped = false;
	let stream: { close: () => void } | null = null;
	let reconnectTimer: Timer | null = null;
	let nativeObservationTimer: Timer | null = null;
	let reconnectAttempt = 0;
	let watcher: fs.FSWatcher | null = null;
	const appliedCommands = new Set<string>();
	let activitySyncedThrough = 0;
	let evidenceSyncedThrough = 0;

	const pushNow = async (): Promise<void> => {
		if (!token) return;
		try {
			snapshot = buildSnapshot(project, kernel);
			const pushed = await requestJson(`${apiUrl}/api/projects/${encodeURIComponent(projectId)}/snapshot`, {
				method: "POST",
				headers: { authorization: `Bearer ${token}` },
				body: snapshot,
			});
			if (pushed.status !== 200) throw new Error(`snapshot status ${pushed.status}`);
			const state = store.read();
			const evidence = buildEventRows(state, state.events.length).filter(
				(row) => row.sequence > evidenceSyncedThrough,
			);
			for (let offset = 0; offset < evidence.length; offset += 100) {
				const uploaded = await requestJson(`${apiUrl}/api/projects/${encodeURIComponent(projectId)}/evidence`, {
					method: "POST",
					headers: { authorization: `Bearer ${token}` },
					body: { items: evidence.slice(offset, offset + 100) },
				});
				if (uploaded.status !== 200) throw new Error(`evidence status ${uploaded.status}`);
			}
			evidenceSyncedThrough = state.events.at(-1)?.sequence ?? 0;
			const rows = queryActivityTimeline(state, { limit: state.events.length }).items;
			const changed = rows.filter(
				(item) =>
					item.sequence > activitySyncedThrough ||
					item.sourceSequences.some((sequence) => sequence > activitySyncedThrough),
			);
			for (let offset = 0; offset < changed.length; offset += 100) {
				const uploaded = await requestJson(`${apiUrl}/api/projects/${encodeURIComponent(projectId)}/activity`, {
					method: "POST",
					headers: { authorization: `Bearer ${token}` },
					body: { items: changed.slice(offset, offset + 100) },
				});
				if (uploaded.status !== 200) throw new Error(`activity status ${uploaded.status}`);
			}
			activitySyncedThrough = state.events.at(-1)?.sequence ?? 0;
		} catch (error) {
			log(`snapshot push failed: ${error instanceof Error ? error.message : String(error)}`);
		}
	};

	const scheduler = createPushScheduler(() => pushNow());

	const reportResult = async (id: string, result: RemoteCommandResult): Promise<void> => {
		try {
			await requestJson(
				`${apiUrl}/api/projects/${encodeURIComponent(projectId)}/commands/${encodeURIComponent(id)}/result`,
				{ method: "POST", headers: { authorization: `Bearer ${token}` }, body: result },
			);
		} catch (error) {
			log(`command result failed: ${error instanceof Error ? error.message : String(error)}`);
		}
	};

	const handleEvent = (event: RemoteEvent) => {
		if (event.type !== "command") return;
		let command: RemoteCommand & { id?: string };
		try {
			command = JSON.parse(event.data) as RemoteCommand & { id?: string };
		} catch {
			log("ignored malformed command");
			return;
		}
		const id = command.id ?? event.id ?? "";
		if (id && appliedCommands.has(id)) return;
		if (id) {
			appliedCommands.add(id);
			if (appliedCommands.size > 200) {
				const oldest = appliedCommands.values().next().value;
				if (oldest !== undefined) appliedCommands.delete(oldest);
			}
		}
		const result = applyCommand(kernel, command, actor, project);
		log(`${command.action} -> ${result.state}: ${result.message}`);
		if (id) void reportResult(id, result);
		if (result.state === "accepted") scheduler.schedule();
	};

	const scheduleReconnect = () => {
		if (stopped || reconnectTimer) return;
		const delay = Math.min(reconnectMaxMs, reconnectMinMs * 2 ** reconnectAttempt);
		reconnectAttempt += 1;
		reconnectTimer = setTimeout(() => {
			reconnectTimer = null;
			connect();
		}, delay);
	};

	const connect = () => {
		if (stopped) return;
		stream = openEventStream(`${apiUrl}/api/projects/${encodeURIComponent(projectId)}/stream`, {
			headers: { authorization: `Bearer ${token}` },
			onOpen: () => {
				reconnectAttempt = 0;
				void pushNow();
			},
			onEvent: handleEvent,
			onClose: (error) => {
				stream = null;
				if (stopped) return;
				if (error) log(`stream closed: ${error.message}`);
				scheduleReconnect();
			},
		});
	};

	if (!token) {
		log("BLOG_TOKEN is not set; sidecar is dormant (snapshot and commands are disabled)");
		return { projectId, stop: () => undefined, pushNow, snapshot: () => snapshot };
	}

	const unsubscribe = store.onAppend(() => scheduler.schedule());
	nativeObservationTimer = setInterval(() => {
		if (stopped) return;
		const active = Object.values(kernel.getState().runs).filter((run) =>
			["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"].includes(run.state),
		);
		if (!active.length) return;
		for (const run of active) {
			if (run.state !== "RUNNING") continue;
			try {
				const native = readNativeRunStatus(run);
				if (native.processTerminal === "observed" && native.terminalOutcome)
					reconcileNativeRun(kernel, run.runId, actor);
			} catch (error) {
				log(
					`native reconciliation failed for ${run.runId}: ${error instanceof Error ? error.message : String(error)}`,
				);
			}
		}
		scheduler.schedule();
	}, NATIVE_OBSERVATION_INTERVAL_MS);
	try {
		watcher = fs.watch(store.root, (_event, filename) => {
			if (!filename || filename.toString() === "events.jsonl") scheduler.schedule();
		});
		watcher.on("error", () => undefined);
	} catch (error) {
		log(`ledger watch unavailable: ${error instanceof Error ? error.message : String(error)}`);
	}

	connect();
	scheduler.schedule();

	return {
		projectId,
		stop: () => {
			stopped = true;
			scheduler.stop();
			unsubscribe();
			watcher?.close();
			stream?.close();
			if (reconnectTimer) clearTimeout(reconnectTimer);
			if (nativeObservationTimer) clearInterval(nativeObservationTimer);
		},
		pushNow,
		snapshot: () => snapshot,
	};
}

export async function main(argv: string[] = process.argv.slice(2)): Promise<void> {
	let project = process.cwd();
	let apiUrl: string | undefined;
	let token: string | undefined;
	for (let index = 0; index < argv.length; index += 1) {
		const arg = argv[index];
		if (arg === "--project") project = argv[++index] ?? project;
		else if (arg === "--api-url") apiUrl = argv[++index];
		else if (arg === "--token") token = argv[++index];
		else if (!arg.startsWith("-")) project = arg;
	}
	const lock = acquireSidecarLock(project);
	if (!lock) {
		console.error(`[gov-remote] another sidecar owns this ledger (${sidecarLockPath(project)}); exiting`);
		return;
	}
	const sidecar = startSidecar({ project, apiUrl, token });
	const shutdown = () => {
		sidecar.stop();
		lock.release();
		process.exit(0);
	};
	process.on("SIGINT", shutdown);
	process.on("SIGTERM", shutdown);
	console.error(
		`[gov-remote] ${project} -> ${apiUrl ?? process.env.GOV_API_URL ?? process.env.BLOG_API_URL ?? DEFAULT_API_URL}`,
	);
}

const entry = process.argv[1];
if (entry && path.resolve(entry) === fileURLToPath(import.meta.url)) void main();
