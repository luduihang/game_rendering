import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import type { GovernanceEvent, GovernanceState } from "./types.ts";

export function dataRoot(repo: string): string {
	const common = execFileSync("git", ["rev-parse", "--path-format=absolute", "--git-common-dir"], {
		cwd: repo,
		encoding: "utf8",
	}).trim();
	return path.join(common, "agent-governance-v0.1");
}

export function primaryWorktree(repo: string): string {
	const listing = execFileSync("git", ["worktree", "list", "--porcelain"], { cwd: repo, encoding: "utf8" });
	const first = listing.split("\n").find((line) => line.startsWith("worktree "));
	if (!first) throw new Error("No primary Git worktree found");
	return first.slice("worktree ".length);
}

export function emptyState(): GovernanceState {
	return {
		projectDraft: null,
		projectApproved: null,
		projectRejectedRevision: null,
		projectStatus: "DRAFT",
		agents: {},
		tasks: {},
		approved: {},
		delegations: {},
		runs: {},
		workspaces: {},
		decisions: {},
		deliverables: {},
		verifications: {},
		accepted: {},
		events: [],
	};
}

export function fold(state: GovernanceState, event: GovernanceEvent): void {
	const value = event.payload.value;
	switch (event.type) {
		case "project.drafted":
			state.projectDraft = value as GovernanceState["projectDraft"];
			state.projectRejectedRevision = null;
			break;
		case "project.approved":
			state.projectApproved = value as GovernanceState["projectApproved"];
			state.projectRejectedRevision = null;
			state.projectStatus = "ACTIVE";
			break;
		case "project.rejected":
			state.projectRejectedRevision = Number(event.payload.revision);
			break;
		case "project.paused":
			state.projectStatus = "PAUSED";
			break;
		case "project.revoked":
			state.projectStatus = "REVOKED";
			break;
		case "project.resumed":
			state.projectStatus = "ACTIVE";
			break;
		case "agent.registered": {
			const agent = value as GovernanceState["agents"][string];
			state.agents[agent.agentId] = agent;
			break;
		}
		case "task.created":
		case "task.revised": {
			const task = value as GovernanceState["tasks"][string];
			state.tasks[task.taskId] = task;
			delete state.accepted[task.taskId];
			if (event.payload.autoApproved === true) state.approved[task.taskId] = task.revision;
			break;
		}
		case "task.approved":
		case "task.auto-approved":
			state.approved[event.taskId ?? ""] = Number(event.payload.revision);
			break;
		case "delegation.authorized": {
			const delegation = value as GovernanceState["delegations"][string];
			state.delegations[delegation.delegationId] = delegation;
			break;
		}
		case "run.created": {
			const run = value as GovernanceState["runs"][string];
			state.runs[run.runId] = run;
			break;
		}
		case "run.updated": {
			const run = value as GovernanceState["runs"][string];
			state.runs[run.runId] = run;
			break;
		}
		case "run.started":
		case "run.paused":
		case "run.resumed":
		case "run.interrupted":
		case "run.failed":
		case "run.finished":
		case "run.cancelled": {
			const run = value as GovernanceState["runs"][string];
			state.runs[run.runId] = run;
			break;
		}
		case "workspace.registered":
		case "workspace.updated": {
			const workspace = value as GovernanceState["workspaces"][string];
			state.workspaces[workspace.workspaceId] = workspace;
			break;
		}
		case "decision.requested":
		case "decision.recorded": {
			const decision = value as GovernanceState["decisions"][string];
			state.decisions[decision.decisionId] = decision;
			break;
		}
		case "deliverable.submitted": {
			const deliverable = value as GovernanceState["deliverables"][string];
			state.deliverables[deliverable.deliverableId] = deliverable;
			delete state.accepted[deliverable.taskId];
			break;
		}
		case "verification.recorded": {
			const verification = value as GovernanceState["verifications"][string];
			state.verifications[verification.verificationId] = verification;
			break;
		}
		case "task.accepted":
			state.accepted[event.taskId ?? ""] = String(event.payload.verificationId);
			state.decisions[event.eventId] = {
				decisionId: event.eventId,
				taskId: event.taskId ?? "",
				revision: Number(event.payload.revision),
				kind: "acceptance",
				request: "Accept verified deliverable",
				requester: "governance",
				result: "approved",
				actor: event.actor,
				scope: String(event.payload.commit),
				expiresAt: null,
				evidence: [String(event.payload.verificationId)],
			};
			break;
	}
	state.events.push(event);
}

function readEvents(file: string, recover: boolean): GovernanceEvent[] {
	if (!fs.existsSync(file)) return [];
	const raw = fs.readFileSync(file, "utf8");
	if (raw.length === 0) return [];
	const lastNewline = raw.lastIndexOf("\n");
	if (lastNewline !== raw.length - 1) {
		if (!recover) throw new Error("Governance log has an incomplete tail; writer recovery required");
		const tail = raw.slice(lastNewline + 1);
		const backup = `${file}.partial-${Date.now()}`;
		fs.writeFileSync(backup, tail, { flag: "wx", mode: 0o600 });
		fs.truncateSync(file, Buffer.byteLength(raw.slice(0, lastNewline + 1)));
	}
	const complete = raw.slice(0, lastNewline + 1).trim();
	if (!complete) return [];
	const events = complete.split("\n").map((line) => JSON.parse(line) as GovernanceEvent);
	let expected = 1;
	const ids = new Set<string>();
	for (const event of events) {
		if (
			!event ||
			typeof event !== "object" ||
			typeof event.eventId !== "string" ||
			typeof event.type !== "string" ||
			!event.type.trim() ||
			typeof event.actor !== "string" ||
			!event.actor.trim() ||
			typeof event.time !== "string" ||
			!Number.isFinite(Date.parse(event.time)) ||
			!event.payload ||
			typeof event.payload !== "object" ||
			Array.isArray(event.payload) ||
			![event.taskId, event.runId, event.delegationId].every((value) => value === null || typeof value === "string")
		)
			throw new Error("Governance event schema is corrupt");
		if (event.sequence !== expected++ || ids.has(event.eventId))
			throw new Error("Governance log sequence or ID is corrupt");
		ids.add(event.eventId);
	}
	return events;
}

export class GovernanceStore {
	readonly root: string;
	constructor(root: string) {
		this.root = root;
	}

	read(): GovernanceState {
		const state = emptyState();
		for (const event of readEvents(path.join(this.root, "events.jsonl"), false)) fold(state, event);
		return state;
	}

	append(
		input: Omit<GovernanceEvent, "eventId" | "sequence" | "time">,
		check?: (state: GovernanceState) => void,
	): GovernanceEvent {
		fs.mkdirSync(this.root, { recursive: true, mode: 0o700 });
		const lock = path.join(this.root, "writer.lock");
		try {
			fs.mkdirSync(lock);
		} catch (error) {
			if (fs.existsSync(lock) && Date.now() - fs.statSync(lock).mtimeMs > 30_000) {
				const owner = path.join(lock, "owner");
				const pid = fs.existsSync(owner) ? Number(fs.readFileSync(owner, "utf8").split("\n")[0]) : NaN;
				let alive = false;
				if (Number.isSafeInteger(pid) && pid > 0) {
					try {
						process.kill(pid, 0);
						alive = true;
					} catch {
						alive = false;
					}
				}
				if (!alive) throw new Error(`Stale governance writer lock requires operator inspection: ${lock}`);
			}
			throw new Error(`Governance writer busy: ${lock}`, { cause: error });
		}
		try {
			fs.writeFileSync(path.join(lock, "owner"), `${process.pid}\n${Date.now()}\n`, { mode: 0o600 });
			const state = emptyState();
			for (const event of readEvents(path.join(this.root, "events.jsonl"), true)) fold(state, event);
			check?.(state);
			const event: GovernanceEvent = {
				...input,
				eventId: randomUUID(),
				sequence: state.events.length + 1,
				time: new Date().toISOString(),
			};
			const fd = fs.openSync(path.join(this.root, "events.jsonl"), "a", 0o600);
			try {
				const bytes = Buffer.from(`${JSON.stringify(event)}\n`);
				let offset = 0;
				while (offset < bytes.length) offset += fs.writeSync(fd, bytes, offset, bytes.length - offset);
				fs.fsyncSync(fd);
			} finally {
				fs.closeSync(fd);
			}
			return event;
		} finally {
			fs.rmSync(lock, { recursive: true });
		}
	}

	restore(source: string): void {
		readEvents(source, false);
		fs.mkdirSync(this.root, { recursive: true, mode: 0o700 });
		const lock = path.join(this.root, "writer.lock");
		fs.mkdirSync(lock);
		try {
			fs.copyFileSync(source, path.join(this.root, "events.jsonl"), fs.constants.COPYFILE_EXCL);
		} finally {
			fs.rmSync(lock, { recursive: true });
		}
	}

	backup(destination: string): void {
		const lock = path.join(this.root, "writer.lock");
		fs.mkdirSync(lock);
		try {
			const source = path.join(this.root, "events.jsonl");
			readEvents(source, false);
			fs.copyFileSync(source, destination, fs.constants.COPYFILE_EXCL);
			const fd = fs.openSync(destination, "r");
			try {
				fs.fsyncSync(fd);
			} finally {
				fs.closeSync(fd);
			}
		} finally {
			fs.rmSync(lock, { recursive: true });
		}
	}
}
