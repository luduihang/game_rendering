import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import type { Run } from "./types.ts";

/**
 * What a running child is doing, read from the native side rather than reported by it.
 *
 * A child describing its own progress is a second source of truth, and the weaker one:
 * `turnCount` is counted by the harness, while a self-written "progress: 60%" is an
 * opinion. The native side already records every tool the child launches, so the
 * question "is it stuck?" can be answered without asking the child to be honest or
 * articulate.
 *
 * Nothing here counts toward delivery. A child that ran 78 tools produced activity and
 * possibly nothing else; that distinction is what `artifactProjection` exists to keep.
 */
export type NativeActivity = {
	/** Time this projection was read, not the time of a native event. */
	observedAt: number;
	/** Tool calls seen, oldest first, capped at `limit`. */
	tools: {
		at: number | null;
		tool: string;
		target: string | null;
		durationMs: number | null;
		result: "success" | "error" | null;
	}[];
	/** Last completed assistant message with measured output tokens; a heartbeat is not output. */
	lastOutputAt: number | null;
	/**
	 * How many tool calls were recovered from the scanned tail.
	 *
	 * This is not the total the child ran - scanning stops once enough are found. The
	 * authoritative total is the native `toolCount`; this figure only says how much of
	 * the log was read to build `tools`.
	 */
	collectedCount: number | null;
	/** Set when the event log could not be read; the rest of the fields are then empty, not zero. */
	unavailable: string | null;
};

/**
 * Remove values that look like credentials from a tool argument.
 *
 * Best-effort, not a guarantee: this is a display filter over a string whose meaning
 * cannot be determined, the same limit that makes `bash` a poor security boundary. It
 * exists so a status page does not become a way to read a token out of a command line,
 * and it will miss encodings it does not recognise.
 */
function redact(value: string): string {
	return (
		value
			// `NAME=secret`, the common shape in an inline environment assignment.
			.replace(
				/(\b[A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)[A-Za-z0-9_]*\s*=\s*)([^\s'"]+)/gi,
				"$1[redacted]",
			)
			// `--password secret` and `--api-key=secret`.
			.replace(/(--?(?:password|passwd|token|api[-_]?key|secret)[=\s]+)([^\s'"]+)/gi, "$1[redacted]")
			// Bearer and Basic credentials inside a quoted argument.
			.replace(/(Bearer\s+)[A-Za-z0-9._-]+/gi, "$1[redacted]")
			.slice(0, 200)
	);
}

/** Arguments worth showing: what the tool acted on, never the whole payload. */
function toolTarget(args: unknown): string | null {
	if (!args || typeof args !== "object") return null;
	const record = args as Record<string, unknown>;
	// Ordered by how directly the value identifies the subject of the call.
	for (const key of ["path", "command", "pattern", "query", "url", "file_path"]) {
		const value = record[key];
		if (typeof value === "string" && value.trim()) return redact(value.trim());
	}
	return null;
}

/**
 * Read the child's tool activity.
 *
 * The event log is append-only and unbounded, so it is read from the tail: a child that
 * ran for ten minutes has thousands of events and only the last few matter for "what is
 * it doing now". Reading the whole file on every status call would make observation
 * itself a cost.
 */
export function readNativeActivity(run: Run, limit = 12, maxBytes = 4 * 1024 * 1024): NativeActivity {
	const observedAt = Date.now();
	if (!run.nativeAsyncDir) {
		return {
			observedAt,
			tools: [],
			lastOutputAt: null,
			collectedCount: null,
			unavailable: "Run has no native async directory",
		};
	}
	const file = path.join(run.nativeAsyncDir, "events.jsonl");
	const tools: NativeActivity["tools"] = [];
	let lastOutputAt: number | null = null;
	let outputSeen = false;
	const ends = new Map<string, { at: number | null; result: "success" | "error" }>();
	let collectedCount = 0;
	let handle: number;
	let size: number;
	try {
		size = fs.statSync(file).size;
		handle = fs.openSync(file, "r");
	} catch (error) {
		return {
			observedAt,
			tools: [],
			lastOutputAt: null,
			// Null, not zero: nothing was read, so "no tool calls were collected" would be a
			// claim about the child instead of about the read that failed.
			collectedCount: null,
			unavailable: error instanceof Error ? error.message : String(error),
		};
	}
	try {
		// Read backwards in chunks and stop once enough tool calls are collected.
		//
		// A full scan is not an option: the log had grown to 4 MB in ten minutes, mostly
		// because `tool_execution_end` carries each tool's entire result. A single 256 KB
		// tail slice held no tool events at all, which would have reported a busy child as
		// idle. Chunking backwards keeps the cost proportional to what is shown, and the
		// cap bounds a pathological file. We may continue past the tool limit to
		// find the last measured model output, but never past the byte cap.
		const chunk = 256 * 1024;
		let position = size;
		let carried = "";
		while (position > 0 && size - position < maxBytes && (collectedCount < limit || !outputSeen)) {
			const length = Math.min(chunk, position);
			position -= length;
			const buffer = Buffer.alloc(length);
			fs.readSync(handle, buffer, 0, length, position);
			const lines = (buffer.toString("utf8") + carried).split("\n");
			// The first line is partial unless this chunk starts the file; carry it to the
			// next (earlier) chunk instead of parsing a fragment.
			carried = position === 0 ? "" : (lines.shift() ?? "");
			for (let index = lines.length - 1; index >= 0; index -= 1) {
				const line = lines[index];
				if (!line.trim()) continue;
				let event: unknown;
				try {
					event = JSON.parse(line);
				} catch {
					continue; // a torn line at the tail of a live append
				}
				if (!event || typeof event !== "object") continue;
				const record = event as Record<string, unknown>;
				const timestamp =
					typeof record.ts === "number"
						? record.ts
						: typeof record.observedAt === "number"
							? record.observedAt
							: null;
				if (record.type === "message_end" && !outputSeen) {
					const message = record.message;
					if (
						message &&
						typeof message === "object" &&
						"role" in message &&
						message.role === "assistant" &&
						"usage" in message &&
						message.usage &&
						typeof message.usage === "object" &&
						"output" in message.usage &&
						typeof message.usage.output === "number" &&
						message.usage.output > 0
					) {
						outputSeen = true;
						const rawTime = "timestamp" in message ? message.timestamp : null;
						const messageTime =
							typeof rawTime === "number"
								? rawTime
								: typeof rawTime === "string" && Number.isFinite(Date.parse(rawTime))
									? Date.parse(rawTime)
									: null;
						lastOutputAt = timestamp ?? messageTime;
					}
				}
				if (record.type === "tool_execution_end" && typeof record.toolCallId === "string") {
					ends.set(record.toolCallId, { at: timestamp, result: record.isError === true ? "error" : "success" });
					continue;
				}
				// `start`, not `end`: the arguments live here, the payload does not, and a
				// tool that has started but not finished is exactly what "now" means.
				if (record.type !== "tool_execution_start") continue;
				const tool = typeof record.toolName === "string" ? record.toolName : null;
				if (!tool) continue;
				if (collectedCount >= limit) continue;
				collectedCount += 1;
				// Missing native timestamps remain unknown; reading the file now does not
				// establish when an old tool call occurred.
				const ended = typeof record.toolCallId === "string" ? ends.get(record.toolCallId) : undefined;
				tools.unshift({
					at: timestamp,
					tool,
					target: toolTarget(record.args),
					durationMs: timestamp !== null && ended?.at != null ? Math.max(0, ended.at - timestamp) : null,
					result: ended?.result ?? null,
				});
			}
		}
	} catch (error) {
		return {
			observedAt,
			tools: [],
			lastOutputAt: null,
			collectedCount: null,
			unavailable: error instanceof Error ? error.message : String(error),
		};
	} finally {
		fs.closeSync(handle);
	}
	return { observedAt, tools: tools.slice(-limit), lastOutputAt, collectedCount, unavailable: null };
}

/**
 * Where the child's answer ended up, and whether it is worth anything.
 *
 * The failure this exists for: a Run finished SUCCEEDED, its artifact file existed, and
 * it held 342 characters - a child that stopped early and said nothing. Existence alone
 * would have reported that as a delivery.
 */
export type ArtifactReference = {
	path: string;
	sha256: string;
	sizeBytes: number;
	createdAt: number;
	/** `EMPTY` and `THIN` are not failures; they are the difference between output and substance. */
	state: "PRESENT" | "THIN" | "EMPTY";
};

/**
 * Minimum characters before an artifact is treated as having content.
 *
 * Deliberately one number for all agents rather than a quality judgement: this is not
 * "is the report good", which only a reviewer can say, but "is there a report". A real
 * report from this system runs thousands of characters; 342 was an empty shell.
 */
const THIN_THRESHOLD = 500;

/**
 * Locate the child's final message.
 *
 * pi-subagents writes `<artifactsDir>/<nativeRunId>_<agent>_output.md` next to the meta
 * and transcript files. The directory is declared in `status.json`; guessing it from the
 * session layout would break the moment the layout changes.
 */
export function artifactProjection(
	run: Run,
	artifactsDir: string | null,
	nativeAgent: string | null,
): ArtifactReference | null {
	if (!artifactsDir || !run.nativeRunId) return null;
	// The agent name is part of the filename, so a wrong name silently finds nothing;
	// the directory is scanned instead so a missing `nativeAgent` still works.
	let names: string[];
	try {
		names = fs.readdirSync(artifactsDir);
	} catch {
		return null;
	}
	const prefix = `${run.nativeRunId}_`;
	const candidate = names.find(
		(name) =>
			name.startsWith(prefix) &&
			name.endsWith("_output.md") &&
			(!nativeAgent || name.startsWith(`${prefix}${nativeAgent}_`)),
	);
	if (!candidate) return null;
	const file = path.join(artifactsDir, candidate);
	try {
		const stat = fs.statSync(file);
		const body = fs.readFileSync(file);
		const text = body.toString("utf8").trim();
		return {
			path: file,
			sha256: createHash("sha256").update(body).digest("hex"),
			sizeBytes: stat.size,
			createdAt: Math.round(stat.mtimeMs),
			// A hash proves the bytes did not change; it says nothing about whether they
			// answer the question. Size is the cheapest signal that the child actually
			// wrote something, and it is our own measurement rather than the child's claim.
			state: text.length === 0 ? "EMPTY" : text.length < THIN_THRESHOLD ? "THIN" : "PRESENT",
		};
	} catch {
		return null;
	}
}

/**
 * One Run as it actually is, right now.
 *
 * Every field is nullable and null means unknown, never zero. That rule is the whole
 * design: a sidecar that cannot be read must not produce a Run that looks idle, and a
 * Turn count of 71 must not be reported as progress toward a total nobody knows.
 */
export type RunObservation = {
	runId: string;
	taskId: string;
	governedState: string;
	observedAt: number;
	native: {
		state: string | null;
		outcome: "SUCCEEDED" | "FAILED" | null;
		agent: string | null;
		model: string | null;
		turns: number | null;
		tools: number | null;
		tokens: number | null;
		outputTokens: number | null;
		windowTokens: number | null;
		windowPeakTokens: number | null;
		costUsd: number | null;
		activityState: string | null;
		/** Last measured model output, not the native heartbeat. */
		lastActivityAt: number | null;
		deadlineAt: number | null;
		step: { index: number | null; count: number | null };
		timedOut: boolean | null;
	};
	activity: NativeActivity;
	artifact: ArtifactReference | null;
	/** What could not be read, so a caller can show why a figure is missing. */
	unknowns: string[];
};

import { readNativeRunStatus } from "./subagent-supervision.ts";

export function observeRun(run: Run): RunObservation {
	const unknown: string[] = [];
	let status: ReturnType<typeof readNativeRunStatus> | null = null;
	try {
		status = readNativeRunStatus(run);
	} catch (error) {
		unknown.push(`native status unreadable: ${error instanceof Error ? error.message : String(error)}`);
	}
	if (status && !status.available) unknown.push(`native status unavailable: ${status.reason ?? "no carrier file"}`);
	if (status?.available && ["complete", "failed", "stopped"].includes(status.state ?? "") && !status.terminalOutcome)
		unknown.push("native status looks terminal but no verified process outcome is available");
	const activity = readNativeActivity(run);
	if (activity.unavailable) unknown.push(`activity log unreadable: ${activity.unavailable}`);
	else if ((status?.toolCount ?? 0) > 0 && activity.tools.length === 0)
		unknown.push("native tool count is nonzero but no named tool event was found in the scanned log");
	if (activity.tools.some((tool) => tool.at === null))
		unknown.push("some native tool events have no occurrence timestamp");
	if (activity.lastOutputAt === null)
		unknown.push("last model output time is unavailable; native heartbeat is not progress");
	const artifact = artifactProjection(run, status?.artifactsDir ?? null, status?.nativeAgent ?? null);
	if (!artifact && run.state === "SUCCEEDED") unknown.push("Run succeeded but no artifact file was found");
	// An unreadable turn count is a gap in what we know, not a Run that did no turns.
	if (status?.turnCount === undefined) unknown.push("turn count not reported by the native side");
	return {
		runId: run.runId,
		taskId: run.taskId,
		governedState: run.state,
		observedAt: activity.observedAt,
		native: {
			state: status?.state ?? null,
			outcome: status?.terminalOutcome ?? null,
			agent: status?.nativeAgent ?? null,
			model: status?.model ?? null,
			turns: status?.turnCount ?? null,
			tools: status?.toolCount ?? null,
			tokens: status?.totalTokens ?? null,
			outputTokens: status?.outputTokens ?? null,
			windowTokens: status?.windowTokens ?? null,
			windowPeakTokens: status?.windowPeakTokens ?? null,
			costUsd: status?.costUsd ?? null,
			activityState: status?.activityState ?? null,
			lastActivityAt: activity.lastOutputAt,
			deadlineAt: status?.deadlineAt ?? null,
			step: { index: status?.currentStep ?? null, count: status?.stepCount ?? null },
			timedOut: status?.timedOut ?? null,
		},
		activity,
		artifact,
		unknowns: unknown,
	};
}
