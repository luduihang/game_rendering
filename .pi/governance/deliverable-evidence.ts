import { execFileSync } from "node:child_process";
import type { DeliverableEvidence, DeliverableFileChange } from "./types.ts";

function git(repo: string, ...args: string[]): string {
	return execFileSync("git", ["-C", repo, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
}

function gitStatus(repo: string, ...args: string[]): { ok: boolean; stdout: string } {
	try {
		return { ok: true, stdout: git(repo, ...args) };
	} catch {
		return { ok: false, stdout: "" };
	}
}

const STATUS_LETTERS = new Set(["A", "M", "D", "R", "T"]);

function parseNumstat(output: string): Map<string, { additions: number; deletions: number }> {
	const counts = new Map<string, { additions: number; deletions: number }>();
	for (const line of output.split("\n").filter(Boolean)) {
		const [added, removed, ...rest] = line.split("\t");
		const file = rest.join("\t");
		if (!file) continue;
		// Binary files report "-" instead of a count; record zero rather than
		// inventing a number.
		counts.set(file, {
			additions: added === "-" ? 0 : Number(added),
			deletions: removed === "-" ? 0 : Number(removed),
		});
	}
	return counts;
}

/**
 * ROLE-7 and ROLE-9: derive the delivery facts from Git instead of trusting the
 * submitter.
 *
 * The submitter names a commit. Everything returned here is read back from the
 * repository, so a delivery cannot claim a commit that does not exist, a commit
 * that changes nothing, or a set of files the diff does not contain.
 *
 * `baseCommit` is the Worktree base when the Run had one. Without it the only
 * verifiable unit is the commit itself, so its parent becomes the base; a root
 * commit has no parent and cannot be measured, which is a rejection rather than
 * a guessed diff.
 */
export function verifyDeliverableCommit(repo: string, commit: string, baseCommit: string | null): DeliverableEvidence {
	const type = gitStatus(repo, "cat-file", "-t", commit);
	if (!type.ok || type.stdout !== "commit")
		throw new Error(`Deliverable commit is not a commit object in this repository: ${commit}`);

	// Resolve to a literal hash so the record does not depend on `^` notation.
	const base = baseCommit ?? gitStatus(repo, "rev-parse", `${commit}^`).stdout;
	const baseType = base ? gitStatus(repo, "cat-file", "-t", base) : { ok: false, stdout: "" };
	if (!base || !baseType.ok || baseType.stdout !== "commit")
		throw new Error(
			baseCommit
				? `Deliverable base commit is unknown: ${baseCommit}`
				: `Deliverable commit has no parent to measure against: ${commit}`,
		);

	if (!gitStatus(repo, "merge-base", "--is-ancestor", base, commit).ok)
		throw new Error(`Deliverable commit ${commit} does not descend from ${base}`);

	// --no-renames keeps a rename as a delete plus an add, so every entry has one
	// path and one unambiguous status letter.
	const nameStatus = git(repo, "diff", "--no-renames", "--name-status", `${base}..${commit}`);
	const counts = parseNumstat(git(repo, "diff", "--no-renames", "--numstat", `${base}..${commit}`));
	const files: DeliverableFileChange[] = [];
	for (const line of nameStatus.split("\n").filter(Boolean)) {
		const [letter, ...rest] = line.split("\t");
		const file = rest.join("\t");
		if (!file || !STATUS_LETTERS.has(letter)) continue;
		const count = counts.get(file) ?? { additions: 0, deletions: 0 };
		files.push({
			path: file,
			status: letter as DeliverableFileChange["status"],
			additions: count.additions,
			deletions: count.deletions,
		});
	}

	if (files.length === 0) throw new Error(`Deliverable commit ${commit} introduces no changes relative to ${base}`);

	return {
		commitType: type.stdout,
		commitSubject: gitStatus(repo, "log", "-1", "--format=%s", commit).stdout || null,
		baseCommit: base,
		files,
		additions: files.reduce((total, file) => total + file.additions, 0),
		deletions: files.reduce((total, file) => total + file.deletions, 0),
	};
}
