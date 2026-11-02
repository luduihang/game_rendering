import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import type { GovernanceKernel } from "./kernel.ts";
import { dataRoot } from "./store.ts";
import type { Workspace, WorkspaceDestroyEvidence, WorkspaceDestroyResult } from "./types.ts";

function git(cwd: string, ...args: string[]): string {
	return execFileSync("git", args, { cwd, encoding: "utf8" }).trim();
}

function gitOptional(cwd: string, ...args: string[]): string | null {
	try {
		return git(cwd, ...args);
	} catch {
		return null;
	}
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
	if (task.kind === "container") throw new Error("Container tasks cannot own a workspace");
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
		destroyedAt: null,
	};
	try {
		kernel.registerWorkspace(workspace, "governance");
	} catch (error) {
		throw new Error(`Worktree exists but governance registration failed; inspect ${target}`, { cause: error });
	}
	return workspace;
}

export function verifyTakeover(workspace: Workspace, kernel: GovernanceKernel): ReturnType<typeof inspectWorkspace> {
	if (workspace.destroyedAt) throw new Error(`Worktree was destroyed at ${workspace.destroyedAt}`);
	const inspection = inspectWorkspace(workspace);
	if (!inspection.exists || inspection.branch !== workspace.branch)
		throw new Error("Worktree missing or branch changed");
	if (workspace.holderRunId) throw new Error("Worktree is still held by a Run");
	const task = kernel.getState().tasks[workspace.taskId];
	if (!task || task.kind === "container" || kernel.getState().approved[workspace.taskId] !== task.revision)
		throw new Error("Task authority is stale");
	return inspection;
}

/** Porcelain status lines are `XY <path>`; keep the path so the record is readable. */
function statusPaths(status: string[]): string[] {
	return status.map((line) => (line.length > 3 ? line.slice(3) : line));
}

/**
 * Facts that must outlive the directory. Captured before anything is removed and
 * archived under the ledger root, which survives Worktree deletion.
 */
export function captureWorkspaceEvidence(
	repo: string,
	workspace: Workspace,
	kernel: GovernanceKernel,
): WorkspaceDestroyEvidence {
	const inspection = inspectWorkspace(workspace);
	const task = kernel.getState().tasks[workspace.taskId];
	const acceptedVerificationId = kernel.getState().accepted[workspace.taskId];
	const head = inspection.exists ? inspection.head : gitOptional(repo, "rev-parse", workspace.branch);
	const unmerged = head
		? (gitOptional(repo, "rev-list", `${workspace.baseCommit}..${workspace.branch}`) ?? "")
				.split("\n")
				.filter(Boolean)
		: [];
	return {
		taskId: workspace.taskId,
		path: workspace.path,
		branch: workspace.branch,
		baseCommit: workspace.baseCommit,
		head,
		unmergedCommits: unmerged,
		dirtyPaths: inspection.exists ? statusPaths(inspection.status) : [],
		archivePath: null,
		archiveSha256: null,
		taskAccepted:
			Boolean(acceptedVerificationId) &&
			task !== undefined &&
			kernel.getState().accepted[workspace.taskId] === acceptedVerificationId,
	};
}

/** Write the evidence bundle next to the ledger and return its path and digest. */
function archiveEvidence(ledgerRoot: string, evidence: WorkspaceDestroyEvidence): WorkspaceDestroyEvidence {
	const dir = path.join(ledgerRoot, "evidence", "workspaces");
	fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
	const stamp = new Date().toISOString().replace(/[:.]/g, "-");
	const file = path.join(dir, `${evidence.taskId}-${stamp}.json`);
	const body = `${JSON.stringify(evidence, null, 2)}\n`;
	fs.writeFileSync(file, body, { mode: 0o600 });
	return {
		...evidence,
		archivePath: path.relative(ledgerRoot, file),
		archiveSha256: createHash("sha256").update(body).digest("hex"),
	};
}

export type WorkspaceDestroyOutcome = {
	workspace: Workspace;
	evidence: WorkspaceDestroyEvidence;
	result: WorkspaceDestroyResult;
};

/**
 * Remove a Worktree only after its evidence is archived and recorded.
 *
 * Order is the whole point: archive, then record the request, then delete. If the
 * process dies mid-way the ledger shows a destroy request with no outcome, which
 * reads as "unknown" instead of a directory that silently vanished.
 *
 * Uncommitted or untracked changes mean the Worktree is retained: deleting it
 * would destroy work that no evidence bundle can reconstruct.
 */
export function destroyWorkspace(
	repo: string,
	workspaceId: string,
	kernel: GovernanceKernel,
	actor: string,
): WorkspaceDestroyOutcome {
	const workspace = kernel.getState().workspaces[workspaceId];
	if (!workspace) throw new Error("Unknown workspace");
	if (workspace.destroyedAt) throw new Error(`Workspace already destroyed at ${workspace.destroyedAt}`);
	if (workspace.holderRunId)
		throw new Error(`Workspace is still held by Run ${workspace.holderRunId}; release it first`);

	const captured = captureWorkspaceEvidence(repo, workspace, kernel);
	// Evidence lives beside the ledger, which outlives the Worktree.
	const evidence = archiveEvidence(kernel.store.root, captured);

	// The archive is on disk and hashed before the ledger records the intent, so a
	// crash between the two leaves an orphan file rather than unrecorded removal.
	kernel.requestWorkspaceDestroy(workspace, evidence, actor);

	const result: WorkspaceDestroyResult = {
		worktreeRemoved: false,
		branchRemoved: false,
		pruned: false,
		retained: false,
		reason: null,
	};

	if (evidence.dirtyPaths.length > 0) {
		result.retained = true;
		result.reason = `Worktree has ${evidence.dirtyPaths.length} uncommitted or untracked path(s); retained`;
	} else {
		try {
			git(repo, "worktree", "remove", workspace.path);
			result.worktreeRemoved = true;
		} catch (error) {
			result.retained = true;
			result.reason = `git worktree remove failed: ${error instanceof Error ? error.message.split("\n")[0] : String(error)}`;
		}
	}

	if (!result.retained) {
		if (evidence.unmergedCommits.length > 0) {
			// The branch holds commits that no other ref reaches. Deleting it would
			// make the delivered commit collectable, so keep the ref and say why.
			result.reason = `Branch retained: ${evidence.unmergedCommits.length} commit(s) not reachable from ${workspace.baseCommit}`;
		} else {
			try {
				git(repo, "branch", "-D", workspace.branch);
				result.branchRemoved = true;
			} catch (error) {
				result.reason = `git branch -D failed: ${error instanceof Error ? error.message.split("\n")[0] : String(error)}`;
			}
		}
		try {
			git(repo, "worktree", "prune");
			result.pruned = true;
		} catch (error) {
			const note = `git worktree prune failed: ${error instanceof Error ? error.message.split("\n")[0] : String(error)}`;
			result.reason = result.reason ? `${result.reason}; ${note}` : note;
		}
	}

	return {
		workspace: kernel.finishWorkspaceDestroy(workspace.workspaceId, evidence, result, actor),
		evidence,
		result,
	};
}
