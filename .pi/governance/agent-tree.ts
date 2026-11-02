import type { GovernanceEvent, GovernanceState, RunState } from "./types.ts";

export type AgentTreeNode = {
	id: string;
	parentId: string | null;
	kind: "session" | "delegation" | "run" | "attempt";
	label: string;
	status: string;
	taskId: string | null;
	delegationId: string | null;
	runId: string | null;
	agentDefinitionId: string | null;
	agentInstanceId: string | null;
	nativeRunId: string | null;
	objective: string | null;
	startedAt: string | null;
	finishedAt: string | null;
	provenance: "session-observed" | "native-linked" | "ledger-only" | "blocked";
	sourceSequences: number[];
	actionCount: number;
	recentActions: { sequence: number; tool: string; resource: string | null; outcome: string }[];
	children: AgentTreeNode[];
};

export type AgentTree = {
	ledgerSequence: number;
	counts: {
		authorized: number;
		nativeLinked: number;
		activeRuns: number;
		blockedAttempts: number;
		ledgerOnlyRuns: number;
	};
	roots: AgentTreeNode[];
};

function payloadObject(event: GovernanceEvent): Record<string, unknown> {
	const value = event.payload.value;
	return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function field(value: unknown): string | null {
	return typeof value === "string" && value ? value : null;
}

/** Build a historical tree from ledger events. Native state is never queried here. */
export function queryAgentTree(state: GovernanceState): AgentTree {
	const currentEvents = state.events.filter((event) => event.sequence > state.archiveBoundary);
	const nodes = new Map<string, AgentTreeNode>();
	const sessions = new Set<string>();
	const attemptsByToolCall = new Map<string, string>();
	const pendingAttemptParents = new Map<string, string>();
	const instanceEvents = new Map<string, GovernanceEvent>();
	const runEvents = new Map<string, GovernanceEvent[]>();
	const actionEvents = currentEvents.filter((event) => event.eventType === "governance.agent.action-observed");
	const delegations = currentEvents.filter((event) => event.eventType === "governance.delegation.authorized");
	const unmanaged = currentEvents.filter((event) => event.eventType === "governance.delegation.unmanaged");

	for (const event of currentEvents) {
		if (event.eventType === "governance.agent.instance-observed" && event.context.runId)
			instanceEvents.set(event.context.runId, event);
		if (event.context.runId && event.eventType.startsWith("governance.run.")) {
			const related = runEvents.get(event.context.runId) ?? [];
			related.push(event);
			runEvents.set(event.context.runId, related);
		}
		if (event.eventType === "governance.agent.session-observed") {
			const sessionId = field(event.payload.sessionId);
			if (sessionId) sessions.add(sessionId);
		}
	}
	for (const event of [...delegations, ...unmanaged]) {
		if (event.actor.sessionId) sessions.add(event.actor.sessionId);
		if (event.context.sessionId) sessions.add(event.context.sessionId);
	}
	for (const event of actionEvents) if (event.actor.sessionId) sessions.add(event.actor.sessionId);
	for (const sessionId of sessions) {
		const source = currentEvents.filter(
			(event) => event.eventType === "governance.agent.session-observed" && event.payload.sessionId === sessionId,
		);
		const ended = currentEvents.filter(
			(event) => event.eventType === "governance.agent.session-ended" && event.payload.sessionId === sessionId,
		);
		const actions = actionEvents.filter((event) => event.actor.sessionId === sessionId);
		const unlinkedParent =
			source.at(-1)?.payload.parentSessionFile !== null && source.at(-1)?.payload.parentSessionFile !== undefined;
		const outcomes = new Map<unknown, unknown>();
		for (const event of currentEvents.filter(
			(entry) => entry.eventType === "governance.agent.action-result" && entry.actor.sessionId === sessionId,
		)) {
			const callId = event.payload.toolCallId;
			if (event.payload.outcome === "blocked" || outcomes.get(callId) !== "blocked")
				outcomes.set(callId, event.payload.outcome);
		}
		nodes.set(`session:${sessionId}`, {
			id: `session:${sessionId}`,
			parentId: null,
			kind: "session",
			label: `${unlinkedParent ? "身份待核对" : "主 Agent"} · ${sessionId}`,
			status: ended.length ? "已结束" : unlinkedParent ? "待绑定" : "已观察",
			taskId: null,
			delegationId: null,
			runId: null,
			agentDefinitionId: unlinkedParent ? null : "coordinator",
			agentInstanceId: `pi-session:${sessionId}`,
			nativeRunId: null,
			objective: null,
			startedAt: source[0]?.recordedAt ?? null,
			finishedAt: ended.at(-1)?.recordedAt ?? null,
			provenance: source.length ? "session-observed" : "ledger-only",
			sourceSequences: [...source, ...ended].map((event) => event.sequence).sort((a, b) => a - b),
			actionCount: actions.length,
			recentActions: actions.slice(-5).map((event) => ({
				sequence: event.sequence,
				tool: field(event.payload.tool) ?? "unknown",
				resource: field(event.payload.resource),
				outcome: String(outcomes.get(event.payload.toolCallId) ?? "attempted"),
			})),
			children: [],
		});
	}

	for (const event of delegations) {
		const value = payloadObject(event);
		const delegationId = field(value.delegationId) ?? event.context.delegationId;
		if (!delegationId) continue;
		const parentRunId = field(value.parentRunId);
		const sessionId = event.actor.sessionId ?? event.context.sessionId;
		const agent = field(value.executorId);
		nodes.set(`delegation:${delegationId}`, {
			id: `delegation:${delegationId}`,
			parentId: parentRunId ? `run:${parentRunId}` : sessionId ? `session:${sessionId}` : null,
			kind: "delegation",
			label: agent ?? "未知 Agent",
			status: "已授权",
			taskId: event.context.taskId,
			delegationId,
			runId: null,
			agentDefinitionId: agent,
			agentInstanceId: null,
			nativeRunId: null,
			objective: field(value.objective),
			startedAt: event.recordedAt,
			finishedAt: null,
			provenance: "ledger-only",
			sourceSequences: [event.sequence],
			actionCount: 0,
			recentActions: [],
			children: [],
		});
	}

	for (const run of Object.values(state.runs)) {
		const related = runEvents.get(run.runId) ?? [];
		const instance = instanceEvents.get(run.runId);
		const observed = instance ? payloadObject(instance) : {};
		const first = related.find((event) => event.type === "run.started");
		const last = [...related]
			.reverse()
			.find((event) => ["run.finished", "run.failed", "run.cancelled"].includes(event.type));
		const nativeRunId = field(observed.nativeRunId) ?? run.nativeRunId;
		nodes.set(`run:${run.runId}`, {
			id: `run:${run.runId}`,
			parentId: `delegation:${run.delegationId}`,
			kind: "run",
			label: `${run.executorId} · ${run.runId}`,
			status: run.state,
			taskId: run.taskId,
			delegationId: run.delegationId,
			runId: run.runId,
			agentDefinitionId: run.executorId,
			agentInstanceId: field(observed.agentInstanceId) ?? (nativeRunId ? `pi-run:${nativeRunId}` : null),
			nativeRunId,
			objective: null,
			startedAt: first?.recordedAt ?? null,
			finishedAt: last?.recordedAt ?? null,
			provenance: nativeRunId ? "native-linked" : "ledger-only",
			sourceSequences: [...related.map((event) => event.sequence), ...(instance ? [instance.sequence] : [])].sort(
				(a, b) => a - b,
			),
			actionCount: 0,
			recentActions: [],
			children: [],
		});
	}
	for (const event of currentEvents) {
		if (event.eventType !== "governance.agent.session-observed") continue;
		const sessionId = field(event.payload.sessionId);
		const sessionFile = field(event.payload.sessionFile);
		if (!sessionId || !sessionFile) continue;
		const childRun = Object.values(state.runs).find((run) => run.sessionRef === sessionFile);
		const sessionNode = nodes.get(`session:${sessionId}`);
		if (childRun && sessionNode) {
			sessionNode.parentId = `run:${childRun.runId}`;
			sessionNode.label = `子 Agent 会话 · ${sessionId}`;
			sessionNode.runId = childRun.runId;
			sessionNode.taskId = childRun.taskId;
			sessionNode.agentDefinitionId = childRun.executorId;
		}
	}

	for (const event of unmanaged) {
		const toolCallId = field(event.payload.toolCallId);
		const parentToolCallId = field(event.payload.parentToolCallId);
		const sessionId = event.actor.sessionId ?? event.context.sessionId;
		const id = `attempt:${event.eventId}`;
		if (toolCallId) attemptsByToolCall.set(toolCallId, id);
		if (parentToolCallId) pendingAttemptParents.set(id, parentToolCallId);
		nodes.set(id, {
			id,
			parentId: sessionId ? `session:${sessionId}` : null,
			kind: "attempt",
			label: field(event.payload.agent) ?? "未指定 Agent",
			status: "已拦截",
			taskId: event.context.taskId,
			delegationId: null,
			runId: null,
			agentDefinitionId: field(event.payload.agent),
			agentInstanceId: null,
			nativeRunId: null,
			objective: field(event.payload.objective),
			startedAt: event.recordedAt,
			finishedAt: event.recordedAt,
			provenance: "blocked",
			sourceSequences: [event.sequence],
			actionCount: 0,
			recentActions: [],
			children: [],
		});
	}
	for (const [id, parentToolCallId] of pendingAttemptParents) {
		const parent = attemptsByToolCall.get(parentToolCallId);
		if (parent && parent !== id) nodes.get(id)!.parentId = parent;
	}
	if ([...nodes.values()].some((node) => node.kind !== "session" && (!node.parentId || !nodes.has(node.parentId)))) {
		nodes.set("unattributed", {
			id: "unattributed",
			parentId: null,
			kind: "session",
			label: "未关联到 Agent 会话",
			status: "来源待核对",
			taskId: null,
			delegationId: null,
			runId: null,
			agentDefinitionId: null,
			agentInstanceId: null,
			nativeRunId: null,
			objective: null,
			startedAt: null,
			finishedAt: null,
			provenance: "ledger-only",
			sourceSequences: [],
			actionCount: 0,
			recentActions: [],
			children: [],
		});
		for (const node of nodes.values())
			if ((!node.parentId || !nodes.has(node.parentId)) && node.id !== "unattributed" && node.kind !== "session")
				node.parentId = "unattributed";
	}

	const roots: AgentTreeNode[] = [];
	for (const node of nodes.values()) {
		const parent = node.parentId ? nodes.get(node.parentId) : null;
		if (parent) parent.children.push(node);
		else roots.push(node);
	}
	const runNodes = [...nodes.values()].filter((node) => node.kind === "run");
	const activeStates: RunState[] = ["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"];
	return {
		ledgerSequence: state.events.at(-1)?.sequence ?? 0,
		counts: {
			authorized: delegations.length,
			nativeLinked: runNodes.filter((node) => node.nativeRunId !== null).length,
			activeRuns: runNodes.filter((node) => activeStates.includes(node.status as RunState)).length,
			blockedAttempts: unmanaged.length,
			ledgerOnlyRuns: runNodes.filter((node) => node.nativeRunId === null).length,
		},
		roots,
	};
}
