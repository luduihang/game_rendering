import { taskAccepted } from "./task-tree.ts";
import type { GovernanceState, TaskContract } from "./types.ts";

/**
 * Work status owes the reader two separate answers: what state this Task is in, and
 * what (if anything) it is waiting on a human to do. They are separate fields because
 * a Task can be cancelled (state) without anything being actionable (next), and a Task
 * can need approval (next) while its work state is simply "not started".
 */
export type TaskWorkStatus = {
	taskId: string;
	authorization: "approved" | "pending";
	work:
		| "NOT_STARTED"
		| "READY"
		| "BLOCKED"
		| "IN_PROGRESS"
		| "AWAITING_DELIVERY"
		| "AWAITING_VERIFICATION"
		| "AWAITING_ACCEPTANCE"
		| "NEEDS_REWORK"
		| "ACCEPTED"
		| "CANCELLED";
	/**
	 * Plain-language explanation shown to the operator. Never an internal term: the
	 * reader of this field is a human asking "why is this sitting here".
	 */
	reason: string | null;
	/** The single action the operator can take right now, or null when none applies. */
	next: { action: "task.approve" | "task.accept" | "task.revise"; taskId: string } | null;
	cancelledReason: string | null;
	acceptedChildren: number;
	totalChildren: number;
	assignees: string[];
	latestActivityAt: string | null;
};

/** Reasons written for a human, not for someone who already knows the code. */
const PENDING_REASON = "等你批准任务修订后才能开始";

/**
 * Why a Task is still unapproved. The distinction matters to the operator: a Task
 * waiting on their approval can be unblocked by one click, while one the project
 * baseline refused cannot be approved at all until the baseline itself changes.
 * Telling both "等你批准" sends the reader chasing a button that does not exist.
 */
function pendingReason(
	state: GovernanceState,
	task: TaskContract,
): {
	reason: string;
	next: TaskWorkStatus["next"];
} {
	// Bounded by the Task's own creation, not by the reset boundary: a Task created before
	// the boundary is still current (reset prunes approvals, it does not remove Tasks), so
	// the refusal that explains why it is unapproved can predate the boundary.
	const created = state.events.find((entry) => {
		if (entry.type !== "task.created") return false;
		const value = entry.payload.value as { taskId?: unknown } | undefined;
		return value?.taskId === task.taskId;
	});
	const since = created?.sequence ?? 0;
	const refusals = state.events.filter(
		(entry) => entry.type === "redline.triggered" && entry.payload.taskId === task.taskId && entry.sequence >= since,
	);
	const codes = new Set(refusals.map((entry) => entry.payload.code));
	if (codes.has("task-outside-baseline"))
		return {
			reason: "超出项目基线范围，改了基线才能开工",
			next: null,
		};
	const decided = Object.values(state.decisions).some(
		(entry) => entry.taskId === task.taskId && entry.revision === task.revision && entry.result === "pending",
	);
	if (!decided)
		return {
			reason: "还没走到审批，需要重新提交任务修订",
			next: { action: "task.revise", taskId: task.taskId },
		};
	return { reason: PENDING_REASON, next: { action: "task.approve", taskId: task.taskId } };
}

function status(state: GovernanceState, task: TaskContract): TaskWorkStatus {
	const children = Object.values(state.tasks).filter((entry) => entry.parentTaskId === task.taskId);
	const acceptedChildren = children.filter((entry) => taskAccepted(state, entry.taskId)).length;
	const delegations = Object.values(state.delegations).filter((entry) => entry.taskId === task.taskId);
	const runs = Object.values(state.runs).filter((entry) => entry.taskId === task.taskId);
	const currentDeliverables = Object.values(state.deliverables).filter(
		(entry) => entry.taskId === task.taskId && entry.revision === task.revision,
	);
	const latest = currentDeliverables.at(-1);
	const verification =
		latest &&
		Object.values(state.verifications)
			.filter((entry) => entry.deliverableId === latest.deliverableId)
			.at(-1);
	const activity = state.events
		.filter(
			(entry) =>
				entry.taskId === task.taskId &&
				["agent.action-observed", "agent.loop-started", "session.task-activated", "run.started"].includes(
					entry.type,
				),
		)
		.at(-1);
	const assignees = [
		...new Set([
			...delegations.map((entry) => entry.executorId),
			...state.events
				.filter(
					(entry) =>
						entry.type === "agent.action-observed" &&
						entry.taskId === task.taskId &&
						entry.runId === null &&
						entry.actor.sessionId,
				)
				.map((entry) => entry.actor.id),
		]),
	];
	const base = {
		taskId: task.taskId,
		authorization: state.approved[task.taskId] === task.revision ? ("approved" as const) : ("pending" as const),
		acceptedChildren,
		totalChildren: children.length,
		assignees,
		latestActivityAt: activity?.recordedAt ?? null,
	};
	// Cancelled is a terminal state and is reported before every other rule. It used to
	// fall through to the authorization check below and surface as "not approved", so a
	// Task the operator had deliberately killed still read as waiting for their approval.
	const cancellation = state.cancelled[task.taskId];
	if (cancellation && cancellation.revision === task.revision)
		return {
			...base,
			work: "CANCELLED",
			reason: "已取消，不再计入当前工作",
			next: null,
			cancelledReason: cancellation.reason,
		};
	if (taskAccepted(state, task.taskId))
		return { ...base, work: "ACCEPTED", reason: "已验收", next: null, cancelledReason: null };
	if (base.authorization === "pending") {
		const pending = pendingReason(state, task);
		return {
			...base,
			work: "NOT_STARTED",
			reason: pending.reason,
			next: pending.next,
			cancelledReason: null,
		};
	}
	const blocked = task.dependencies.filter((entry) => !taskAccepted(state, entry.taskId));
	if (blocked.length)
		return {
			...base,
			work: "BLOCKED",
			reason: `等这些前置任务验收后才能开始：${blocked.map((entry) => entry.taskId).join("、")}`,
			next: null,
			cancelledReason: null,
		};
	if ((task.kind ?? "executable") === "container") {
		if (!children.length)
			return {
				...base,
				work: "BLOCKED",
				reason: "工作包下面还没有拆子任务",
				next: null,
				cancelledReason: null,
			};
		const childStates = children.map((child) => status(state, child).work);
		// A container has no work of its own: it is exactly the state of its children.
		// Two extremes were falling through to READY and were reported as unstarted
		// work forever - all children accepted (done) and all cancelled (abandoned).
		// Neither is something the operator can act on, so neither is READY.
		const live = childStates.filter((entry) => entry !== "CANCELLED");
		if (!live.length)
			return {
				...base,
				work: "CANCELLED",
				reason: "子任务已全部取消，这个工作包不再占用预算",
				next: null,
				cancelledReason: "全部子任务已取消",
			};
		const work = live.every((entry) => entry === "ACCEPTED")
			? "ACCEPTED"
			: live.some((entry) => entry === "IN_PROGRESS" || entry.startsWith("AWAITING"))
				? "IN_PROGRESS"
				: live.some((entry) => entry === "NEEDS_REWORK")
					? "NEEDS_REWORK"
					: live.every((entry) => entry === "BLOCKED")
						? "BLOCKED"
						: "READY";
		return {
			...base,
			work,
			reason:
				work === "ACCEPTED"
					? `子任务已全部验收 ${acceptedChildren}/${children.length}`
					: `子任务已验收 ${acceptedChildren}/${children.length}`,
			next: null,
			cancelledReason: null,
		};
	}
	if (runs.some((run) => ["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"].includes(run.state)))
		return {
			...base,
			work: "IN_PROGRESS",
			reason: "子 Agent 正在执行",
			next: null,
			cancelledReason: null,
		};
	const mainActive = state.events.some(
		(entry) =>
			entry.type === "agent.loop-started" &&
			entry.taskId === task.taskId &&
			!state.events.some(
				(later) =>
					later.sequence > entry.sequence &&
					later.context.sessionId === entry.context.sessionId &&
					later.type === "agent.loop-settled",
			),
	);
	if (mainActive)
		return {
			...base,
			work: "IN_PROGRESS",
			reason: "主 Agent 正在处理",
			next: null,
			cancelledReason: null,
		};
	if (latest) {
		if (verification?.result === "failed")
			return {
				...base,
				work: "NEEDS_REWORK",
				reason: "复核没通过，需要返工",
				next: { action: "task.revise", taskId: task.taskId },
				cancelledReason: null,
			};
		if (verification?.result === "passed")
			return {
				...base,
				work: "AWAITING_ACCEPTANCE",
				reason: "复核已通过，等你验收",
				next: { action: "task.accept", taskId: task.taskId },
				cancelledReason: null,
			};
		return {
			...base,
			work: "AWAITING_VERIFICATION",
			reason: "已交付，等独立复核",
			next: null,
			cancelledReason: null,
		};
	}
	if (
		runs.some((run) => run.state === "SUCCEEDED") ||
		state.events.some(
			(entry) =>
				entry.type === "agent.action-result" &&
				entry.taskId === task.taskId &&
				entry.runId === null &&
				entry.payload.outcome === "ok" &&
				["write", "edit"].includes(String(entry.payload.tool ?? "")),
		)
	)
		return {
			...base,
			work: "AWAITING_DELIVERY",
			reason: "有执行痕迹，但没有登记交付物",
			next: null,
			cancelledReason: null,
		};
	if (runs.some((run) => run.state === "FAILED"))
		return {
			...base,
			work: "NEEDS_REWORK",
			reason: "执行失败，需要重试或修订任务",
			next: { action: "task.revise", taskId: task.taskId },
			cancelledReason: null,
		};
	return {
		...base,
		work: activity ? "READY" : "NOT_STARTED",
		reason: activity ? "已批准，尚未开始执行" : null,
		next: null,
		cancelledReason: null,
	};
}

export function queryTaskWorkStatuses(state: GovernanceState): Record<string, TaskWorkStatus> {
	return Object.fromEntries(Object.values(state.tasks).map((task) => [task.taskId, status(state, task)]));
}
