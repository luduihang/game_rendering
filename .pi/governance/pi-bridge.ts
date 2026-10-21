import { randomUUID } from "node:crypto";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { GovernanceKernel } from "./kernel.ts";
import { dataRoot, GovernanceStore, primaryWorktree } from "./store.ts";
import type { Authority, Delegation, ProjectContract, TaskContract } from "./types.ts";
import { assertProjectDocumentsWritable, renderViews } from "./views.ts";
import { verifyTakeover } from "./workspace.ts";

const params = Type.Object({
	taskId: Type.String(),
	agent: Type.String(),
	objective: Type.String(),
	budgetTokens: Type.Integer({ minimum: 1 }),
	workspaceId: Type.Optional(Type.String()),
	parentRunId: Type.Optional(Type.String()),
	retryOf: Type.Optional(Type.String()),
	paths: Type.Array(Type.String()),
	tools: Type.Array(Type.String()),
	readRepository: Type.Boolean(),
	writeWorkspace: Type.Boolean(),
	commitBranch: Type.Boolean(),
	integrateBranch: Type.Boolean(),
});
const authoritySchema = Type.Object({
	paths: Type.Array(Type.String()),
	tools: Type.Array(Type.String()),
	readRepository: Type.Boolean(),
	writeWorkspace: Type.Boolean(),
	commitBranch: Type.Boolean(),
	integrateBranch: Type.Boolean(),
});
const projectSchema = Type.Object({
	projectId: Type.String(),
	revision: Type.Integer({ minimum: 1 }),
	name: Type.String(),
	goal: Type.String(),
	inScope: Type.Array(Type.String()),
	outOfScope: Type.Array(Type.String()),
	successCriteria: Type.Array(Type.String()),
	authority: authoritySchema,
	delegationPolicy: Type.Object({
		allowInternalTasks: Type.Boolean(),
		maxDepth: Type.Integer({ minimum: 0 }),
		maxConcurrent: Type.Integer({ minimum: 1 }),
	}),
	resourceLimits: Type.Object({ budgetTokens: Type.Integer({ minimum: 1 }) }),
	humanApprovalTriggers: Type.Array(Type.String()),
	prd: Type.String(),
	plan: Type.String(),
	changeReason: Type.String(),
});
const taskSchema = Type.Object({
	taskId: Type.String(),
	revision: Type.Integer({ minimum: 1 }),
	goal: Type.String(),
	scope: Type.Array(Type.String()),
	acceptance: Type.Array(Type.String()),
	owner: Type.String(),
	budgetTokens: Type.Integer({ minimum: 1 }),
	maxDepth: Type.Integer({ minimum: 0 }),
	maxConcurrent: Type.Integer({ minimum: 1 }),
	authority: authoritySchema,
	dependencies: Type.Array(Type.Object({ taskId: Type.String(), requiredState: Type.Literal("accepted") })),
});

type RpcReply =
	| { success: true; data: { details?: { runId?: string; asyncDir?: string }; text?: string } }
	| { success: false; error: { message: string } };

function isReply(value: unknown): value is RpcReply {
	return typeof value === "object" && value !== null && "success" in value;
}

function nativeRunId(value: unknown): string | null {
	if (typeof value !== "object" || value === null || !("runId" in value)) return null;
	return typeof value.runId === "string" ? value.runId : null;
}

export default function governanceBridge(pi: ExtensionAPI) {
	let currentTask: string | null = null;
	let currentSession: string | null = null;
	let currentProject: string | null = null;
	const pendingCompletions = new Map<string, unknown>();

	pi.on("session_start", (_event, ctx) => {
		pendingCompletions.clear();
		currentSession = ctx.sessionManager.getSessionId();
		currentProject = primaryWorktree(ctx.cwd);
		const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(currentProject)));
		const mainId = `pi-session:${currentSession}`;
		if (!kernel.getState().agents[mainId])
			kernel.registerAgent(
				{ agentId: mainId, harness: "pi", role: "coordinator", capabilities: ["task-orchestration", "delegation"] },
				mainId,
			);
		const activation = kernel
			.getState()
			.events.filter(
				(event) => event.type === "session.task-activated" && event.payload.sessionId === currentSession,
			)
			.at(-1);
		const taskId = activation?.taskId ?? null;
		currentTask =
			taskId && kernel.getState().approved[taskId] === kernel.getState().tasks[taskId]?.revision ? taskId : null;
	});
	pi.on("session_shutdown", () => {
		currentTask = null;
		currentSession = null;
		pendingCompletions.clear();
	});
	pi.on("tool_call", (event) => {
		if (!currentProject) return;
		const state = new GovernanceKernel(new GovernanceStore(dataRoot(currentProject))).getState();
		const initialized = state.events.some((entry) => entry.type === "project.initialized");
		if ((initialized || currentTask) && event.toolName === "subagent") {
			return {
				block: true,
				reason: "Governed projects use governance_delegate for formal child work.",
			};
		}
		if (initialized && state.projectStatus !== "ACTIVE" && ["bash", "write", "edit"].includes(event.toolName))
			return { block: true, reason: "Project baseline is not active; use read tools and governance_project_draft." };
	});
	pi.on("before_agent_start", (_event, ctx) => {
		const state = new GovernanceKernel(new GovernanceStore(dataRoot(ctx.cwd))).getState();
		if (!state.events.some((entry) => entry.type === "project.initialized")) return;
		const projectId = state.events.find((entry) => entry.type === "project.initialized")?.payload.projectId;
		return {
			message: {
				customType: "governance-project-context",
				display: false,
				content:
					state.projectApproved && state.projectStatus === "ACTIVE"
						? `Project ID ${projectId}. Project baseline r${state.projectApproved.revision} is active. Use governance_task_create for ordinary internal tasks, governance_delegate for child runs, and governance_project_draft for changes. Exact inScope entries and authority ceilings govern automatic tasks. Do not treat a PRD edit as approval. Read management/PROJECT.md and management/NOW.md for state.`
						: `Project ID ${projectId}. Project baseline is ${state.projectStatus}. Discuss goals, scope, exclusions, constraints, resources and success criteria with the user. Use governance_project_draft to record PRD, contract and plan. Formal writable work and child delegation require local human approval via project approve. Read management/PROJECT.md and management/INBOX.md.`,
			},
		};
	});

	pi.registerTool({
		name: "governance_project_draft",
		label: "Draft project baseline",
		description: "Record a new immutable project contract revision, PRD and plan. This never approves the project.",
		parameters: projectSchema,
		async execute(_id, input, _signal, _update, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			try {
				assertProjectDocumentsWritable(project);
				kernel.submitProjectDraft(input as ProjectContract, `pi:${ctx.sessionManager.getSessionId()}`);
				renderViews(project, kernel);
				return {
					content: [
						{
							type: "text",
							text: `Project revision ${input.revision} drafted. Human must run: node .pi/governance/cli.ts project approve ${input.revision}`,
						},
					],
					details: {},
				};
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
		},
	});
	pi.registerTool({
		name: "governance_task_create",
		label: "Create project task",
		description:
			"Create an internal task under the approved project baseline. Exact scope entries, permissions and budget are checked.",
		parameters: taskSchema,
		async execute(_id, input, _signal, _update, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			try {
				kernel.submitTask(input as TaskContract, `pi:${ctx.sessionManager.getSessionId()}`, true);
				renderViews(project, kernel);
				return {
					content: [{ type: "text", text: `Task ${input.taskId} authorized under project baseline` }],
					details: {},
				};
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
		},
	});
	const onCompletion = (payload: unknown) => {
		if (!currentProject) return;
		const native = nativeRunId(payload);
		if (!native) return;
		const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(currentProject)));
		const run = Object.values(kernel.getState().runs).find((item) => item.nativeRunId === native);
		if (!run) {
			pendingCompletions.set(native, payload);
			if (pendingCompletions.size > 100) pendingCompletions.delete(pendingCompletions.keys().next().value ?? native);
			return;
		}
		if (run.state !== "RUNNING") return;
		const record = payload as { success?: unknown; state?: unknown; results?: { sessionPath?: unknown }[] };
		const next = record.success === true ? "SUCCEEDED" : record.state === "paused" ? "PAUSED" : "FAILED";
		try {
			const childSession = record.results?.find((entry) => typeof entry.sessionPath === "string")?.sessionPath;
			kernel.updateRun(run.runId, next, { sessionRef: typeof childSession === "string" ? childSession : null });
			if (next !== "PAUSED" && run.workspaceId)
				kernel.releaseWorkspace(run.workspaceId, run.runId, "pi-subagents", `async-complete:${native}`);
			renderViews(currentProject, kernel);
		} catch (error) {
			console.error("Governance completion reconciliation failed:", error);
		}
	};
	pi.events.on("subagent:async-complete", onCompletion);

	pi.registerTool({
		name: "governance_delegate",
		label: "Governed delegation",
		description: "Start an approved task's child Agent through the governed Pi subagent entry point.",
		parameters: params,
		async execute(_toolCallId, input, signal, _onUpdate, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			const authority: Authority = {
				paths: input.paths,
				tools: input.tools,
				readRepository: input.readRepository,
				writeWorkspace: input.writeWorkspace,
				commitBranch: input.commitBranch,
				integrateBranch: input.integrateBranch,
			};
			if (currentTask !== input.taskId) {
				kernel.store.append({
					type: "session.task-activated",
					actor: `pi:${ctx.sessionManager.getSessionId()}`,
					taskId: input.taskId,
					runId: null,
					delegationId: null,
					payload: { sessionId: ctx.sessionManager.getSessionId() },
				});
				currentTask = input.taskId;
			}
			const workspace = input.workspaceId ? kernel.getState().workspaces[input.workspaceId] : undefined;
			if (input.writeWorkspace && !workspace)
				return {
					content: [{ type: "text", text: "Writable delegation requires a registered workspaceId" }],
					isError: true,
					details: {},
				};
			if (workspace) verifyTakeover(workspace, kernel);
			if (!kernel.getState().agents[input.agent])
				kernel.registerAgent(
					{ agentId: input.agent, harness: "pi", role: "executor", capabilities: ["delegated-work"] },
					`pi:${ctx.sessionManager.getSessionId()}`,
				);
			kernel.store.append({
				type: "delegation.requested",
				actor: `pi:${ctx.sessionManager.getSessionId()}`,
				taskId: input.taskId,
				runId: input.parentRunId ?? null,
				delegationId: null,
				payload: { agent: input.agent, objective: input.objective, retryOf: input.retryOf ?? null },
			});
			let delegation: Delegation;
			try {
				if (input.retryOf) {
					const prior = kernel.getState().runs[input.retryOf];
					const previous = prior && kernel.getState().delegations[prior.delegationId];
					if (
						!previous ||
						prior.taskId !== input.taskId ||
						previous.executorId !== input.agent ||
						JSON.stringify(previous.authority) !== JSON.stringify(authority) ||
						previous.budgetTokens !== input.budgetTokens
					)
						throw new Error("Retry must reuse the same delegation contract");
					delegation = previous;
				} else {
					delegation = kernel.authorizeDelegation(
						{
							taskId: input.taskId,
							parentRunId: input.parentRunId ?? null,
							executorId: input.agent,
							objective: input.objective,
							authority,
							budgetTokens: input.budgetTokens,
						},
						`pi:${ctx.sessionManager.getSessionId()}`,
					);
				}
			} catch (error) {
				kernel.store.append({
					type: "delegation.rejected",
					actor: `pi:${ctx.sessionManager.getSessionId()}`,
					taskId: input.taskId,
					runId: input.parentRunId ?? null,
					delegationId: null,
					payload: { reason: error instanceof Error ? error.message : String(error), agent: input.agent },
				});
				if (kernel.getState().tasks[input.taskId])
					kernel.requestDecision(
						input.taskId,
						"scope",
						`Review rejected delegation to ${input.agent}: ${error instanceof Error ? error.message : String(error)}`,
						`pi:${ctx.sessionManager.getSessionId()}`,
					);
				return {
					content: [
						{
							type: "text",
							text: `Delegation denied: ${error instanceof Error ? error.message : String(error)}`,
						},
					],
					isError: true,
					details: {},
				};
			}
			const run = kernel.createRun(
				delegation.delegationId,
				"pi",
				null,
				workspace?.workspaceId ?? null,
				input.retryOf ?? null,
				ctx.sessionManager.getSessionFile() ?? null,
			);
			try {
				if (workspace)
					kernel.leaseWorkspace(
						workspace.workspaceId,
						run.runId,
						new Date(Date.now() + 60 * 60_000).toISOString(),
					);
			} catch (error) {
				kernel.updateRun(run.runId, "FAILED", {}, "workspace admission failed");
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			}
			const requestId = randomUUID();
			const replyEvent = `subagents:rpc:v1:reply:${requestId}`;
			let unsubscribe: (() => void) | undefined;
			let timer: ReturnType<typeof setTimeout> | undefined;
			const reply = new Promise<RpcReply>((resolve, reject) => {
				unsubscribe = pi.events.on(replyEvent, (value) => {
					if (isReply(value)) resolve(value);
				});
				timer = setTimeout(
					() => reject(new Error("Pi subagent RPC reply timeout; do not retry until reconciled")),
					30_000,
				);
				signal?.addEventListener(
					"abort",
					() => reject(new Error("Governed launch interrupted; reconcile native run before retry")),
					{ once: true },
				);
			});
			pi.events.emit("subagents:rpc:v1:request", {
				version: 1,
				requestId,
				method: "spawn",
				params: {
					agent: input.agent,
					task: input.objective,
					context: "fresh",
					cwd: workspace?.path ?? project,
					async: true,
					worktree: false,
				},
				source: { extension: "agent-governance-v0.1" },
			});
			let explicitFailure = false;
			try {
				const response = await reply;
				if (!response.success) {
					explicitFailure = true;
					throw new Error(response.error.message);
				}
				const native = response.data.details?.runId;
				if (!native) throw new Error("Pi spawn reply lacks native Run ID; reconcile before retry");
				kernel.updateRun(run.runId, "RUNNING", { nativeRunId: native });
				const earlyCompletion = pendingCompletions.get(native);
				if (earlyCompletion) {
					pendingCompletions.delete(native);
					onCompletion(earlyCompletion);
				}
				renderViews(project, kernel);
				return {
					content: [
						{
							type: "text",
							text: `Governance Run ${run.runId}; Pi Run ${native}; workspace ${workspace?.path ?? "read-only"}`,
						},
					],
					details: { runId: run.runId, nativeRunId: native, delegationId: delegation.delegationId },
				};
			} catch (error) {
				if (kernel.getState().runs[run.runId]?.state === "CREATED") {
					kernel.updateRun(run.runId, explicitFailure ? "FAILED" : "INTERRUPTED");
					if (explicitFailure && workspace)
						kernel.releaseWorkspace(
							workspace.workspaceId,
							run.runId,
							"pi-subagents",
							"RPC spawn rejected before launch",
						);
				}
				renderViews(project, kernel);
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			} finally {
				unsubscribe?.();
				if (timer) clearTimeout(timer);
			}
		},
	});

	pi.registerTool({
		name: "governance_control",
		label: "Governed Run control",
		description: "Query, interrupt, stop, or resume a governed Pi Run. Acknowledgement is not terminal proof.",
		parameters: Type.Object({
			runId: Type.String(),
			action: Type.Union([
				Type.Literal("status"),
				Type.Literal("interrupt"),
				Type.Literal("stop"),
				Type.Literal("resume"),
			]),
			message: Type.Optional(Type.String()),
		}),
		async execute(_toolCallId, input, signal, _onUpdate, ctx) {
			const project = primaryWorktree(ctx.cwd);
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(project)));
			const run = kernel.getState().runs[input.runId];
			if (!run?.nativeRunId)
				return {
					content: [{ type: "text", text: "Governed Run has no known native Pi Run ID" }],
					isError: true,
					details: {},
				};
			if (input.action === "resume" && !input.message?.trim())
				return { content: [{ type: "text", text: "Resume requires a message" }], isError: true, details: {} };
			if (input.action !== "status")
				kernel.controlRun(
					input.runId,
					input.action === "interrupt" ? "pause" : input.action === "stop" ? "cancel" : "resume",
					`pi:${ctx.sessionManager.getSessionId()}`,
				);
			const requestId = randomUUID();
			const replyEvent = `subagents:rpc:v1:reply:${requestId}`;
			let unsubscribe: (() => void) | undefined;
			let timer: ReturnType<typeof setTimeout> | undefined;
			const reply = new Promise<RpcReply>((resolve, reject) => {
				unsubscribe = pi.events.on(replyEvent, (value) => {
					if (isReply(value)) resolve(value);
				});
				timer = setTimeout(() => reject(new Error("Pi control RPC reply timeout")), 30_000);
				signal?.addEventListener("abort", () => reject(new Error("Pi control RPC interrupted")), { once: true });
			});
			pi.events.emit("subagents:rpc:v1:request", {
				version: 1,
				requestId,
				method: input.action,
				params: { id: run.nativeRunId, ...(input.message ? { message: input.message } : {}) },
				source: { extension: "agent-governance-v0.1" },
			});
			try {
				const response = await reply;
				if (!response.success) throw new Error(response.error.message);
				if (input.action === "resume") {
					const resumedNative = response.data.details?.runId;
					if (!resumedNative)
						throw new Error(
							"Resume acknowledgement lacks native Run ID; reconcile before another control action",
						);
					kernel.updateRun(run.runId, "RUNNING", { nativeRunId: resumedNative });
					renderViews(project, kernel);
				}
				return {
					content: [
						{ type: "text", text: response.data.text ?? JSON.stringify(response.data.details ?? response.data) },
					],
					details: { acknowledged: true, nativeRunId: run.nativeRunId },
				};
			} catch (error) {
				return {
					content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }],
					isError: true,
					details: {},
				};
			} finally {
				unsubscribe?.();
				if (timer) clearTimeout(timer);
			}
		},
	});

	pi.registerTool({
		name: "governance_state",
		label: "Governance state",
		description: "Read approved tasks, Run states, workspaces, pending decisions, and verification records.",
		parameters: Type.Object({}),
		async execute(_toolCallId, _input, _signal, _onUpdate, ctx) {
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(ctx.cwd)));
			const state = kernel.getState();
			return {
				content: [
					{
						type: "text",
						text: JSON.stringify(
							{
								agents: state.agents,
								projectDraft: state.projectDraft,
								projectApproved: state.projectApproved,
								projectStatus: state.projectStatus,
								tasks: state.tasks,
								approved: state.approved,
								runs: state.runs,
								delegations: state.delegations,
								workspaces: state.workspaces,
								pendingDecisions: Object.values(state.decisions).filter(
									(decision) => decision.result === "pending",
								),
								deliverables: state.deliverables,
								verifications: state.verifications,
								accepted: state.accepted,
							},
							null,
							2,
						),
					},
				],
				details: {},
			};
		},
	});

	pi.registerCommand("gov-task", {
		description: "Activate an approved governed task in this Pi session: /gov-task <task-id>",
		handler: async (taskId, ctx) => {
			const kernel = new GovernanceKernel(new GovernanceStore(dataRoot(ctx.cwd)));
			const task = kernel.getState().tasks[taskId.trim()];
			if (!task || kernel.getState().approved[task.taskId] !== task.revision)
				throw new Error("Task is not approved");
			currentTask = task.taskId;
			currentSession = ctx.sessionManager.getSessionId();
			kernel.store.append({
				type: "session.task-activated",
				actor: `pi:${currentSession}`,
				taskId: task.taskId,
				runId: null,
				delegationId: null,
				payload: { sessionId: currentSession },
			});
			ctx.ui.notify(`Governed task active: ${currentTask}`, "info");
		},
	});
}
