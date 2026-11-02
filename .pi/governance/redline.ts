import type { RedlineRefusal } from "./types.ts";

/**
 * RED-5: a refusal that leaves no trace cannot be audited.
 *
 * Every hard guard in the kernel throws on the way out. Throwing alone means the
 * ledger shows a project with no attempts, which reads identically to a project
 * where nothing was attempted. This marker travels on the error itself, so the
 * refusal is recorded exactly once no matter which guard produced it and how
 * deep the caller is.
 *
 * It exists because recording inside `store.append` does not work: the check
 * callback runs while the writer lock is held, and appending from there
 * deadlocks on the lock file.
 */
const REFUSAL = Symbol.for("agent-governance/redline-refusal");

type MarkedError = Error & {
	[REFUSAL]?: {
		code: RedlineRefusal["code"];
		context: Partial<Pick<RedlineRefusal, "taskId" | "runId" | "delegationId">>;
		detail: Record<string, unknown>;
		operation: string;
		recorded: boolean;
	};
};

/**
 * Throw a refusal. The kernel catches it at the public boundary, writes
 * `redline.triggered`, and rethrows the same error so callers see the original
 * message.
 */
export function refuse(
	code: RedlineRefusal["code"],
	message: string,
	operation: string,
	detail: Record<string, unknown> = {},
	context: Partial<Pick<RedlineRefusal, "taskId" | "runId" | "delegationId">> = {},
): never {
	const error = new Error(message) as MarkedError;
	error[REFUSAL] = { code, context, detail, operation, recorded: false };
	throw error;
}

export function refusalOf(error: unknown): MarkedError[typeof REFUSAL] {
	if (!(error instanceof Error)) return undefined;
	const marked = (error as MarkedError)[REFUSAL];
	return marked?.recorded ? undefined : marked;
}

export function markRefusalRecorded(error: unknown): void {
	if (!(error instanceof Error)) return;
	const marked = (error as MarkedError)[REFUSAL];
	if (marked) marked.recorded = true;
}

/** Build the ledger payload for a refused attempt. */
export function refusalPayload(error: Error): RedlineRefusal {
	const marked = (error as MarkedError)[REFUSAL];
	if (!marked) throw new Error("Not a refusal");
	return {
		code: marked.code,
		message: error.message,
		operation: marked.operation,
		taskId: marked.context.taskId ?? null,
		runId: marked.context.runId ?? null,
		delegationId: marked.context.delegationId ?? null,
		detail: marked.detail,
	};
}
