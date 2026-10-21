import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { GovernanceKernel } from "./kernel.ts";
import { dataRoot, GovernanceStore, primaryWorktree } from "./store.ts";
import type { ProjectContract, TaskContract, Verification } from "./types.ts";
import { assertProjectDocumentsWritable, renderViews } from "./views.ts";
import { createWorkspace, inspectWorkspace, verifyTakeover } from "./workspace.ts";

const project = primaryWorktree(execFileSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" }).trim());
const store = new GovernanceStore(dataRoot(project));
const kernel = new GovernanceKernel(store);
const actor = `local:${os.userInfo().username}`;
const [command, action, ...args] = process.argv.slice(2);

function required(value: string | undefined, label: string): string {
	if (!value) throw new Error(`${label} is required`);
	return value;
}

function jsonFile<T>(file: string): T {
	return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

try {
	let output: unknown;
	if (command === "project" && action === "draft") {
		assertProjectDocumentsWritable(project);
		kernel.submitProjectDraft(jsonFile<ProjectContract>(required(args[0], "project contract file")), actor);
		output = "Project draft recorded; human approval pending";
	} else if (command === "project" && action === "approve") {
		kernel.approveProject(Number(required(args[0], "project revision")), actor);
		output = "Project baseline approved";
	} else if (command === "project" && action === "reject") {
		kernel.rejectProject(Number(required(args[0], "project revision")), actor, required(args[1], "rejection reason"));
		output = "Project draft rejected; prior approved baseline remains active";
	} else if (command === "project" && (action === "pause" || action === "resume" || action === "revoke")) {
		kernel.controlProject(action, actor);
		output = `Project ${action} recorded`;
	} else if (command === "task" && (action === "create" || action === "create-internal")) {
		kernel.submitTask(
			jsonFile<TaskContract>(required(args[0], "contract file")),
			actor,
			action === "create-internal",
		);
		output =
			action === "create-internal"
				? "Internal task authorized by project baseline"
				: "Task created; approval is pending";
	} else if (command === "decision" && (action === "approve" || action === "reject")) {
		output = kernel.recordDecision(
			required(args[0], "decision ID"),
			action === "approve" ? "approved" : "rejected",
			actor,
			required(args[1], "scope"),
			args[2] ?? null,
			[],
		);
	} else if (command === "task" && action === "approve") {
		kernel.approveTask(required(args[0], "task ID"), required(args[1], "decision ID"), actor);
		output = "Task revision approved";
	} else if (command === "workspace" && action === "create") {
		output = createWorkspace(project, required(args[0], "task ID"), kernel);
	} else if (command === "workspace" && action === "inspect") {
		const workspace = kernel.getState().workspaces[required(args[0], "workspace ID")];
		if (!workspace) throw new Error("Unknown workspace");
		output = inspectWorkspace(workspace);
	} else if (command === "workspace" && action === "takeover") {
		const workspace = kernel.getState().workspaces[required(args[0], "workspace ID")];
		if (!workspace) throw new Error("Unknown workspace");
		output = verifyTakeover(workspace, kernel);
	} else if (command === "workspace" && action === "release") {
		kernel.releaseWorkspace(
			required(args[0], "workspace ID"),
			required(args[1], "run ID"),
			actor,
			required(args[2], "terminal proof"),
		);
		output = "Workspace released";
	} else if (command === "run" && action === "state") {
		const next = required(args[1], "state");
		if (next !== "FAILED" && next !== "CANCELLED")
			throw new Error("Manual Run correction supports only FAILED or CANCELLED");
		const proof = required(args[2], "terminal proof");
		output = kernel.updateRun(required(args[0], "run ID"), next, {}, proof);
	} else if (command === "deliverable" && action === "submit") {
		output = kernel.submitDeliverable(jsonFile(required(args[0], "deliverable file")));
	} else if (command === "verification" && action === "record") {
		const input = jsonFile<{ deliverableId: string; criteria: Verification["criteria"] }>(
			required(args[0], "verification file"),
		);
		output = kernel.recordVerification(input.deliverableId, actor, input.criteria);
	} else if (command === "task" && action === "accept") {
		kernel.acceptTask(required(args[0], "task ID"), required(args[1], "verification ID"), actor);
		output = "Task accepted";
	} else if (command === "views" && action === "render") {
		output = "Views rendered";
	} else if (command === "state" && action === "show") {
		output = kernel.getState();
	} else if (command === "backup" && action === "export") {
		const destination = path.resolve(required(args[0], "destination"));
		store.backup(destination);
		output = destination;
	} else if (command === "backup" && action === "restore") {
		store.restore(path.resolve(required(args[0], "backup file")));
		output = "Governance log restored into an empty data root";
	} else {
		throw new Error(
			"Usage: project draft|approve|reject|pause|resume|revoke, task create|create-internal|approve|accept, decision approve|reject, workspace create|inspect|takeover|release, run state, deliverable submit, verification record, views render, state show, backup export|restore",
		);
	}
	if (command !== "state" && command !== "backup") renderViews(project, kernel);
	process.stdout.write(`${typeof output === "string" ? output : JSON.stringify(output, null, 2)}\n`);
} catch (error) {
	process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
	process.exitCode = 1;
}
