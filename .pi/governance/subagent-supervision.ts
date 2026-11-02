import { createHash, randomUUID } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { Run } from "./types.ts";

export type SubagentRpcReply =
	| { success: true; data: { details?: Record<string, unknown>; text?: string } }
	| { success: false; error: { message: string } };

export async function subagentRpc(
	pi: ExtensionAPI,
	method: string,
	params: Record<string, unknown>,
	signal?: AbortSignal,
	requestId: string = randomUUID(),
): Promise<SubagentRpcReply> {
	const replyEvent = `subagents:rpc:v1:reply:${requestId}`;
	let unsubscribe: (() => void) | undefined;
	let timer: ReturnType<typeof setTimeout> | undefined;
	let rejectPending: ((error: Error) => void) | undefined;
	const reply = new Promise<SubagentRpcReply>((resolve, reject) => {
		rejectPending = reject;
		unsubscribe = pi.events.on(replyEvent, (value) => {
			if (!value || typeof value !== "object" || !("success" in value)) return;
			resolve(value as SubagentRpcReply);
		});
		timer = setTimeout(
			() => reject(new Error(`Pi subagent ${method} RPC timeout; inspect rpc-spawn-${requestId} before retry`)),
			30_000,
		);
	});
	const onAbort = () => rejectPending?.(new Error(`Pi subagent ${method} RPC interrupted; reconcile before retry`));
	signal?.addEventListener("abort", onAbort, { once: true });
	try {
		pi.events.emit("subagents:rpc:v1:request", {
			version: 1,
			requestId,
			method,
			params,
			source: { extension: "agent-governance-v0.1" },
		});
		return await reply;
	} finally {
		unsubscribe?.();
		if (timer) clearTimeout(timer);
		signal?.removeEventListener("abort", onAbort);
	}
}

export type NativeRunStatus = {
	available: boolean;
	reason?: string;
	runId: string | null;
	state?: string;
	model?: string;
	modelEvidenceSource?: "child-session" | "native-status";
	sessionSha256?: string;
	activityState?: string;
	currentTool?: string;
	lastUpdate?: number;
	totalTokens?: number;
	windowTokens?: number;
	windowPeakTokens?: number;
	outputTokens?: number;
	costUsd?: number;
	sessionFile?: string;
	outputFile?: string;
	asyncDir?: string;
	/** Tools the native child actually launched with, as declared in its recovery descriptor. */
	nativeTools?: string[];
	nativeAgent?: string;
	/**
	 * The work the child actually did, as the native side counts it.
	 *
	 * These fields have always been in `status.json`; they were simply not declared,
	 * so the ledger could say a Run was running but never what it was doing. A child
	 * that ran 71 turns and 78 tools looked the same as one that had just started.
	 *
	 * They are counters, not progress: 40 of 71 turns is not "56% done", because the
	 * number of turns a task needs is not known until it finishes.
	 */
	turnCount?: number;
	toolCount?: number;
	currentStep?: number;
	stepCount?: number;
	steps?: { agent?: string; status?: string; exitCode?: number | null }[];
	startedAt?: number;
	lastActivityAt?: number;
	deadlineAt?: number;
	timeoutMs?: number;
	timedOut?: boolean;
	pid?: number;
	/** `pid:[<inode>]`; identifies the PID namespace the pid belongs to. */
	pidNamespaceScope?: string;
	artifactsDir?: string;
	sessionDir?: string;
	processTerminal?: string;
	terminalOutcome?: "SUCCEEDED" | "FAILED";
	statusSha256?: string;
	terminalSha256?: string;
};

/** pi-subagents 0.77.0 injects this coordination tool after loading the Agent tool list. */
export function compareNativeTools(
	nativeTools: string[] | undefined,
	approvedTools: string[] | null,
	pluginVersion: string | undefined,
	requireExact: boolean,
): { match: boolean | null; escalation: string[]; internalTools: string[]; executionTools: string[] | null } {
	if (!nativeTools || !approvedTools)
		return { match: null, escalation: [], internalTools: [], executionTools: nativeTools ?? null };
	const internalTools: string[] =
		pluginVersion === "0.77.0" ? nativeTools.filter((tool) => tool === "contact_supervisor") : [];
	const executionTools = nativeTools.filter((tool) => !internalTools.includes(tool));
	const escalation = executionTools.filter((tool) => !approvedTools.includes(tool));
	return {
		match: escalation.length === 0 && (!requireExact || executionTools.length === approvedTools.length),
		escalation,
		internalTools,
		executionTools,
	};
}

export function readNativeRunStatus(run: Run): NativeRunStatus {
	const unavailable = (reason: string): NativeRunStatus => ({ available: false, reason, runId: run.nativeRunId });
	if (!run.nativeRunId || !run.nativeAsyncDir) return unavailable("Native run reference is incomplete");
	const file = path.join(run.nativeAsyncDir, "status.json");
	let value: unknown;
	let statusRaw: string;
	try {
		if (fs.statSync(file).size > 1024 * 1024) return unavailable("Native status exceeds 1 MiB");
		statusRaw = fs.readFileSync(file, "utf8");
		value = JSON.parse(statusRaw);
	} catch {
		return unavailable("Native status artifact is missing or unreadable");
	}
	if (!value || typeof value !== "object" || Array.isArray(value))
		return unavailable("Invalid native status artifact");
	const status = value as Record<string, unknown>;
	if (status.runId !== run.nativeRunId) return unavailable("Native status Run ID mismatch");
	const tokens = status.totalTokens;
	const cost = status.totalCost;
	let proof: unknown =
		status.processTerminal &&
		typeof status.processTerminal === "object" &&
		"runId" in status.processTerminal &&
		status.processTerminal.runId === run.nativeRunId
			? status.processTerminal
			: undefined;
	let terminalRaw: string | undefined;
	try {
		const proofFile = path.join(run.nativeAsyncDir, "process-terminal.json");
		if (fs.statSync(proofFile).size <= 1024 * 1024) {
			const raw = fs.readFileSync(proofFile, "utf8");
			const candidate: unknown = JSON.parse(raw);
			if (
				candidate &&
				typeof candidate === "object" &&
				"runId" in candidate &&
				candidate.runId === run.nativeRunId
			) {
				proof = candidate;
				terminalRaw = raw;
			}
		}
	} catch {
		// Older plugin artifacts may only include an embedded proof.
	}
	// The child's launch tool set lives in the recovery descriptor, not in status.json.
	// Read it here so the governance layer can compare it with the approved authority.
	let nativeTools: string[] | undefined;
	let nativeAgent: string | undefined;
	let descriptorSessionFile: string | undefined;
	try {
		const descriptorFile = path.join(run.nativeAsyncDir, "recovery-descriptor.json");
		if (fs.statSync(descriptorFile).size <= 1024 * 1024) {
			const descriptor: unknown = JSON.parse(fs.readFileSync(descriptorFile, "utf8"));
			if (
				descriptor &&
				typeof descriptor === "object" &&
				"tools" in descriptor &&
				Array.isArray(descriptor.tools) &&
				descriptor.tools.every((entry) => typeof entry === "string")
			)
				nativeTools = descriptor.tools as string[];
			if (
				descriptor &&
				typeof descriptor === "object" &&
				"agent" in descriptor &&
				typeof descriptor.agent === "string"
			)
				nativeAgent = descriptor.agent;
			if (
				descriptor &&
				typeof descriptor === "object" &&
				"sourceRunId" in descriptor &&
				descriptor.sourceRunId === run.nativeRunId &&
				"sessionFile" in descriptor &&
				typeof descriptor.sessionFile === "string"
			)
				descriptorSessionFile = descriptor.sessionFile;
		}
	} catch {
		// Older plugin artifacts may omit the descriptor.
	}
	if (descriptorSessionFile && typeof status.sessionFile === "string" && descriptorSessionFile !== status.sessionFile)
		return unavailable("Native session file differs between status and recovery descriptor");
	const sessionFile = typeof status.sessionFile === "string" ? status.sessionFile : descriptorSessionFile;
	let observedModel: string | undefined;
	let sessionSha256: string | undefined;
	if (sessionFile) {
		try {
			if (fs.statSync(sessionFile).size <= 32 * 1024 * 1024) {
				const sessionRaw = fs.readFileSync(sessionFile, "utf8");
				const models = new Set<string>();
				for (const line of sessionRaw.split("\n")) {
					if (!line.includes('"role":"assistant"')) continue;
					let entry: unknown;
					try {
						entry = JSON.parse(line);
					} catch {
						continue;
					}
					if (!entry || typeof entry !== "object" || !("message" in entry)) continue;
					const message = entry.message;
					if (!message || typeof message !== "object" || !("role" in message)) continue;
					if (message.role !== "assistant") continue;
					if (
						"provider" in message &&
						"model" in message &&
						typeof message.provider === "string" &&
						typeof message.model === "string"
					)
						models.add(`${message.provider}/${message.model}`);
				}
				if (models.size === 1) {
					observedModel = [...models][0];
					sessionSha256 = createHash("sha256").update(sessionRaw).digest("hex");
				}
			}
		} catch {
			// Missing, incomplete, or oversized child sessions leave the model unknown.
		}
	}
	const observed = proof && typeof proof === "object" && "state" in proof && proof.state === "observed";
	const instances =
		observed && proof && typeof proof === "object" && "instances" in proof && Array.isArray(proof.instances)
			? proof.instances
			: [];
	const runners = instances.filter((entry) => entry && typeof entry === "object" && entry.kind === "runner");
	const runnerExitedCleanly =
		runners.length > 0 && runners.every((entry) => entry.exitCode === 0 && entry.signal === null);
	const steps = Array.isArray(status.steps) ? status.steps : [];
	const stepsSucceeded =
		steps.length > 0 &&
		steps.every((entry) => entry && typeof entry === "object" && entry.status === "complete" && entry.exitCode === 0);
	const terminalOutcome = observed
		? status.state === "complete" && runnerExitedCleanly && stepsSucceeded
			? "SUCCEEDED"
			: status.state === "failed"
				? "FAILED"
				: undefined
		: undefined;
	return {
		available: true,
		runId: run.nativeRunId,
		asyncDir: run.nativeAsyncDir,
		statusSha256: createHash("sha256").update(statusRaw).digest("hex"),
		...(terminalRaw ? { terminalSha256: createHash("sha256").update(terminalRaw).digest("hex") } : {}),
		...(terminalOutcome ? { terminalOutcome } : {}),
		...(typeof status.state === "string" ? { state: status.state } : {}),
		...(observedModel
			? { model: observedModel, modelEvidenceSource: "child-session" as const, sessionSha256 }
			: typeof status.model === "string"
				? { model: status.model, modelEvidenceSource: "native-status" as const }
				: {}),
		...(typeof status.activityState === "string" ? { activityState: status.activityState } : {}),
		...(typeof status.currentTool === "string" ? { currentTool: status.currentTool } : {}),
		...(typeof status.lastUpdate === "number" ? { lastUpdate: status.lastUpdate } : {}),
		// Absent values stay absent so a reader can tell "no data" from "zero turns".
		// Defaulting them to 0 is how an unreadable sidecar becomes a confident answer.
		...(typeof status.turnCount === "number" ? { turnCount: status.turnCount } : {}),
		...(typeof status.toolCount === "number" ? { toolCount: status.toolCount } : {}),
		...(typeof status.currentStep === "number" ? { currentStep: status.currentStep } : {}),
		...(typeof status.chainStepCount === "number" ? { stepCount: status.chainStepCount } : {}),
		...(Array.isArray(status.steps)
			? {
					steps: status.steps.flatMap((step) =>
						step && typeof step === "object"
							? [
									{
										...(typeof step.agent === "string" ? { agent: step.agent } : {}),
										...(typeof step.status === "string" ? { status: step.status } : {}),
										...(typeof step.exitCode === "number" || step.exitCode === null
											? { exitCode: step.exitCode as number | null }
											: {}),
									},
								]
							: [],
					),
				}
			: {}),
		...(typeof status.startedAt === "number" ? { startedAt: status.startedAt } : {}),
		...(typeof status.lastActivityAt === "number" ? { lastActivityAt: status.lastActivityAt } : {}),
		...(typeof status.deadlineAt === "number" ? { deadlineAt: status.deadlineAt } : {}),
		...(typeof status.timeoutMs === "number" ? { timeoutMs: status.timeoutMs } : {}),
		...(typeof status.timedOut === "boolean" ? { timedOut: status.timedOut } : {}),
		...(typeof status.pid === "number" ? { pid: status.pid } : {}),
		...(typeof status.pidNamespaceScope === "string" ? { pidNamespaceScope: status.pidNamespaceScope } : {}),
		...(typeof status.artifactsDir === "string" ? { artifactsDir: status.artifactsDir } : {}),
		...(typeof status.sessionDir === "string" ? { sessionDir: status.sessionDir } : {}),
		...(tokens && typeof tokens === "object" && "total" in tokens && typeof tokens.total === "number"
			? { totalTokens: tokens.total }
			: {}),
		...(tokens && typeof tokens === "object" && "window" in tokens && typeof tokens.window === "number"
			? { windowTokens: tokens.window }
			: {}),
		...(tokens && typeof tokens === "object" && "windowPeak" in tokens && typeof tokens.windowPeak === "number"
			? { windowPeakTokens: tokens.windowPeak }
			: {}),
		...(tokens && typeof tokens === "object" && "output" in tokens && typeof tokens.output === "number"
			? { outputTokens: tokens.output }
			: {}),
		...(cost && typeof cost === "object" && "costUsd" in cost && typeof cost.costUsd === "number"
			? { costUsd: cost.costUsd }
			: {}),
		...(nativeTools ? { nativeTools } : {}),
		...(nativeAgent ? { nativeAgent } : {}),
		...(sessionFile ? { sessionFile } : {}),
		...(typeof status.outputFile === "string" ? { outputFile: status.outputFile } : {}),
		...(proof && typeof proof === "object" && "state" in proof && typeof proof.state === "string"
			? { processTerminal: proof.state }
			: {}),
	};
}

/**
 * Whether the native process behind a Run has actually stopped.
 *
 * "Cancelled" is a governance record, not a fact about a process. The two came
 * apart in a way that cost real money: `gov run cancel` wrote `CANCELLED`, freed
 * the concurrency slot, and the child kept working for another ten minutes - 853,137
 * tokens - until its own timeout fired. The slot was free while the child ran, so a
 * delegation made in between would have been the second concurrent child the kernel
 * believed was the first.
 *
 * Only three answers are possible, and `running` is the default for anything this
 * cannot prove. An unreadable sidecar is not evidence of a stop.
 */
export type NativeRunLiveness = "running" | "stopped" | "unknown";

export function nativeRunLiveness(run: Run): NativeRunLiveness {
	if (!run.nativeRunId || !run.nativeAsyncDir) return "unknown";
	let status: NativeRunStatus;
	try {
		status = readNativeRunStatus(run);
	} catch {
		return "unknown";
	}
	if (!status.available) return "unknown";
	// The process terminal record is written by the runner when it exits. Its presence
	// is the only proof that nothing is left to consume the stop request.
	if (status.processTerminal) return "stopped";
	if (status.state === "running" || status.state === "queued" || status.state === "paused") return "running";
	if (status.state === "complete" || status.state === "failed") return "stopped";
	return "unknown";
}

/**
 * Ask a running child to stop, by writing the request its runner already watches.
 *
 * pi-subagents gives each run a control directory and the runner polls it. Writing
 * there is the same path its own `stop` action uses, so it needs no extension runtime
 * and works from a CLI invocation - which is where cancellation is usually issued.
 *
 * The caller must then wait for confirmation: the request only says "stop", and the
 * child takes time to notice. Returning success here would be the original bug in a
 * new place.
 */
export function requestNativeStop(run: Run, reason: string): { requested: boolean; detail: string } {
	if (!run.nativeAsyncDir) return { requested: false, detail: "Run has no native async directory" };
	const dir = path.join(run.nativeAsyncDir, "control", "stop-requests");
	try {
		fs.mkdirSync(dir, { recursive: true });
		// Written under a temporary name and renamed so the watcher never reads a
		// partially written file.
		const name = `stop-${Date.now()}-${process.pid}.json`;
		const target = path.join(dir, name);
		const temp = `${target}.tmp`;
		fs.writeFileSync(
			temp,
			`${JSON.stringify({ version: 1, type: "stop", source: "governance", reason, ts: Date.now() })}\n`,
		);
		fs.renameSync(temp, target);
		return { requested: true, detail: target };
	} catch (error) {
		return { requested: false, detail: error instanceof Error ? error.message : String(error) };
	}
}

/**
 * Poll until the native process is provably stopped, or the budget runs out.
 *
 * A stop request is not a stop. The runner has to notice it, unwind, and write the
 * process terminal record; only that record proves nothing is left running. Polling
 * without a bound would hang the caller, so the wait is limited and a timeout is
 * reported as "not confirmed" rather than as success.
 */
export async function awaitNativeStop(
	run: Run,
	timeoutMs = 30_000,
	intervalMs = 250,
): Promise<{ stopped: boolean; detail: string }> {
	const deadline = Date.now() + timeoutMs;
	let last: NativeRunLiveness = "unknown";
	while (Date.now() < deadline) {
		last = nativeRunLiveness(run);
		if (last === "stopped") return { stopped: true, detail: "native process exited" };
		await new Promise((resolve) => setTimeout(resolve, intervalMs));
	}
	return {
		stopped: false,
		detail:
			last === "running"
				? `the process was still running after ${timeoutMs}ms`
				: `the stop could not be confirmed (native state ${last})`,
	};
}
