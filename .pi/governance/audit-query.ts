import type { Delegation, GovernanceEvent, GovernanceState, ProjectArchive, Run } from "./types.ts";

export type AuditEventReference = {
	sequence: number;
	eventId: string;
	eventType: string;
	recordedAt: string;
	actorId: string;
	subject: GovernanceEvent["subject"];
};

export type DelegationAuditRecord = {
	delegation: Delegation;
	status: "authorized" | "cancelled";
	parentDelegationId: string | null;
	childDelegationIds: string[];
	runs: Pick<Run, "runId" | "state" | "retryOf" | "nativeRunId" | "workspaceId">[];
	events: AuditEventReference[];
};

function reference(event: GovernanceEvent): AuditEventReference {
	return {
		sequence: event.sequence,
		eventId: event.eventId,
		eventType: event.eventType,
		recordedAt: event.recordedAt,
		actorId: event.actor.id,
		subject: event.subject,
	};
}

export function queryDelegations(
	state: GovernanceState,
	taskId?: string,
): {
	ledgerSequence: number;
	records: DelegationAuditRecord[];
	sourceSequences: number[];
} {
	const authorized = state.events.filter(
		(event) => event.eventType === "governance.delegation.authorized" && (!taskId || event.context.taskId === taskId),
	);
	const delegations = authorized.map((event) => event.payload.value as Delegation);
	const records = delegations.map((delegation) => {
		const events = state.events.filter(
			(event) =>
				event.context.delegationId === delegation.delegationId ||
				(event.context.runId !== null &&
					Object.values(state.runs).some(
						(run) => run.runId === event.context.runId && run.delegationId === delegation.delegationId,
					)),
		);
		return {
			delegation,
			status: events.some((event) => event.eventType === "governance.delegation.cancelled")
				? ("cancelled" as const)
				: ("authorized" as const),
			parentDelegationId: delegation.parentDelegationId,
			childDelegationIds: delegations
				.filter((candidate) => candidate.parentDelegationId === delegation.delegationId)
				.map((candidate) => candidate.delegationId),
			runs: Object.values(state.runs)
				.filter((run) => run.delegationId === delegation.delegationId)
				.map(({ runId, state: runState, retryOf, nativeRunId, workspaceId }) => ({
					runId,
					state: runState,
					retryOf,
					nativeRunId,
					workspaceId,
				})),
			events: events.map(reference),
		};
	});
	return {
		ledgerSequence: state.events.at(-1)?.sequence ?? 0,
		records,
		sourceSequences: [...new Set(records.flatMap((record) => record.events.map((event) => event.sequence)))].sort(
			(a, b) => a - b,
		),
	};
}

export function queryRunLineage(
	state: GovernanceState,
	runId: string,
): {
	ledgerSequence: number;
	run: Run;
	delegation: Delegation;
	ancestorRuns: Run[];
	descendantRuns: Run[];
	events: AuditEventReference[];
	sourceSequences: number[];
} {
	const run = state.runs[runId];
	if (!run) throw new Error("Unknown Run");
	const delegation = state.delegations[run.delegationId];
	if (!delegation) throw new Error("Run delegation is missing");
	const ancestorRuns: Run[] = [];
	let parentRunId = delegation.parentRunId;
	const seen = new Set<string>();
	while (parentRunId) {
		if (seen.has(parentRunId)) throw new Error("Delegation ancestry contains a cycle");
		seen.add(parentRunId);
		const parent = state.runs[parentRunId];
		if (!parent) break;
		ancestorRuns.unshift(parent);
		parentRunId = state.delegations[parent.delegationId]?.parentRunId ?? null;
	}
	const descendantRuns: Run[] = [];
	const queue = [runId];
	while (queue.length) {
		const parent = queue.shift();
		for (const childDelegation of Object.values(state.delegations).filter(
			(candidate) => candidate.parentRunId === parent,
		)) {
			for (const childRun of Object.values(state.runs).filter(
				(candidate) => candidate.delegationId === childDelegation.delegationId,
			)) {
				descendantRuns.push(childRun);
				queue.push(childRun.runId);
			}
		}
	}
	const relatedRunIds = new Set([
		runId,
		...ancestorRuns.map((entry) => entry.runId),
		...descendantRuns.map((entry) => entry.runId),
	]);
	const relatedDelegationIds = new Set([run, ...ancestorRuns, ...descendantRuns].map((entry) => entry.delegationId));
	const relatedDeliverableIds = new Set(
		Object.values(state.deliverables)
			.filter((deliverable) => deliverable.runId !== null && relatedRunIds.has(deliverable.runId))
			.map((deliverable) => deliverable.deliverableId),
	);
	const relatedVerificationIds = new Set(
		Object.values(state.verifications)
			.filter((verification) => relatedDeliverableIds.has(verification.deliverableId))
			.map((verification) => verification.verificationId),
	);
	const events = state.events.filter(
		(event) =>
			(event.context.runId !== null && relatedRunIds.has(event.context.runId)) ||
			(event.context.delegationId !== null && relatedDelegationIds.has(event.context.delegationId)) ||
			(event.subject.type === "deliverable" && relatedDeliverableIds.has(event.subject.id)) ||
			(event.subject.type === "verification" && relatedVerificationIds.has(event.subject.id)) ||
			(event.eventType === "governance.task.accepted" &&
				typeof event.payload.verificationId === "string" &&
				relatedVerificationIds.has(event.payload.verificationId)),
	);
	return {
		ledgerSequence: state.events.at(-1)?.sequence ?? 0,
		run,
		delegation,
		ancestorRuns,
		descendantRuns,
		events: events.map(reference),
		sourceSequences: events.map((event) => event.sequence),
	};
}

export function queryEvents(state: GovernanceState, eventTypePrefix: string): GovernanceEvent[] {
	const prefix = state.events.some((event) => event.eventType.startsWith(eventTypePrefix))
		? eventTypePrefix
		: `governance.${eventTypePrefix}`;
	return state.events.filter((event) => event.eventType.startsWith(prefix));
}

export type ArchiveAuditRecord = {
	archiveId: string;
	archivedAt: string;
	actor: string;
	reason: string;
	boundary: number;
	counts: ProjectArchive["counts"];
	tasks: {
		taskId: string;
		revision: number;
		kind: "container" | "executable";
		goal: string;
		parentTaskId: string | null;
		won: boolean;
	}[];
	runs: { runId: string; taskId: string; state: Run["state"]; nativeRunId: string | null }[];
	deliverables: { deliverableId: string; taskId: string; commit: string }[];
	verifications: { verificationId: string; taskId: string; result: "passed" | "failed" }[];
	accepted: { taskId: string; verificationId: string }[];
	events: AuditEventReference[];
};

/**
 * Read-only view of archived work.
 *
 * Archived records are moved out of the current projection, so this is the only
 * place they can be read. Nothing here can be used to resume old work: the
 * archive is a record of what happened, and continuing it means creating a new
 * Task that references it.
 */
export function queryArchives(state: GovernanceState, archiveId?: string): ArchiveAuditRecord[] {
	return state.archiveOrder
		.filter((id) => archiveId === undefined || id === archiveId)
		.map((id) => state.archives[id])
		.filter((archive): archive is ProjectArchive => Boolean(archive))
		.map((archive) => {
			const taskIds = new Set(Object.keys(archive.records.tasks));
			const events = state.events.filter(
				(event) =>
					event.sequence <= archive.boundary &&
					((event.taskId !== null && taskIds.has(event.taskId)) ||
						(event.subject.type === "task" && taskIds.has(event.subject.id))),
			);
			return {
				archiveId: archive.archiveId,
				archivedAt: archive.archivedAt,
				actor: archive.actor,
				reason: archive.reason,
				boundary: archive.boundary,
				counts: archive.counts,
				tasks: Object.values(archive.records.tasks).map((task) => ({
					taskId: task.taskId,
					revision: task.revision,
					kind: task.kind ?? "executable",
					goal: task.goal,
					parentTaskId: task.parentTaskId ?? null,
					// Historical acceptance, as it stood when archived. Not a current
					// authorization: nothing archived can be executed.
					won: Boolean(archive.records.accepted[task.taskId]),
				})),
				runs: Object.values(archive.records.runs).map((run) => ({
					runId: run.runId,
					taskId: run.taskId,
					state: run.state,
					nativeRunId: run.nativeRunId,
				})),
				deliverables: Object.values(archive.records.deliverables).map((entry) => ({
					deliverableId: entry.deliverableId,
					taskId: entry.taskId,
					commit: entry.commit,
				})),
				verifications: Object.values(archive.records.verifications).map((entry) => ({
					verificationId: entry.verificationId,
					taskId: entry.taskId,
					result: entry.result,
				})),
				accepted: Object.entries(archive.records.accepted).map(([taskId, verificationId]) => ({
					taskId,
					verificationId,
				})),
				events: events.map(reference),
			};
		});
}
