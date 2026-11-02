import { randomUUID } from "node:crypto";
import * as fs from "node:fs";
import type { GovernanceEvent, GovernanceState, Run } from "./types.ts";

/**
 * Whether a Run's native process was ever confirmed to exist, and if so, which process it is.
 *
 * The problem this exists for: a Run that crashed between starting its child and recording
 * the child's identity leaves the ledger saying `RUNNING` with nothing to look up. Guessing
 * is expensive in both directions - assume it died and a live child's slot is double-booked,
 * assume it lives and the slot is gone forever.
 *
 * The native side generates its own Run ID and offers no way to supply one, so the identity
 * cannot be written before the process exists. Instead the intent is recorded first and the
 * binding second, and the gap between them is a state of its own rather than an assumption:
 * `LAUNCH_UNBOUND` means "we asked for a child and never learned what became of it".
 */
export type ExecutionAttempt = {
	executionAttemptId: string;
	runId: string;
	requestedAt: number;
	/** Set only once the native side reported a Run ID; never guessed from timing. */
	bound: {
		nativeRunId: string;
		at: number;
		pid: number | null;
		pidNamespaceScope: string | null;
		/** `/proc/<pid>/stat` field 22 at bind time, which is what defeats PID reuse later. */
		processStartIdentity: string | null;
		hostBootId: string | null;
	} | null;
};

export type ExecutionAttemptState =
	| "NOT_STARTED"
	/** Intent recorded, no native identity. Possibly nothing started, possibly a child is running. */
	| "LAUNCH_UNBOUND"
	| "BOUND";

/** Derive the attempts a Run has made, oldest first. */
export function executionAttempts(state: GovernanceState, runId: string): ExecutionAttempt[] {
	const attempts = new Map<string, ExecutionAttempt>();
	for (const event of state.events) {
		// `runId` and `type` are non-enumerable compatibility aliases that `readEvents`
		// attaches to every event; the stored fields are `context.runId` and `eventType`.
		// Reading through the aliases keeps this in step with the rest of the kernel.
		if ((event.runId ?? event.context.runId) !== runId) continue;
		if (event.type === "run.execution-launch-requested") {
			// The payload a governance event carries is `{ value, evidence }`; the value is
			// the record this mechanism wrote.
			const value = (event.payload as { value?: Record<string, unknown> }).value ?? {};
			const id = value.executionAttemptId;
			if (typeof id !== "string") continue;
			if (attempts.has(id)) continue; // idempotent
			attempts.set(id, {
				executionAttemptId: id,
				runId,
				requestedAt: typeof value.at === "number" ? value.at : Date.parse(event.occurredAt) || 0,
				bound: null,
			});
		}
		if (event.type === "run.execution-bound") {
			const value = (event.payload as { value?: Record<string, unknown> }).value ?? {};
			const id = value.executionAttemptId;
			if (typeof id !== "string" || typeof value.nativeRunId !== "string") continue;
			const attempt = attempts.get(id);
			// A binding for an attempt that was never announced is a corrupt log, not a
			// new attempt: inventing the parent here would hide the inconsistency.
			if (!attempt || attempt.bound) continue; // idempotent
			attempt.bound = {
				nativeRunId: value.nativeRunId,
				at: typeof value.at === "number" ? value.at : Date.parse(event.occurredAt) || 0,
				pid: typeof value.pid === "number" ? value.pid : null,
				pidNamespaceScope: typeof value.pidNamespaceScope === "string" ? value.pidNamespaceScope : null,
				processStartIdentity: typeof value.processStartIdentity === "string" ? value.processStartIdentity : null,
				hostBootId: typeof value.hostBootId === "string" ? value.hostBootId : null,
			};
		}
	}
	return [...attempts.values()];
}

export function executionAttemptState(attempts: ExecutionAttempt[], run: Run): ExecutionAttemptState {
	// Runs recorded before this mechanism existed have a native Run ID but no events.
	// Calling them BOUND would fabricate a binding that never happened; they are reported
	// as legacy and judged by whatever the sidecar can still prove.
	if (!attempts.length) return run.nativeRunId ? "BOUND" : "NOT_STARTED";
	const latest = attempts.at(-1);
	return latest?.bound ? "BOUND" : "LAUNCH_UNBOUND";
}

/** `pid:<inode>` for the calling process, the same shape the native side records. */
export function currentPidNamespace(): string | null {
	try {
		return fs.readlinkSync("/proc/self/ns/pid");
	} catch {
		return null;
	}
}

/** Kernel boot identifier: unchanged across processes, different after a reboot. */
export function currentHostBootId(): string | null {
	try {
		return fs.readFileSync("/proc/sys/kernel/random/boot_id", "utf8").trim() || null;
	} catch {
		return null;
	}
}

/**
 * The pid's start time from `/proc/<pid>/stat`, which is what makes a PID trustworthy.
 *
 * PIDs are recycled, so "pid 1234 exists" says nothing about whether it is the same 1234.
 * Field 22 of stat - start time in clock ticks since boot - does: the pair (pid, starttime)
 * is unique in practice. Reading it needs care because the process name in field 2 is
 * parenthesised and may itself contain spaces or parentheses, so parsing is anchored on the
 * last `)` rather than on splitting the whole line.
 */
export function processStartIdentity(pid: number): string | null {
	const probed = probeProcessStart(pid);
	return probed.kind === "present" ? probed.starttime : null;
}

/**
 * Read a pid's start time, keeping "gone" distinct from "could not read".
 *
 * The two were previously folded into one `null`, and the caller read it as "the process no
 * longer exists". A pid whose stat is unreadable - a permission change, a transient kernel
 * error, a reaped entry still listed - would therefore be judged dead, which frees that
 * Run's concurrency slot while its child keeps running. The next delegation then starts on
 * top of a child that is still working, and the governor now believes it has capacity it
 * does not have. The absence of an answer is not an answer.
 */
export function probeProcessStart(pid: number): ProcessStartProbe {
	let stat: string;
	try {
		stat = fs.readFileSync(`/proc/${pid}/stat`, "utf8");
	} catch (error) {
		const code = (error as NodeJS.ErrnoException).code;
		// ENOENT is the only code that means the pid is not there. Anything else - EACCES,
		// EPERM, ESRCH under load - leaves us unable to say, so it must not be read as gone.
		if (code === "ENOENT") return { kind: "absent" };
		return { kind: "unreadable" };
	}
	const close = stat.lastIndexOf(")");
	if (close < 0) return { kind: "unreadable" };
	const fields = stat.slice(close + 2).split(" ");
	// After the command name, fields resume at state (field 3), so starttime (22) is
	// at offset 19 from here.
	const starttime = fields[19];
	if (typeof starttime !== "string" || !/^\d+$/.test(starttime)) return { kind: "unreadable" };
	// Field 3 is the process state; `Z` marks one that has exited but not been reaped. It
	// keeps its /proc entry and its start time, so only this flag separates it from a live
	// child.
	return { kind: "present", starttime, state: fields[0] ?? "" };
}

export type ProcessStartProbe =
	/** The pid exists; `starttime` identifies which process holds it. */
	| { kind: "present"; starttime: string; state: string }
	/** The pid is not in the process table. */
	| { kind: "absent" }
	/** The pid may exist, but its stat entry could not be read or parsed. */
	| { kind: "unreadable" };

/**
 * Whether `/proc` gives us any ability to judge a process at all.
 *
 * Asked of our own pid: if this process's own stat cannot be read, then no pid can be, and
 * every verdict on this platform would be a guess.
 */
export function canProbeProcesses(): boolean {
	return probeProcessStart(process.pid).kind === "present";
}

/**
 * Identity for a binding, captured while the child is known to be alive.
 *
 * Every field is nullable on purpose. A platform without `/proc` binds what it can and
 * leaves the rest null, which later reads as "cannot judge" rather than "no process".
 */
export function captureExecutionIdentity(pid: number | undefined): {
	pid: number | null;
	pidNamespaceScope: string | null;
	processStartIdentity: string | null;
	hostBootId: string | null;
} {
	return {
		pid: typeof pid === "number" ? pid : null,
		pidNamespaceScope: currentPidNamespace(),
		processStartIdentity: typeof pid === "number" ? processStartIdentity(pid) : null,
		hostBootId: currentHostBootId(),
	};
}

/**
 * What a bound process is now, using the evidence it left behind.
 *
 * `unknown` is the default for every case that cannot be settled. Releasing a slot needs
 * proof of death, not the absence of proof of life - the two were conflated once and the
 * result was a child running for ten minutes under a freed slot.
 */
export type ProcessVerdict = "alive" | "dead" | "unknown";

export function judgeBoundProcess(attempt: ExecutionAttempt): { verdict: ProcessVerdict; reason: string } {
	const bound = attempt.bound;
	if (!bound) return { verdict: "unknown", reason: "attempt was never bound to a native process" };
	if (bound.pid === null) return { verdict: "unknown", reason: "binding recorded no pid" };
	if (!canProbeProcesses())
		return { verdict: "unknown", reason: "this platform has no /proc, so a pid cannot be judged" };
	const bootId = currentHostBootId();
	// A different boot means every process from the old boot is gone, whatever the pid says.
	if (bound.hostBootId && bootId && bound.hostBootId !== bootId)
		return { verdict: "dead", reason: `host rebooted (boot ${bound.hostBootId} -> ${bootId})` };
	// A different PID namespace means the pid number refers to a different process space;
	// comparing against it would be comparing unrelated things.
	const namespace = currentPidNamespace();
	if (bound.pidNamespaceScope && namespace && bound.pidNamespaceScope !== namespace)
		return { verdict: "unknown", reason: "pid was recorded in a different PID namespace" };
	const probed = probeProcessStart(bound.pid);
	// Only ENOENT proves the pid is gone. An unreadable stat is a missing answer, and
	// treating it as death would release the slot of a child that may still be running.
	if (probed.kind === "unreadable")
		return { verdict: "unknown", reason: `pid ${bound.pid} could not be read, so it cannot be judged` };
	if (probed.kind === "absent") return { verdict: "dead", reason: `pid ${bound.pid} no longer exists` };
	if (bound.processStartIdentity === null)
		return {
			verdict: "unknown",
			reason: "binding recorded no process start identity, so PID reuse cannot be excluded",
		};
	if (probed.starttime !== bound.processStartIdentity)
		return { verdict: "dead", reason: `pid ${bound.pid} was reused by another process` };
	// A zombie still has an entry and the same start time, but it has already exited and is
	// only waiting to be reaped. Reporting it alive would keep a finished child's slot
	// reserved for as long as its parent lives - the reverse error, but the same cost.
	if (probed.state === "Z") return { verdict: "dead", reason: `pid ${bound.pid} exited and is awaiting reaping` };
	return { verdict: "alive", reason: `pid ${bound.pid} is still the bound process` };
}

export function newExecutionAttemptId(): string {
	return `A-${randomUUID()}`;
}

export type { GovernanceEvent };

/**
 * What can be proven about a Run's child right now, and what cannot.
 *
 * This is the read-only half: it never changes the ledger, so asking is free and safe.
 * Termination is a separate, explicit step because releasing a concurrency slot on a
 * wrong guess is exactly the failure that started this work.
 */
export type AttemptProbe = {
	runId: string;
	state: ExecutionAttemptState;
	executionAttemptId: string | null;
	verdict: ProcessVerdict;
	/** Why the verdict is what it is, in terms an operator can act on. */
	reason: string;
	/** True only when the evidence justifies freeing the slot and the reservation. */
	releasable: boolean;
	snapshot: {
		nativeRunId: string | null;
		pid: number | null;
		boundAt: number | null;
		requestedAt: number | null;
	};
};

/**
 * @param boundWindowMs how long an unbound attempt may wait before absence of any native
 *   trace is accepted as "nothing ever started". Too short and a slow cold start is
 *   mistaken for a failed one; too long and a genuinely dead attempt holds its slot.
 */
export function probeExecutionAttempt(run: Run, attempts: ExecutionAttempt[], boundWindowMs = 120_000): AttemptProbe {
	const state = executionAttemptState(attempts, run);
	const latest = attempts.at(-1) ?? null;
	const base = {
		runId: run.runId,
		state,
		executionAttemptId: latest?.executionAttemptId ?? null,
		snapshot: {
			nativeRunId: latest?.bound?.nativeRunId ?? run.nativeRunId ?? null,
			pid: latest?.bound?.pid ?? null,
			boundAt: latest?.bound?.at ?? null,
			requestedAt: latest?.requestedAt ?? null,
		},
	};
	if (state === "NOT_STARTED")
		return { ...base, verdict: "dead", reason: "no child was ever launched for this Run", releasable: true };
	if (state === "LAUNCH_UNBOUND") {
		// The hard case. Nothing in the ledger distinguishes "the spawn never happened" from
		// "the child is running and we lost its identity", because the native side mints the
		// ID we would need to look it up. Waiting out a bounded window is the only way to
		// let the first case resolve without guessing about the second.
		const requestedAt = latest?.requestedAt ?? 0;
		const waited = Date.now() - requestedAt;
		if (waited < boundWindowMs)
			return {
				...base,
				verdict: "unknown",
				reason: `launch requested ${Math.round(waited / 1000)}s ago, inside the ${Math.round(boundWindowMs / 1000)}s binding window`,
				releasable: false,
			};
		// Past the window and still nothing: no native directory, no binding. Even here the
		// honest answer is unknown unless the Run never got a native directory at all -
		// a launch that produced nothing is not proof that nothing was spawned.
		if (!run.nativeAsyncDir)
			return {
				...base,
				verdict: "unknown",
				reason:
					"launch was requested and never bound; the native side accepts no caller-supplied Run ID, " +
					"so whether a child started cannot be determined. Inspect the host for an orphan process before releasing.",
				releasable: false,
			};
		return {
			...base,
			verdict: "unknown",
			reason:
				"launch requested past the binding window but a native directory exists; probe the bound attempt instead",
			releasable: false,
		};
	}
	if (!latest) {
		// No attempt events but a native Run ID: the Run predates execution attempts. Its
		// identity was never recorded, so nothing can be proven about the process now.
		return {
			...base,
			verdict: "unknown",
			reason:
				"this Run predates execution attempts, so no pid or start identity was recorded; " +
				"its process cannot be identified",
			releasable: false,
		};
	}
	const judged = judgeBoundProcess(latest);
	// A Run that already reached a terminal state has released its own slot; probing it
	// again must not imply a second release.
	const terminal = !["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"].includes(run.state);
	return {
		...base,
		verdict: judged.verdict,
		reason: judged.reason,
		releasable: !terminal && judged.verdict === "dead",
	};
}

/**
 * The child's pid as the native side recorded it, or undefined if it has not written it yet.
 *
 * Read from `status.json` because the spawn reply does not carry it. This is a file read at
 * bind time on purpose: a binding without a pid is nearly worthless, since judging the
 * process later needs something to look up.
 */
export function readNativePid(asyncDir: string | null): number | undefined {
	if (!asyncDir) return undefined;
	try {
		const raw = JSON.parse(fs.readFileSync(`${asyncDir}/status.json`, "utf8")) as { pid?: unknown };
		return typeof raw.pid === "number" ? raw.pid : undefined;
	} catch {
		return undefined;
	}
}

/**
 * Wait, briefly, for the native side to write the child's pid.
 *
 * The spawn reply does not carry the pid and `status.json` is written after that reply
 * returns, so reading it the instant the spawn resolves loses the race: measured on a real
 * delegation, the bind ran 486ms before `startedAt` appeared in the sidecar and recorded
 * `pid: null`. A binding without a pid cannot be judged later, which makes the whole
 * orphan mechanism unavailable for exactly the Runs most likely to need it.
 *
 * Bounded on purpose. Waiting forever would turn a stuck sidecar into a stuck delegation;
 * past the deadline the caller binds with what it has and the later probe reports "no pid
 * was recorded" - an honest unknown rather than a fabricated one.
 *
 * @returns the pid, or undefined if it did not appear within `timeoutMs`.
 */
export async function awaitNativePid(asyncDir: string | null, timeoutMs = 2000): Promise<number | undefined> {
	if (!asyncDir) return undefined;
	const deadline = Date.now() + timeoutMs;
	// First read is immediate: the common case after a fast spawn is that the file already
	// exists, and paying a poll interval there would slow every delegation for nothing.
	for (;;) {
		const pid = readNativePid(asyncDir);
		if (pid !== undefined) return pid;
		if (Date.now() >= deadline) return undefined;
		await new Promise((resolve) => setTimeout(resolve, 25));
	}
}

/**
 * Close a Run whose child is provably gone but whose outcome cannot be recovered.
 *
 * The two facts are separated on purpose:
 *
 * - the process is dead, so the concurrency slot can be released;
 * - the outcome and the spend are unknown, so `usageTokens` stays null.
 *
 * Recording zero here would turn a vanished child into a free one. A `FAILED` state is used
 * because that is what happened - the Run did not succeed - while `run.execution-lost`
 * records *why* it is unknown, so a reader that only looks at `state` is not misled into
 * thinking the child reported an error.
 *
 * Deliberately not automatic. Releasing a slot on a wrong guess double-books capacity,
 * which is the failure this whole mechanism exists to prevent, so the caller must have a
 * verdict of `dead` in hand.
 */
export function lostRunEvidence(attempt: ExecutionAttempt | null): Record<string, unknown> {
	return {
		verdict: "dead",
		executionAttemptId: attempt?.executionAttemptId ?? null,
		nativeRunId: attempt?.bound?.nativeRunId ?? null,
		pid: attempt?.bound?.pid ?? null,
		processStartIdentity: attempt?.bound?.processStartIdentity ?? null,
		hostBootId: attempt?.bound?.hostBootId ?? null,
		note: "process is gone; outcome and token usage were never obtained and are recorded as unknown, not zero",
	};
}
