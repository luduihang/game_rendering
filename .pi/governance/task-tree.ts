import type { GovernanceState } from "./types.ts";

export type TaskTreeNode = {
	taskId: string;
	revision: number;
	kind: "container" | "executable";
	parentTaskId: string | null;
	goal: string;
	approved: boolean;
	accepted: boolean;
	/** True when the cancellation record matches this node's revision. */
	cancelled: boolean;
	dependencies: string[];
	children: TaskTreeNode[];
};

export function taskAccepted(state: GovernanceState, taskId: string, visiting = new Set<string>()): boolean {
	const task = state.tasks[taskId];
	if (!task || visiting.has(taskId)) return false;
	if ((task.kind ?? "executable") === "executable") return Boolean(state.accepted[taskId]);
	if (state.approved[taskId] !== task.revision) return false;
	const children = Object.values(state.tasks).filter((candidate) => candidate.parentTaskId === taskId);
	if (!children.length) return false;
	visiting.add(taskId);
	const result =
		task.dependencies.every((dependency) => taskAccepted(state, dependency.taskId, visiting)) &&
		children.every((child) => taskAccepted(state, child.taskId, visiting));
	visiting.delete(taskId);
	return result;
}

export function queryTaskTree(state: GovernanceState): TaskTreeNode[] {
	const nodes = new Map<string, TaskTreeNode>();
	for (const task of Object.values(state.tasks).sort((left, right) => left.taskId.localeCompare(right.taskId))) {
		nodes.set(task.taskId, {
			taskId: task.taskId,
			revision: task.revision,
			kind: task.kind ?? "executable",
			parentTaskId: task.parentTaskId ?? null,
			goal: task.goal,
			approved: state.approved[task.taskId] === task.revision,
			accepted: taskAccepted(state, task.taskId),
			cancelled: state.cancelled[task.taskId]?.revision === task.revision,
			dependencies: task.dependencies.map((dependency) => dependency.taskId),
			children: [],
		});
	}
	const roots: TaskTreeNode[] = [];
	for (const node of nodes.values()) {
		const parent = node.parentTaskId ? nodes.get(node.parentTaskId) : null;
		if (parent) parent.children.push(node);
		else roots.push(node);
	}
	return roots;
}
