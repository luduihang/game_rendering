import {
	type AttemptProbe,
	canProbeProcesses,
	executionAttempts,
	probeExecutionAttempt,
} from "./execution-identity.ts";
import type { GovernanceState, Run } from "./types.ts";

/**
 * Runs left `RUNNING` with no process behind them, found by reading only the ledger.
 *
 * The problem: a Run whose child is gone stays `RUNNING` forever. Its concurrency slot
 * stays reserved, so a Task at `maxConcurrent: 1` can never delegate again, and the
 * operator sees an active child that does not exist. Nothing in the normal lifecycle
 * repairs this - only a human noticing and running `run probe`.
 *
 * Why this only reports: settling a Run frees its slot, and a wrong settlement
 * double-books capacity. That failure is what `execution-identity.ts` exists to prevent,
 * so the automatic path stops at naming candidates and the operator (or an explicit
 * command) performs the settling step. The scan is therefore free to run on every
 * session start.
 */
export type OrphanCandidate = {
	runId: string;
	taskId: string;
	executorId: string;
	state: Run["state"];
	/** How long the ledger has said RUNNING, which is only a hint, never evidence. */
	runningSince: number | null;
	probe: AttemptProbe;
};

export type OrphanScan = {
	candidates: OrphanCandidate[];
	/** Runs that were examined and left alone, with the reason, so silence is not ambiguous. */
	judged: { runId: string; verdict: AttemptProbe["verdict"]; reason: string }[];
	/** Why the whole scan could not run, when that is the case. */
	unavailable: string | null;
};

const ACTIVE: Run["state"][] = ["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"];

/**
 * @param boundWindowMs passed through to the probe; a launch younger than this is not
 *   judged because it may still be starting.
 */
export function scanOrphanRuns(state: GovernanceState, boundWindowMs?: number): OrphanScan {
	const candidates: OrphanCandidate[] = [];
	const judged: OrphanScan["judged"] = [];
	for (const run of Object.values(state.runs)) {
		if (!ACTIVE.includes(run.state)) continue;
		const attempts = executionAttempts(state, run.runId);
		const probe = probeExecutionAttempt(run, attempts, boundWindowMs);
		// A Run that never asked for a child has lost nothing, so `execution-lost` is the
		// wrong repair for it - the state would claim a failure that never happened. It is
		// reported as a held slot with a different remedy instead.
		if (probe.state === "NOT_STARTED") {
			judged.push({
				runId: run.runId,
				verdict: probe.verdict,
				reason: "no child was ever launched for this Run; cancel it rather than declaring it lost",
			});
			continue;
		}
		if (probe.releasable)
			candidates.push({
				runId: run.runId,
				taskId: run.taskId,
				executorId: run.executorId,
				state: run.state,
				runningSince: lastRunningAt(state, run.runId),
				probe,
			});
		else judged.push({ runId: run.runId, verdict: probe.verdict, reason: probe.reason });
	}
	// On a platform without /proc every judgement above came out `unknown`, so reporting
	// an empty candidate list alone would read as "nothing is wrong". It means "cannot
	// tell", which is a different answer and has to be said out loud.
	const unavailable = canProbeProcesses()
		? null
		: "this platform has no /proc, so a Run's process cannot be judged; orphan recovery is unavailable and stale slots need manual settlement";
	return { candidates, judged, unavailable };
}

/**
 * When the ledger last said the Run was running, or null if it never said so.
 *
 * Read from events rather than stored: `Run` carries no `startedAt`, and adding one would
 * create a second place for the same fact to disagree with the log. Null is a real answer
 * here - a Run recorded by an older kernel has no such event.
 */
function lastRunningAt(state: GovernanceState, runId: string): number | null {
	let latest: number | null = null;
	for (const event of state.events) {
		if ((event.runId ?? event.context.runId) !== runId) continue;
		// `updateRun` writes `run.started` for the RUNNING transition; there is no `run.running`.
		if (event.type !== "run.started") continue;
		const at = Date.parse(event.occurredAt);
		if (Number.isFinite(at)) latest = at;
	}
	return latest;
}

/**
 * One line per Run the operator has to act on, and nothing when there is nothing to say.
 *
 * Kept separate from the scan so the wording can change without touching the judgement,
 * and so a caller that only wants the count does not pay for the sentences.
 */
export function describeOrphanCandidates(scan: OrphanScan, cli: string): string[] {
	return scan.candidates.map((candidate) => {
		const age =
			candidate.runningSince === null
				? "since an unrecorded time"
				: `for ${Math.round((Date.now() - candidate.runningSince) / 1000)}s`;
		return (
			`Run ${candidate.runId} (${candidate.executorId}, task ${candidate.taskId}) has been ${candidate.state} ` +
			`${age} with no live process: ${candidate.probe.reason}. ` +
			`Its slot is still held. Confirm with: ${cli} run probe ${candidate.runId} --confirm-lost`
		);
	});
}
