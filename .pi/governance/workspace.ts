import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import type { GovernanceKernel } from "./kernel.ts";
import { dataRoot } from "./store.ts";
import type { Workspace } from "./types.ts";

function git(cwd: string, ...args: string[]): string {
	return execFileSync("git", args, { cwd, encoding: "utf8" }).trim();
}

export function inspectWorkspace(workspace: Workspace): {
	exists: boolean;
	branch: string | null;
	head: string | null;
	status: string[];
} {
	if (!fs.existsSync(workspace.path)) return { exists: false, branch: null, head: null, status: [] };
	return {
		exists: true,
		branch: git(workspace.path, "branch", "--show-current"),
		head: git(workspace.path, "rev-parse", "HEAD"),
		status: git(workspace.path, "status", "--porcelain=v1", "--untracked-files=all").split("\n").filter(Boolean),
	};
}

export function createWorkspace(repo: string, taskId: string, kernel: GovernanceKernel): Workspace {
	const task = kernel.getState().tasks[taskId];
	if (!task) throw new Error("Unknown task");
	if (kernel.getState().approved[taskId] !== task.revision) throw new Error("Task is not approved");
	if (!/^[A-Za-z0-9_-]+$/.test(taskId)) throw new Error("Unsafe task ID for Worktree branch");
	const existing = Object.values(kernel.getState().workspaces).find((entry) => entry.taskId === taskId);
	if (existing) return existing;
	const root = dataRoot(repo);
	const projectKey = createHash("sha256").update(root).digest("hex").slice(0, 12);
	const home = path.resolve(repo, "..", `.pi-governance-worktrees-${projectKey}`);
	const target = path.join(home, taskId);
	const branch = `governance/${taskId}`;
	if (fs.existsSync(target)) throw new Error(`Existing unmanaged Worktree path: ${target}`);
	const baseCommit = git(repo, "rev-parse", "HEAD");
	fs.mkdirSync(home, { recursive: true });
	git(repo, "worktree", "add", "-b", branch, target, baseCommit);
	const workspace: Workspace = {
		workspaceId: `W-${taskId}`,
		taskId,
		path: target,
		branch,
		baseCommit,
		holderRunId: null,
		leaseUntil: null,
	};
	try {
		kernel.registerWorkspace(workspace, "governance");
	} catch (error) {
		throw new Error(`Worktree exists but governance registration failed; inspect ${target}`, { cause: error });
	}
	return workspace;
}

export function verifyTakeover(workspace: Workspace, kernel: GovernanceKernel): ReturnType<typeof inspectWorkspace> {
	const inspection = inspectWorkspace(workspace);
	if (!inspection.exists || inspection.branch !== workspace.branch)
		throw new Error("Worktree missing or branch changed");
	if (workspace.holderRunId) throw new Error("Worktree is still held by a Run");
	const task = kernel.getState().tasks[workspace.taskId];
	if (!task || kernel.getState().approved[workspace.taskId] !== task.revision)
		throw new Error("Task authority is stale");
	return inspection;
}
