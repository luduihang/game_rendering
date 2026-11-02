import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import type { TestLogEvidence, TestReport } from "./types.ts";

/**
 * ROLE-8: make test results checkable instead of quoted.
 *
 * A submitter can always type "237 passed". What it cannot do is produce a log
 * committed in the delivery that a third party can hash and read. So a report
 * keeps the claim (`passed`/`failed`) and may name the artifact (`logPath`).
 *
 * `logPath` is optional, and that is deliberate: requiring it would tax every
 * small delivery, and a taxed check gets switched off. What is not optional is
 * honesty about which case applies - a report with no log is recorded as
 * unverified, never as verified, and the views say so.
 */

function gitShow(repo: string, commit: string, file: string): Buffer | null {
	try {
		return execFileSync("git", ["-C", repo, "show", `${commit}:${file}`], {
			stdio: ["ignore", "pipe", "pipe"],
			maxBuffer: 64 * 1024 * 1024,
		});
	} catch {
		return null;
	}
}

/**
 * Extract the largest `passed`/`failed` counts named in a log.
 *
 * Largest rather than last: a run often prints per-file progress before the
 * total, and the total is the number that matters. When the log names no count,
 * both stay null rather than defaulting to zero - "no number found" and "zero
 * tests" are different facts.
 */
export function countsFromLog(text: string): { passed: number | null; failed: number | null } {
	let passed: number | null = null;
	let failed: number | null = null;
	for (const match of text.matchAll(/(\d+)\s+(passed|failed)\b/gi)) {
		const value = Number(match[1]);
		if (match[2].toLowerCase() === "passed") passed = passed === null ? value : Math.max(passed, value);
		else failed = failed === null ? value : Math.max(failed, value);
	}
	return { passed, failed };
}

/**
 * Check one report against the delivery commit.
 *
 * Returns null for a report that named no log: the absence is the finding, so
 * the caller stores null instead of an evidence object that would imply a check
 * happened.
 */
export function verifyTestLog(repo: string, commit: string, report: TestReport): TestLogEvidence | null {
	if (typeof report.command !== "string" || !report.command.trim()) throw new Error("Test report needs a command");
	if (!Number.isSafeInteger(report.passed) || report.passed < 0)
		throw new Error(`Test report has an invalid passed count: ${report.command}`);
	if (!Number.isSafeInteger(report.failed) || report.failed < 0)
		throw new Error(`Test report has an invalid failed count: ${report.command}`);
	if (report.logPath === undefined || report.logPath === null || report.logPath === "") return null;
	if (typeof report.logPath !== "string" || report.logPath.startsWith("/") || report.logPath.split("/").includes(".."))
		throw new Error(`Test log path must stay inside the repository: ${String(report.logPath)}`);

	// Resolved inside the delivery commit, not the working tree: a log that was
	// never committed dies with the Worktree it was written in.
	const bytes = gitShow(repo, commit, report.logPath);
	if (!bytes) throw new Error(`Test log is not in commit ${commit.slice(0, 12)}: ${report.logPath}`);
	if (bytes.length === 0) throw new Error(`Test log is empty: ${report.logPath}`);

	return {
		path: report.logPath,
		bytes: bytes.length,
		sha256: createHash("sha256").update(bytes).digest("hex"),
		observed: countsFromLog(bytes.toString("utf8")),
	};
}

/** Reject the old free-text shape with a message that names the replacement. */
export function assertStructuredTests(entries: unknown): asserts entries is TestReport[] {
	if (!Array.isArray(entries) || entries.length === 0) throw new Error("Delivery requires at least one test report");
	for (const entry of entries) {
		if (typeof entry === "string")
			throw new Error(
				`Test results must be objects like { command, passed, failed, logPath }, not the string ${JSON.stringify(entry)}. A string cannot be checked against the delivery commit.`,
			);
		if (!entry || typeof entry !== "object" || Array.isArray(entry)) throw new Error("Invalid test report");
	}
}
