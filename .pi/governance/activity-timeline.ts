import type { GovernanceEvent, GovernanceState } from "./types.ts";

export type ActivityItem = {
	id: string;
	sequence: number;
	time: string;
	type: string;
	actor: string;
	actorRole: "main" | "child" | "system" | "unknown";
	sessionId: string | null;
	taskId: string | null;
	runId: string | null;
	delegationId: string | null;
	summary: string;
	outcome: "observed" | "ok" | "error" | "blocked" | "unknown";
	observationGap: string | null;
	sourceSequences: number[];
};

export type ActivityPage = { items: ActivityItem[]; total: number; hasMore: boolean; beforeSequence: number | null };

export type MainAgentStatus = {
	sessionId: string;
	agentInstanceId: string | null;
	taskId: string | null;
	startedAt: string;
	endedAt: string | null;
	state: "working" | "idle" | "ended";
	lastActivityAt: string;
};

const visible = new Set([
	"agent.session-observed",
	"agent.session-ended",
	"agent.request-observed",
	"agent.loop-started",
	"agent.loop-settled",
	"agent.action-observed",
	"agent.action-result",
	"session.task-activated",
	"task.created",
	"task.revised",
	"task.approved",
	"task.auto-approved",
	"delegation.requested",
	"delegation.authorized",
	"delegation.rejected",
	"delegation.unmanaged",
	"run.created",
	"run.started",
	"run.finished",
	"run.failed",
	"run.cancelled",
	"run.terminal-unverified",
	"run.session-bound",
	"deliverable.submitted",
	"verification.recorded",
	"task.accepted",
]);

function role(sessionRoles: Map<string, ActivityItem["actorRole"]>, event: GovernanceEvent): ActivityItem["actorRole"] {
	if (event.actor.kind === "system" || event.actor.kind === "human" || event.actor.kind === "plugin") return "system";
	const sessionId = event.context.sessionId ?? event.actor.sessionId;
	return sessionId ? (sessionRoles.get(sessionId) ?? "unknown") : "unknown";
}

function summary(event: GovernanceEvent): string {
	const type = event.type;
	if (type === "agent.action-observed") {
		const tool = typeof event.payload.tool === "string" ? event.payload.tool : "tool";
		const resource = typeof event.payload.resource === "string" ? ` · ${event.payload.resource}` : "";
		return `调用 ${tool}${resource}`;
	}
	if (type === "agent.action-result") return `工具 ${String(event.payload.tool ?? "未知")} 返回`;
	if (type === "task.created") return `创建 Task ${event.taskId ?? "未知"}`;
	if (type === "task.revised") return `修订 Task ${event.taskId ?? "未知"}`;
	if (type === "delegation.authorized") return `委派 ${event.taskId ?? "未知 Task"}`;
	if (type === "deliverable.submitted") return `提交交付物 ${event.subject.id}`;
	if (type === "verification.recorded") return `记录独立验证 ${event.subject.id}`;
	if (type === "task.accepted") return `验收 Task ${event.taskId ?? "未知"}`;
	if (type === "run.terminal-unverified")
		return `子 Agent 返回结束通知，但 Run ${event.runId ?? "未知"} 缺少原生终态证明`;
	if (type === "session.task-activated") return `切换到 Task ${event.taskId ?? "未知"}`;
	return type.replaceAll("-", " ").replaceAll(".", " · ");
}

function includesTask(state: GovernanceState, candidate: string | null, selected: string): boolean {
	let current = candidate;
	const visited = new Set<string>();
	while (current && !visited.has(current)) {
		if (current === selected) return true;
		visited.add(current);
		current = state.tasks[current]?.parentTaskId ?? null;
	}
	return false;
}

/** Read-only activity projection. A missing tool result stays an observation, never a success. */
export function queryActivityTimeline(
	state: GovernanceState,
	filter: {
		taskId?: string;
		actor?: string;
		type?: string;
		beforeSequence?: number;
		limit?: number;
		/**
		 * `current` (default) shows work since the last Start Fresh; `archived` shows
		 * everything an archive covers. The ledger holds both; only the view differs.
		 */
		scope?: "current" | "archived";
	},
): ActivityPage {
	const scopeFilter = (event: GovernanceEvent): boolean => {
		if (filter.scope === "archived") return state.archiveBoundary === 0 || event.sequence <= state.archiveBoundary;
		return event.sequence > state.archiveBoundary;
	};
	const results = new Map<string, GovernanceEvent>();
	const calls = new Set<string>();
	const sessionRoles = new Map<string, ActivityItem["actorRole"]>();
	const childBindings = new Map<
		string,
		{ taskId: string | null; runId: string | null; delegationId: string | null }
	>();
	for (const event of state.events) {
		if (!scopeFilter(event)) continue;
		const sessionId = event.context.sessionId ?? event.actor.sessionId;
		if (
			event.type === "agent.session-observed" &&
			typeof event.payload.sessionId === "string" &&
			sessionRoles.get(event.payload.sessionId) !== "child"
		)
			sessionRoles.set(event.payload.sessionId, event.payload.parentSessionFile === null ? "main" : "unknown");
		if (event.type === "run.session-bound" && typeof event.payload.sessionId === "string") {
			sessionRoles.set(event.payload.sessionId, "child");
			childBindings.set(event.payload.sessionId, {
				taskId: event.taskId,
				runId: event.runId,
				delegationId: event.delegationId,
			});
		}
		if (event.type === "agent.action-observed" && sessionId)
			calls.add(`${sessionId}:${String(event.payload.toolCallId ?? "")}`);
		if (event.type !== "agent.action-result" || !event.context.sessionId) continue;
		const key = `${event.context.sessionId}:${String(event.payload.toolCallId ?? "")}`;
		if (event.payload.outcome === "blocked" || results.get(key)?.payload.outcome !== "blocked")
			results.set(key, event);
	}
	const rows: ActivityItem[] = [];
	for (const event of state.events) {
		if (!visible.has(event.type) || event.type === "agent.action-result" || !scopeFilter(event)) continue;
		const sessionId = event.context.sessionId ?? event.actor.sessionId;
		const result =
			event.type === "agent.action-observed" && sessionId
				? results.get(`${sessionId}:${String(event.payload.toolCallId ?? "")}`)
				: undefined;
		const rawOutcome = result?.payload.outcome;
		const outcome =
			rawOutcome === "ok" || rawOutcome === "error" || rawOutcome === "blocked"
				? rawOutcome
				: [
							"task.accepted",
							"deliverable.submitted",
							"verification.recorded",
							"task.approved",
							"task.auto-approved",
						].includes(event.type)
					? "ok"
					: ["run.failed", "delegation.rejected"].includes(event.type)
						? "error"
						: event.type === "run.terminal-unverified"
							? "unknown"
							: event.type === "agent.action-observed"
								? "observed"
								: "observed";
		const actorRole = role(sessionRoles, event);
		const binding = sessionId ? childBindings.get(sessionId) : undefined;
		rows.push({
			id:
				event.type === "agent.action-observed" && typeof event.payload.actionId === "string"
					? event.payload.actionId
					: event.eventId,
			sequence: event.sequence,
			time: event.recordedAt,
			type: event.type,
			actor: event.actor.id,
			actorRole,
			sessionId: sessionId ?? null,
			taskId: event.taskId ?? binding?.taskId ?? null,
			runId: event.runId ?? binding?.runId ?? null,
			delegationId: event.delegationId ?? binding?.delegationId ?? null,
			summary: summary(event),
			outcome,
			observationGap:
				event.type === "agent.action-observed" && !result
					? "tool_result_missing"
					: actorRole === "unknown" && sessionId
						? "session_role_unverified"
						: null,
			sourceSequences: result ? [event.sequence, result.sequence] : [event.sequence],
		});
	}
	for (const event of state.events) {
		if (event.type !== "agent.action-result" || !scopeFilter(event)) continue;
		if (calls.has(`${event.context.sessionId}:${String(event.payload.toolCallId ?? "")}`)) continue;
		const binding = event.context.sessionId ? childBindings.get(event.context.sessionId) : undefined;
		rows.push({
			id: event.eventId,
			sequence: event.sequence,
			time: event.recordedAt,
			type: event.type,
			actor: event.actor.id,
			actorRole: role(sessionRoles, event),
			sessionId: event.context.sessionId,
			taskId: event.taskId ?? binding?.taskId ?? null,
			runId: event.runId ?? binding?.runId ?? null,
			delegationId: event.delegationId ?? binding?.delegationId ?? null,
			summary: summary(event),
			outcome: "unknown",
			observationGap: "tool_call_missing",
			sourceSequences: [event.sequence],
		});
	}
	const filtered = rows
		.filter(
			(entry) =>
				(filter.beforeSequence === undefined || entry.sequence < filter.beforeSequence) &&
				(!filter.taskId || includesTask(state, entry.taskId, filter.taskId)) &&
				(!filter.actor || entry.actor === filter.actor) &&
				(!filter.type || entry.type === filter.type),
		)
		.sort((a, b) => b.sequence - a.sequence);
	const limit = Math.min(Math.max(filter.limit ?? 100, 1), Math.max(state.events.length, 1));
	const items = filtered.slice(0, limit);
	return {
		items,
		total: filtered.length,
		hasMore: filtered.length > limit,
		beforeSequence: items.length && filtered.length > limit ? items.at(-1)!.sequence : null,
	};
}

/** Main identity and work are derived from Pi session events; a child Run is never projected as Main. */
export function queryMainAgentStatuses(state: GovernanceState): MainAgentStatus[] {
	const sessions = new Map<string, MainAgentStatus>();
	const children = new Set<string>();
	for (const event of state.events) {
		if (event.sequence <= state.archiveBoundary) continue;
		if (event.type === "run.session-bound" && typeof event.payload.sessionId === "string")
			children.add(event.payload.sessionId);
		if (
			event.type === "agent.session-observed" &&
			event.payload.parentSessionFile === null &&
			typeof event.payload.sessionId === "string"
		) {
			const sessionId = event.payload.sessionId;
			sessions.set(sessionId, {
				sessionId,
				agentInstanceId: typeof event.payload.agentInstanceId === "string" ? event.payload.agentInstanceId : null,
				taskId: null,
				startedAt: event.recordedAt,
				endedAt: null,
				state: "idle",
				lastActivityAt: event.recordedAt,
			});
			continue;
		}
		const sessionId = event.context.sessionId ?? event.actor.sessionId;
		if (!sessionId) continue;
		const session = sessions.get(sessionId);
		if (!session) continue;
		if (event.type === "session.task-activated") session.taskId = event.taskId;
		if (event.type === "agent.loop-started") session.state = "working";
		if (event.type === "agent.loop-settled") session.state = "idle";
		if (event.type === "agent.session-ended") {
			session.state = "ended";
			session.endedAt = event.recordedAt;
		}
		session.lastActivityAt = event.recordedAt;
	}
	return [...sessions.values()]
		.filter((session) => !children.has(session.sessionId))
		.sort((a, b) => b.lastActivityAt.localeCompare(a.lastActivityAt));
}
