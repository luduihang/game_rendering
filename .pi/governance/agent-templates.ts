// Agent definition files written for a new project.
//
// The V3 policy names roles, and `.pi/settings.json` carries their tool overrides,
// but pi-subagents discovers agents from markdown files. A policy that names a
// role with no definition is silently useless: the override is stored, the role
// never appears, and delegation fails with "not allowed by project subagent
// policy". Writing the definitions together with the policy is what makes the
// template a working starting point instead of a trap.
//
// Frontmatter must start at byte zero. A leading blank line makes
// `parseFrontmatter` return nothing, and pi-subagents skips such a file without
// recording a diagnostic — the failure that cost the most time to find.
import * as fs from "node:fs";
import * as path from "node:path";

export type AgentTemplate = {
	id: string;
	description: string;
	/** When Main should pick this role; shown to the model in the routing hint. */
	useFor: string;
	tools: string[];
	/** Reasoning effort for this role; `medium` unless a role has a measured reason otherwise. */
	thinking?: string;
	/**
	 * What this role is allowed to do, recorded in the ledger when it registers.
	 *
	 * Was missing entirely: every subagent registered as `role: "executor"` with
	 * `capabilities: ["delegated-work"]` regardless of which role it was, so the ledger
	 * could not answer "may this Run verify a delivery". Deriving it from the template is
	 * what makes the answer checkable instead of inferred from a name.
	 */
	capabilities: string[];
	maxConcurrent: number;
	maxAllocationTokens: number;
	timeoutMs: number;
	body: string;
};

const READER_BODY = `你是当前项目的只读代码调查专家。

职责：
1. 阅读和理解现有代码，定位文件、符号与调用关系。
2. 调查 Bug 的可能原因，给出具体文件路径与行号。
3. 向 Main Agent 提交清晰的调查报告。

原则：
- 不修改任何代码，不创建、删除或覆盖文件。
- 不提交 Git Commit，不自行扩大任务范围。
- 不发起子 Agent 委派（当前只允许 Main → Child 一层）。
- 结论必须有代码证据；无法确认时明确标 UNKNOWN。

输出格式：调查目标 / 涉及文件 / 关键代码位置 / 调用关系 / 发现的问题 / 结论与建议。
`;

const WORKER_BODY = `你是当前项目的实现工人，在 Main Agent 给定范围内完成编码工作。

职责：
1. 按任务契约完成指定改动，只碰授权路径。
2. 自测改动，报告实际执行的命令与结果。
3. 交付时说明改了什么、为什么、如何验证。

原则：
- 不超出任务范围，不顺手重构无关代码。
- 不发起子 Agent 委派。
- 测试没跑就说没跑，不要声称通过。
- 遇到需要扩大权限或范围时停下来，交回 Main Agent。

输出格式：改动摘要 / 涉及文件 / 验证方式与结果 / 未完成或风险项。
`;

const REVIEWER_BODY = `你是独立审核者，核对别人的产物与证据，不替实现者补写。

职责：
1. 逐条核对任务验收条件，对照交付证据（Git 提交、文件清单、测试输出）。
2. 判断是否达标；不达标要指出具体返工点。
3. 区分「声明」与「已核验」：没有日志或证据的一律标未核验。

原则：
- 不修改代码，不修复实现者的工作。
- 不因为实现者说完成就认为完成。
- 不发起子 Agent 委派。

输出格式：验收条件逐条结论 / 证据 / 返工点 / 总体结论（通过 / 不通过 / 证据不足）。
`;

/**
 * Roles written by `gov init`, matching `INITIAL_SUBAGENT_POLICY`.
 *
 * `tools` duplicates the policy on purpose: the policy decides what the child may
 * use, and the definition is what pi-subagents actually launches. They must agree,
 * or the terminal check reports a configuration mismatch.
 */
export const AGENT_TEMPLATES: AgentTemplate[] = [
	{
		id: "reader",
		description: "只读代码调查：定位文件、检索符号、分析调用链",
		useFor: "代码阅读、文件定位、代码搜索、调用链分析、架构调查、Bug 原因分析",
		tools: ["read", "grep", "find", "ls"],
		// Reads and reports. Cannot verify: verification is a judgement about a delivery,
		// and a role whose job is to read code has no standing to pass one.
		capabilities: ["investigate"],
		maxConcurrent: 5,
		maxAllocationTokens: 30000,
		timeoutMs: 900000,
		body: READER_BODY,
	},
	{
		id: "worker",
		description: "范围明确的实现工作，在独立工作区完成改动与测试",
		useFor: "已界定边界的编码、重构、补测试",
		tools: ["read", "grep", "find", "ls", "edit", "write", "bash"],
		// Implements. Deliberately without `verify`: an implementer checking its own
		// delivery is the case the reviewer role exists to keep separate.
		capabilities: ["implement"],
		// Two so an implementation can proceed alongside a second one in its own
		// worktree. It stays a small number: each worker can write, and the point of
		// the ceiling is to keep their file boundaries reviewable.
		maxConcurrent: 2,
		maxAllocationTokens: 120000,
		timeoutMs: 1800000,
		body: WORKER_BODY,
	},
	{
		id: "reviewer",
		description: "独立审核与验证，不替 worker 补写",
		useFor: "核对产物与证据、复核交付、指出返工点",
		tools: ["read", "grep", "find", "ls"],
		// Read-only and never the implementer: the one role that may verify a delivery.
		capabilities: ["investigate", "verify"],
		maxConcurrent: 1,
		maxAllocationTokens: 60000,
		timeoutMs: 900000,
		body: REVIEWER_BODY,
	},
];

/**
 * What the named role may do, taken from its template.
 *
 * Returns `null` for a role with no template, which the caller must treat as "no
 * capabilities" rather than "no restrictions". An unknown role is not a trusted one.
 */
export function capabilitiesOf(id: string, templates: AgentTemplate[] = AGENT_TEMPLATES): string[] | null {
	const template = templates.find((entry) => entry.id === id);
	return template ? [...template.capabilities] : null;
}

export function agentDefinitionPath(project: string, id: string): string {
	return path.join(project, ".pi", "agents", `${id}.md`);
}

/** Render one definition. Frontmatter starts at byte zero; see the header note. */
/** Thinking level for roles that do not state one. */
export const DEFAULT_AGENT_THINKING = "medium";

export function renderAgentDefinition(template: AgentTemplate): string {
	return [
		"---",
		`name: ${template.id}`,
		`description: ${template.description}`,
		`tools: ${template.tools.join(", ")}`,
		// Pinned rather than inherited. Without it the child takes the operator's global
		// level, which on a reasoning model defaults to `high` and spends most of its output
		// budget thinking: an observed reader sat in one turn for minutes producing a single
		// long trace. `medium` is the level these roles were measured at.
		`thinking: ${template.thinking ?? DEFAULT_AGENT_THINKING}`,
		"---",
		"",
		template.body,
	].join("\n");
}

/**
 * Write the definitions that are missing. An existing file is never replaced:
 * the operator's prompt edits are theirs, and the policy still constrains tools.
 */
export function writeAgentDefinitions(project: string, templates: AgentTemplate[] = AGENT_TEMPLATES): string[] {
	const written: string[] = [];
	for (const template of templates) {
		const file = agentDefinitionPath(project, template.id);
		if (fs.existsSync(file)) continue;
		fs.mkdirSync(path.dirname(file), { recursive: true });
		fs.writeFileSync(file, renderAgentDefinition(template), { flag: "wx" });
		written.push(file);
	}
	return written;
}

/**
 * Add a missing thinking level to an existing agent definition.
 *
 * `writeAgentDefinitions` never touches a file that exists, because the operator's prompt
 * edits are theirs. That rule leaves a real gap here: definitions written before the level
 * was pinned have none, so the child inherits the global default - `high` on a reasoning
 * model, which spends most of its output budget thinking. Only the one key is added and
 * only when absent, so a prompt edit is never touched and a deliberate override survives.
 */
export function backfillAgentThinking(project: string, templates: AgentTemplate[] = AGENT_TEMPLATES): string[] {
	const updated: string[] = [];
	for (const template of templates) {
		const file = agentDefinitionPath(project, template.id);
		if (!fs.existsSync(file)) continue;
		const body = fs.readFileSync(file, "utf8");
		if (/^thinking\s*:/m.test(body)) continue;
		const closed = /^---\s*$/m.exec(body.slice(4));
		if (!closed) continue; // no frontmatter to extend
		const at = 4 + closed.index;
		const level = template.thinking ?? DEFAULT_AGENT_THINKING;
		fs.writeFileSync(file, `${body.slice(0, at)}thinking: ${level}\n${body.slice(at)}`);
		updated.push(file);
	}
	return updated;
}
