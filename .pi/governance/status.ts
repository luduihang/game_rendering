import * as path from "node:path";
import { reservedBudget } from "./kernel.ts";
import { observeRun } from "./native-observability.ts";
import { describeOrphanCandidates, scanOrphanRuns } from "./orphan-scan.ts";
import { queryTaskWorkStatuses, type TaskWorkStatus } from "./task-work-status.ts";
import type { GovernanceState, RunState } from "./types.ts";

// Run states, split the way the kernel and the web projection already do:
// "active" is whatever still holds a concurrency slot, "terminal" is finished.
const ACTIVE_RUN_STATES: RunState[] = ["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"];

/**
 * States a Run reaches by finishing, as opposed to being stopped.
 *
 * `CANCELLED` is deliberately absent. A cancelled Run also lacks usage in the
 * ledger, but the operator chose to stop it, so its cost is a decision rather than
 * an unexplained gap, and the two must not be added into one figure.
 */
const UNMEASURED_RUN_STATES: RunState[] = ["SUCCEEDED", "FAILED"];

export type StatusTask = {
	taskId: string;
	revision: number;
	kind: "container" | "executable";
	work: TaskWorkStatus["work"];
	authorization: TaskWorkStatus["authorization"];
	reason: string | null;
	next: TaskWorkStatus["next"];
};

export type ProjectStatus = {
	project: {
		status: string;
		revision: number | null;
		goal: string | null;
	};
	budget: {
		total: number;
		reserved: number;
		committed: number;
		unknownRunCount: number;
		cancelledRunCount: number;
		available: number;
	};
	tasks: StatusTask[];
	needsHuman: StatusTask[];
	/**
	 * Runs still in motion, with what the native side says they are doing.
	 *
	 * The ledger alone cannot tell a working child from a stalled one - both are just
	 * `RUNNING`. These figures are a snapshot taken at `observedAt`, not progress: the
	 * number of turns a task needs is unknown until it finishes, so a turn count must
	 * never be rendered as a percentage.
	 */
	activeRuns: {
		runId: string;
		taskId: string;
		executorId: string;
		state: RunState;
		observedAt: number;
		turns: number | null;
		tools: number | null;
		tokens: number | null;
		lastActivityAt: number | null;
		lastTool: string | null;
		unknowns: string[];
	}[];
	activeDelegations: { delegationId: string; taskId: string; executorId: string; state: string }[];
	/**
	 * Runs the ledger still calls active whose process is provably gone.
	 *
	 * Listed so a held slot is visible, never settled: see `orphan-scan.ts`.
	 */
	orphans: {
		candidates: {
			runId: string;
			taskId: string;
			executorId: string;
			state: RunState;
			reason: string;
			runningSince: number | null;
		}[];
		hints: string[];
		unavailable: string | null;
	};
	blockers: string[];
	nextActions: string[];
};

/**
 * The operator's front door: what exists, what waits on them, and how the
 * budget splits.
 *
 * Every figure is derived from the same sources the kernel uses rather than
 * re-derived: `reservedBudget` is the kernel's own rule, and each Task's work,
 * authorization and next action come from `queryTaskWorkStatuses`. A status
 * page that recomputes any of them with a cheaper rule would drift from what
 * the kernel actually enforces.
 */
export function projectStatus(state: GovernanceState, project: string): ProjectStatus {
	// Commands are emitted with an absolute path so they run from any cwd.
	const cli = `node ${path.join(project, ".pi", "governance", "cli.ts")}`;
	const runs = Object.values(state.runs);
	const work = queryTaskWorkStatuses(state);
	const orphanScan = scanOrphanRuns(state);
	// Open work is anything not terminal: accepted is done, cancelled is gone
	// (its work status says so in plain words, and it must not come back as
	// "awaiting approval").
	const tasks: StatusTask[] = Object.values(state.tasks)
		.filter((task) => work[task.taskId].work !== "ACCEPTED" && work[task.taskId].work !== "CANCELLED")
		.map((task) => ({
			taskId: task.taskId,
			revision: task.revision,
			kind: task.kind ?? "executable",
			work: work[task.taskId].work,
			authorization: work[task.taskId].authorization,
			reason: work[task.taskId].reason,
			next: work[task.taskId].next,
		}));
	const activeRuns = runs
		.filter((run) => ACTIVE_RUN_STATES.includes(run.state))
		.map((run) => {
			// Reading the native side is best-effort by design: a status page that threw
			// because one sidecar was gone would hide every other Run.
			let observation: ReturnType<typeof observeRun> | null = null;
			try {
				observation = observeRun(run);
			} catch {
				observation = null;
			}
			const lastTool = observation?.activity.tools.at(-1);
			return {
				runId: run.runId,
				taskId: run.taskId,
				executorId: run.executorId,
				state: run.state,
				observedAt: observation?.observedAt ?? Date.now(),
				turns: observation?.native.turns ?? null,
				tools: observation?.native.tools ?? null,
				tokens: observation?.native.tokens ?? null,
				lastActivityAt: observation?.native.lastActivityAt ?? null,
				lastTool: lastTool ? `${lastTool.tool}${lastTool.target ? ` ${lastTool.target}` : ""}` : null,
				unknowns: observation?.unknowns ?? ["native side unreadable"],
			};
		});
	const activeDelegations = Object.values(state.delegations).flatMap((delegation) => {
		const states = runs
			.filter((run) => run.delegationId === delegation.delegationId && ACTIVE_RUN_STATES.includes(run.state))
			.map((run) => run.state);
		// A delegation is live only while one of its Runs is: an authorized but
		// unstarted delegation has nothing in motion to report.
		return states.length
			? [
					{
						delegationId: delegation.delegationId,
						taskId: delegation.taskId,
						executorId: delegation.executorId,
						state: [...new Set(states)].sort().join(","),
					},
				]
			: [];
	});
	const total = (state.projectApproved ?? state.projectDraft)?.resourceLimits.budgetTokens ?? 0;
	const reserved = reservedBudget(state);
	const budget = {
		total,
		reserved,
		committed: runs.reduce((sum, run) => sum + (run.usageTokens ?? 0), 0),
		// Only Runs that finished on their own can be unknown. A cancelled Run has no
		// recorded usage either, but that is a different fact: the operator stopped it,
		// so the cost is a known decision rather than an accounting hole. Counting both
		// together reports "1 unknown spend" for work that was deliberately killed,
		// which sends the reader looking for a leak that is not there.
		unknownRunCount: runs.filter((run) => run.usageTokens === null && UNMEASURED_RUN_STATES.includes(run.state))
			.length,
		// Cancelled Runs whose spend was never captured. Separate from unknown above
		// because it is recoverable: the native side still holds the figure, so this
		// number is a to-do for reconciliation, not an unexplained gap.
		cancelledRunCount: runs.filter((run) => run.usageTokens === null && run.state === "CANCELLED").length,
		available: total - reserved,
	};
	const blockers: string[] = [];
	if (!state.projectApproved) blockers.push("没有已批准的项目基线，不能开始新任务或委派");
	else if (state.projectStatus === "PAUSED") blockers.push("项目已暂停，新授权已停止");
	for (const task of tasks)
		if (task.work === "BLOCKED" && task.reason) blockers.push(`${task.taskId}：${task.reason}`);
	const nextActions: string[] = [];
	const draft = state.projectDraft;
	if (draft && draft.revision !== state.projectApproved?.revision && state.projectRejectedRevision !== draft.revision)
		nextActions.push(`${cli} project approve ${draft.revision}`);
	if (state.projectStatus === "PAUSED") nextActions.push(`${cli} project resume`);
	for (const task of tasks) {
		if (!task.next) continue;
		if (task.next.action === "task.approve") {
			// The approve command needs the pending decision id; the work status
			// only points at approval when such a decision exists.
			const decision = Object.values(state.decisions).find(
				(entry) =>
					entry.taskId === task.taskId &&
					entry.revision === task.revision &&
					entry.kind === "task" &&
					entry.result === "pending",
			);
			if (decision) nextActions.push(`${cli} task approve ${task.taskId} ${decision.decisionId}`);
		} else if (task.next.action === "task.accept") {
			// The accept command needs the verification of the latest deliverable,
			// derived the same way the work status did.
			const latest = Object.values(state.deliverables)
				.filter((entry) => entry.taskId === task.taskId && entry.revision === task.revision)
				.at(-1);
			const verification =
				latest &&
				Object.values(state.verifications)
					.filter((entry) => entry.deliverableId === latest.deliverableId)
					.at(-1);
			if (verification?.result === "passed")
				nextActions.push(`${cli} task accept ${task.taskId} ${verification.verificationId}`);
		} else nextActions.push(`修订任务 ${task.taskId} 并重新提交（governance_task_create）`);
	}
	if (!nextActions.length && !state.projectApproved && !state.projectDraft)
		nextActions.push("与 Pi 讨论项目目标与边界，用 governance_project_draft 生成草稿");
	return {
		project: {
			status: state.projectStatus,
			revision: state.projectApproved?.revision ?? null,
			goal: state.projectApproved?.goal ?? state.projectDraft?.goal ?? null,
		},
		budget,
		tasks,
		// A Task needs the human when its approval is still outstanding: that is
		// the one state where their single action starts the work.
		needsHuman: tasks.filter((task) => task.authorization === "pending"),
		activeRuns,
		activeDelegations,
		// Reported, never settled here: `gov status` is a read, and a command that quietly
		// changed Run states would make running it a decision. The candidates are listed so
		// that a stuck slot is visible without digging, and each one carries the command
		// that would settle it.
		orphans: {
			candidates: orphanScan.candidates.map((candidate) => ({
				runId: candidate.runId,
				taskId: candidate.taskId,
				executorId: candidate.executorId,
				state: candidate.state,
				reason: candidate.probe.reason,
				runningSince: candidate.runningSince,
			})),
			hints: describeOrphanCandidates(orphanScan, cli),
			unavailable: orphanScan.unavailable,
		},
		blockers,
		nextActions,
	};
}
