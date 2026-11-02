// What the running process actually loaded, as opposed to what is on disk.
//
// `gov upgrade` verifies the copy it writes and reports `verified: true`. That
// says the files on disk are the ones the source produced. It says nothing about
// the code the current pi process is executing: a running process keeps the
// modules it imported, and the bridge is loaded once at session start. A project
// can therefore be "upgraded" while every governance tool in the running session
// still calls the old code.
//
// This happened twice in one session, and both times the upgrade report was
// interpreted as "the fix is live":
//
//   - `verified: true`, while the tool that needed fixing still refused.
//   - An upgrade followed by a delegation refused with the same message, because
//     the process had loaded the bridge before the fix existed.
//
// The two facts are recorded separately and compared. Disk is read from the
// installed copy; runtime is captured once, when this module is imported.

import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { installationPath } from "./installation.ts";
import type { GovernanceStore } from "./store.ts";
import type { GovernanceEvent } from "./types.ts";

/** Digest over the installed sources, or null when nothing is installed. */
export function installedDigest(project: string): string | null {
	const root = path.dirname(installationPath(project));
	if (!fs.existsSync(root)) return null;
	const names = fs
		.readdirSync(root)
		.filter((name) => name.endsWith(".ts"))
		.sort();
	if (!names.length) return null;
	const hash = createHash("sha256");
	for (const name of names) {
		hash.update(name);
		hash.update("\0");
		hash.update(fs.readFileSync(path.join(root, name)));
		hash.update("\0");
	}
	return hash.digest("hex");
}

/**
 * Digest of the copy this process is running from.
 *
 * Taken from the directory holding this module rather than from a project path,
 * because the module may be the installed copy or a source checkout and the answer
 * has to describe whichever one is actually executing. Computed once: the value is
 * a fact about load time, and recomputing it after an upgrade would report what is
 * on disk instead of what is in memory, which is the confusion this exists to end.
 */
let loadedDigest: string | null | undefined;

export function loadedRuntimeDigest(): string | null {
	if (loadedDigest !== undefined) return loadedDigest;
	const directory = path.dirname(fileURLToPath(import.meta.url));
	const names = fs
		.readdirSync(directory)
		.filter((name) => name.endsWith(".ts"))
		.sort();
	const hash = createHash("sha256");
	for (const name of names) {
		hash.update(name);
		hash.update("\0");
		try {
			hash.update(fs.readFileSync(path.join(directory, name)));
		} catch {
			// A file listed but unreadable makes the digest unrepresentative, which is
			// the honest answer: this process cannot vouch for what it loaded.
			loadedDigest = null;
			return null;
		}
		hash.update("\0");
	}
	loadedDigest = hash.digest("hex");
	return loadedDigest;
}

export type RuntimeVersionState = "current" | "stale" | "source" | "unknown";

export type RuntimeVersionCheck = {
	state: RuntimeVersionState;
	loaded: string | null;
	installed: string | null;
	/** One sentence an operator can act on, empty when the state is current. */
	detail: string;
};

/**
 * Compare the code in memory with the code on disk.
 *
 * `source` means this process runs a source checkout, so there is nothing to
 * compare against and staleness cannot be claimed either way - which is different
 * from "current" and must not be reported as it.
 */
export function checkRuntimeVersion(project: string): RuntimeVersionCheck {
	const loaded = loadedRuntimeDigest();
	const installed = installedDigest(project);
	if (!loaded || !installed) return { state: "unknown", loaded, installed, detail: "" };
	if (loaded === installed) return { state: "current", loaded, installed, detail: "" };
	// Running from a checkout: the loaded files are not the installed ones by design.
	const root = path.dirname(installationPath(project));
	const runningFrom = path.dirname(fileURLToPath(import.meta.url));
	if (runningFrom !== root)
		return {
			state: "source",
			loaded,
			installed,
			detail: `治理内核正从源码运行（${runningFrom}），不是项目安装副本；升级不会改变本次会话的行为。`,
		};
	return {
		state: "stale",
		loaded,
		installed,
		detail:
			"治理内核在本次会话启动后已被升级。正在运行的进程仍在执行旧代码，重启 Pi 后新版本才会生效。" +
			"`gov upgrade` 报告的 verified 只表示磁盘文件与源码一致，不代表内存已更新。",
	};
}

/**
 * Ledger record of the digest this process loaded, written once per session.
 *
 * Recorded as a fact rather than a verdict: a later reader compares it against
 * what the disk held at the time to tell "the fix was deployed" from "the fix was
 * actually running". Verifying a file and observing that the fix took effect are
 * two different claims, and only the second one matters to a user.
 */
export function recordRuntimeLoad(store: GovernanceStore, sessionId: string): void {
	// The session is carried in the payload, the same way every other observation
	// event carries it, so a reader finds it without knowing this event by name.
	//
	// Keyed on what was *loaded*, not on the session. A resumed session keeps its ID
	// across a Pi restart, so keying on the session alone meant an upgrade recorded once
	// at the old digest was never corrected: the detector reported `stale` forever while
	// the new code was in fact running. That is the opposite of this mechanism's purpose,
	// which is to distinguish "deployed" from "actually running".
	const digest = loadedRuntimeDigest();
	const recorded = store
		.read()
		.events.filter((event) => event.type === "kernel.runtime-loaded" && event.payload.sessionId === sessionId)
		.at(-1);
	if (recorded?.payload.digest === digest) return;
	store.append({
		type: "kernel.runtime-loaded",
		actor: `pi:${sessionId}`,
		taskId: null,
		runId: null,
		delegationId: null,
		sessionId,
		payload: { sessionId, digest, pid: process.pid },
	});
}

export type SessionRuntimeCheck = {
	state: "current" | "stale" | "unknown";
	/** Digest the most recent session recorded when it loaded the kernel. */
	loaded: string | null;
	installed: string | null;
	sessionId: string | null;
	detail: string;
};

/**
 * Compare the running session's kernel with the installed copy.
 *
 * The process-local check above answers "is *this* process current", which is the
 * right question inside the bridge and the wrong one in the CLI: a CLI invocation
 * loads whatever is on disk right now, so it reports `current` even while the pi
 * process that owns the ledger is executing yesterday's code. Reporting that as
 * healthy is worse than reporting nothing, because it is reassuring and wrong.
 *
 * The ledger carries what each session actually loaded, so the comparison a reader
 * needs is between that record and the current install.
 */
export function checkSessionRuntime(project: string, state: { events: GovernanceEvent[] }): SessionRuntimeCheck {
	const installed = installedDigest(project);
	const recorded = state.events.filter((event) => event.type === "kernel.runtime-loaded").at(-1);
	const loaded = typeof recorded?.payload.digest === "string" ? recorded.payload.digest : null;
	const sessionId = typeof recorded?.payload.sessionId === "string" ? recorded.payload.sessionId : null;
	if (!installed || !loaded)
		return {
			state: "unknown",
			loaded,
			installed,
			sessionId,
			detail: loaded
				? ""
				: "账本中没有会话加载治理内核的记录。这通常意味着正在运行的会话使用的是旧版内核，或该会话早于本功能启用。",
		};
	if (loaded === installed) return { state: "current", loaded, installed, sessionId, detail: "" };
	return {
		state: "stale",
		loaded,
		installed,
		sessionId,
		detail:
			"磁盘上的治理内核已比正在运行的会话更新。本次会话仍在执行旧代码，重启 Pi 后新版本才会生效；`gov upgrade` 的 verified 只表示磁盘文件与源码一致。",
	};
}
