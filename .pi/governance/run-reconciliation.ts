import type { GovernanceKernel } from "./kernel.ts";
import { compareNativeTools, readNativeRunStatus } from "./subagent-supervision.ts";
import type { Run } from "./types.ts";

export function reconcileNativeRun(
	kernel: GovernanceKernel,
	runId: string,
	actor: string,
): { run: Run; changed: boolean } {
	const state = kernel.getState();
	const run = state.runs[runId];
	if (!run) throw new Error("Unknown Run");
	if (!run.nativeRunId || !run.nativeAsyncDir) throw new Error("Run has no native status reference");
	const native = readNativeRunStatus(run);
	if (!native.available || !native.terminalOutcome || native.processTerminal !== "observed" || !native.statusSha256)
		throw new Error(`Native terminal evidence is incomplete: ${native.reason ?? native.state ?? "unknown"}`);
	const modelMatch = native.model ? native.model === run.routing?.model : null;
	const approvedTools = run.routing?.expectedTools ?? state.delegations[run.delegationId]?.authority.tools ?? null;
	const toolCheck = compareNativeTools(
		native.nativeTools,
		approvedTools,
		run.routing?.pluginVersion,
		run.routing?.expectedTools !== undefined,
	);
	const agentMatch = native.nativeAgent ? native.nativeAgent === run.routing?.agent : null;
	const outcome =
		modelMatch === false || toolCheck.match === false || agentMatch === false ? "FAILED" : native.terminalOutcome;
	if (run.state !== "RUNNING" && run.state !== outcome)
		throw new Error(`Run state ${run.state} conflicts with native outcome ${outcome}`);
	const evidence = {
		nativeRunId: run.nativeRunId,
		nativeState: native.state,
		statusFile: `${run.nativeAsyncDir}/status.json`,
		statusSha256: native.statusSha256,
		terminalFile: native.terminalSha256 ? `${run.nativeAsyncDir}/process-terminal.json` : null,
		terminalSha256: native.terminalSha256 ?? null,
		processTerminal: native.processTerminal,
		requestedModel: run.routing?.model ?? null,
		observedModel: native.model ?? null,
		modelEvidenceSource: native.modelEvidenceSource ?? null,
		sessionSha256: native.sessionSha256 ?? null,
		modelMatch,
		approvedTools,
		nativeTools: native.nativeTools ?? null,
		nativeInternalTools: toolCheck.internalTools,
		nativeExecutionTools: toolCheck.executionTools,
		toolEscalation: toolCheck.match === false ? toolCheck.escalation : null,
		toolMatch: toolCheck.match,
		nativeAgent: native.nativeAgent ?? null,
		agentMatch,
		pluginVersion: run.routing?.pluginVersion ?? null,
		compliance:
			modelMatch === false || toolCheck.match === false || agentMatch === false
				? "mismatch"
				: modelMatch === null || toolCheck.match === null || agentMatch === null
					? "unknown"
					: "verified",
		policyDigest: run.routing?.policyDigest ?? null,
	};
	let updated = run;
	if (run.state === "RUNNING") {
		updated = kernel.updateRun(
			runId,
			outcome,
			{
				sessionRef: native.sessionFile ?? run.sessionRef,
				usageTokens: native.totalTokens ?? run.usageTokens,
				costUsd: native.costUsd ?? run.costUsd,
			},
			`native-status:${native.statusSha256}`,
			actor,
			evidence,
		);
	}
	if (run.workspaceId && kernel.getState().workspaces[run.workspaceId]?.holderRunId === runId)
		kernel.releaseWorkspace(
			run.workspaceId,
			runId,
			actor,
			`native-terminal:${native.terminalSha256 ?? native.statusSha256}`,
		);
	return { run: updated, changed: run.state === "RUNNING" };
}
