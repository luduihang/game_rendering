import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import type { DelegationSessionOrigin, GovernanceKernel } from "./kernel.ts";
import { readNativeRunStatus } from "./subagent-supervision.ts";

export type ResolvedSessionOrigin = DelegationSessionOrigin & { taskId: string | null };

/** Resolve the caller from Pi's current session, then cross-check child identity with native Run evidence. */
export function resolveSessionOrigin(kernel: GovernanceKernel, ctx: ExtensionContext): ResolvedSessionOrigin {
	const sessionId = ctx.sessionManager.getSessionId();
	const sessionFile = ctx.sessionManager.getSessionFile();
	const header = ctx.sessionManager.getHeader();
	if (!sessionFile || !header || header.id !== sessionId)
		throw new Error("Pi session file and header are required for governed delegation");
	const parentSessionFile = header.parentSession ?? null;
	const state = kernel.getState();
	const observed = state.events.some(
		(event) =>
			event.type === "agent.session-observed" &&
			event.payload.sessionId === sessionId &&
			event.payload.sessionFile === sessionFile &&
			event.payload.parentSessionFile === parentSessionFile,
	);
	if (!observed) throw new Error("Current Pi session has not been observed by governance");
	if (parentSessionFile === null) {
		if (
			Object.values(state.runs).some(
				(run) => run.sessionRef === sessionFile || readNativeRunStatus(run).sessionFile === sessionFile,
			)
		)
			throw new Error("Native child session cannot be treated as a main Agent session");
		return { sessionId, sessionFile, parentRunId: null, taskId: null };
	}
	const matches = Object.values(state.runs).filter(
		(run) =>
			run.parentSessionRef === parentSessionFile &&
			run.nativeRunId &&
			(run.sessionRef === sessionFile || readNativeRunStatus(run).sessionFile === sessionFile),
	);
	if (matches.length !== 1) throw new Error("Child Pi session is not uniquely linked to a governed native Run");
	const parent = matches[0];
	kernel.bindRunSession(parent.runId, sessionId, sessionFile, parentSessionFile);
	if (!["CREATED", "RUNNING", "PAUSED", "INTERRUPTED"].includes(kernel.getState().runs[parent.runId].state))
		throw new Error("Parent Run is no longer active");
	return { sessionId, sessionFile, parentRunId: parent.runId, taskId: parent.taskId };
}
