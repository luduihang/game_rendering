import { createHash } from "node:crypto";
import type {
	ApprovalDiagnosis,
	ApprovalEffect,
	ApprovalEvaluation,
	ApprovalPolicy,
	ApprovalRule,
	ProjectContract,
	TaskContract,
} from "./types.ts";

export function validateApprovalPolicy(value: unknown): asserts value is ApprovalPolicy {
	if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Approval policy is required");
	const policy = value as Record<string, unknown>;
	if (
		policy.version !== 1 ||
		!["ask", "deny"].includes(String(policy.defaultEffect)) ||
		!Array.isArray(policy.rules) ||
		Object.keys(policy).some((key) => !["version", "defaultEffect", "rules"].includes(key))
	)
		throw new Error("Invalid approval policy version, default effect or rules");
	const ids = new Set<string>();
	for (const entry of policy.rules) {
		if (!entry || typeof entry !== "object" || Array.isArray(entry)) throw new Error("Invalid approval rule");
		const rule = entry as ApprovalRule;
		if (
			typeof rule.id !== "string" ||
			!/^[-a-z0-9]+$/.test(rule.id) ||
			ids.has(rule.id) ||
			!["auto", "ask", "deny"].includes(rule.effect) ||
			!["low", "medium", "high"].includes(rule.risk) ||
			!rule.match ||
			typeof rule.match !== "object" ||
			Array.isArray(rule.match) ||
			Object.keys(rule).some((key) => !["id", "effect", "risk", "match"].includes(key)) ||
			Object.keys(rule.match).some(
				(key) =>
					![
						"taskKind",
						"pathsAny",
						"toolsAny",
						"toolsAll",
						"writeWorkspace",
						"commitBranch",
						"integrateBranch",
						"maxDepthMin",
						"minBudgetTokens",
						"maxBudgetTokens",
					].includes(key),
			)
		)
			throw new Error("Invalid or duplicate approval rule");
		ids.add(rule.id);
		const match = rule.match;
		if (match.taskKind !== undefined && !["internal", "ordinary", "revision"].includes(match.taskKind))
			throw new Error(`Invalid task kind in rule ${rule.id}`);
		for (const key of ["pathsAny", "toolsAny", "toolsAll"] as const) {
			const list = match[key];
			if (
				list !== undefined &&
				(!Array.isArray(list) || !list.length || list.some((item) => typeof item !== "string" || !item.trim()))
			)
				throw new Error(`Invalid ${key} in rule ${rule.id}`);
		}
		if (match.writeWorkspace !== undefined && typeof match.writeWorkspace !== "boolean")
			throw new Error(`Invalid writeWorkspace in rule ${rule.id}`);
		for (const key of ["commitBranch", "integrateBranch"] as const) {
			if (match[key] !== undefined && typeof match[key] !== "boolean")
				throw new Error(`Invalid ${key} in rule ${rule.id}`);
		}
		if (match.maxDepthMin !== undefined && (!Number.isSafeInteger(match.maxDepthMin) || match.maxDepthMin < 0))
			throw new Error(`Invalid maxDepthMin in rule ${rule.id}`);
		if (
			match.minBudgetTokens !== undefined &&
			(!Number.isSafeInteger(match.minBudgetTokens) || match.minBudgetTokens < 1)
		)
			throw new Error(`Invalid minBudgetTokens in rule ${rule.id}`);
		if (
			match.maxBudgetTokens !== undefined &&
			(!Number.isSafeInteger(match.maxBudgetTokens) || match.maxBudgetTokens < 1)
		)
			throw new Error(`Invalid maxBudgetTokens in rule ${rule.id}`);
		if (
			match.minBudgetTokens !== undefined &&
			match.maxBudgetTokens !== undefined &&
			match.minBudgetTokens > match.maxBudgetTokens
		)
			throw new Error(`Inverted budget range in rule ${rule.id}`);
		if (
			rule.effect === "auto" &&
			(match.taskKind === undefined ||
				match.pathsAny === undefined ||
				match.toolsAll === undefined ||
				match.writeWorkspace === undefined ||
				match.maxBudgetTokens === undefined)
		)
			throw new Error(`Automatic rule ${rule.id} must bound task kind, paths, tools, workspace writing and budget`);
	}
}

/** Does `path` sit inside `allowed`, treating a directory as covering its children? */
function pathWithin(path: string, allowed: string): boolean {
	const prefix = allowed.replace(/\/$/, "");
	return path === prefix || path.startsWith(`${prefix}/`);
}

/**
 * What the Task asks for that the approved baseline does not allow.
 *
 * This is the question a human actually has to answer before revising a
 * baseline, so it is computed in full rather than summarized as a boolean.
 */
export function baselineExceeded(project: ProjectContract, task: TaskContract): ApprovalDiagnosis["exceeded"] {
	const projectPaths = project.authority.paths;
	const projectTools = project.authority.tools;
	const paths = task.authority.paths.filter((path) => !projectPaths.some((allowed) => pathWithin(path, allowed)));
	const tools = task.authority.tools.filter((tool) => !projectTools.includes(tool));
	const flags: string[] = [];
	if (task.authority.writeWorkspace && !project.authority.writeWorkspace) flags.push("writeWorkspace");
	if (task.authority.commitBranch && !project.authority.commitBranch) flags.push("commitBranch");
	if (task.authority.integrateBranch && !project.authority.integrateBranch) flags.push("integrateBranch");
	if (task.authority.readRepository && !project.authority.readRepository) flags.push("readRepository");
	return {
		paths,
		tools,
		flags,
		budgetTokens:
			task.budgetTokens > project.resourceLimits.budgetTokens
				? task.budgetTokens - project.resourceLimits.budgetTokens
				: null,
		maxDepth:
			task.maxDepth > project.delegationPolicy.maxDepth ? task.maxDepth - project.delegationPolicy.maxDepth : null,
		maxConcurrent:
			task.maxConcurrent > project.delegationPolicy.maxConcurrent
				? task.maxConcurrent - project.delegationPolicy.maxConcurrent
				: null,
	};
}

function exceededIsEmpty(exceeded: ApprovalDiagnosis["exceeded"]): boolean {
	return (
		exceeded.paths.length === 0 &&
		exceeded.tools.length === 0 &&
		exceeded.flags.length === 0 &&
		exceeded.budgetTokens === null &&
		exceeded.maxDepth === null &&
		exceeded.maxConcurrent === null
	);
}

/**
 * Evaluate the conditions of one rule against the Task.
 *
 * The returned list of failed conditions is what turns "ask" into something a
 * human can act on: a rule that did not match says which of its conditions held
 * and which did not.
 */
function evaluateRule(rule: ApprovalRule, task: TaskContract, taskKind: ApprovalEvaluation["inputs"]["taskKind"]) {
	const inputs = {
		taskKind,
		paths: [...task.authority.paths],
		tools: [...task.authority.tools],
		writeWorkspace: task.authority.writeWorkspace,
		commitBranch: task.authority.commitBranch,
		integrateBranch: task.authority.integrateBranch,
		maxDepth: task.maxDepth,
		budgetTokens: task.budgetTokens,
	};
	const failedOn: string[] = [];
	const match = rule.match;
	if (match.taskKind !== undefined && match.taskKind !== taskKind) failedOn.push("taskKind");
	if (
		match.pathsAny !== undefined &&
		!(rule.effect === "auto"
			? inputs.paths.length > 0 &&
				inputs.paths.every((path) => match.pathsAny?.some((allowed) => pathWithin(path, allowed)))
			: inputs.paths.some((path) => match.pathsAny?.some((allowed) => pathWithin(path, allowed))))
	)
		failedOn.push("pathsAny");
	if (match.toolsAny !== undefined && !inputs.tools.some((tool) => match.toolsAny?.includes(tool)))
		failedOn.push("toolsAny");
	if (
		match.toolsAll !== undefined &&
		!(rule.effect === "auto" && inputs.tools.length === 0
			? false
			: inputs.tools.every((tool) => match.toolsAll?.includes(tool)))
	)
		failedOn.push("toolsAll");
	if (match.writeWorkspace !== undefined && inputs.writeWorkspace !== match.writeWorkspace)
		failedOn.push("writeWorkspace");
	if (match.commitBranch !== undefined && inputs.commitBranch !== match.commitBranch) failedOn.push("commitBranch");
	if (match.integrateBranch !== undefined && inputs.integrateBranch !== match.integrateBranch)
		failedOn.push("integrateBranch");
	if (match.maxDepthMin !== undefined && inputs.maxDepth < match.maxDepthMin) failedOn.push("maxDepthMin");
	// `minBudgetTokens` is a lower bound: it matches when the budget is at least this.
	// On a `deny` rule that makes it an upper limit, which is the opposite of what the
	// name suggests at the call site. Organisation policy relies on that reading
	// (`no-unbounded-budget` denies at 2,000,000), so the semantics cannot be inverted
	// without breaking existing configuration - only labelled.
	if (match.minBudgetTokens !== undefined && inputs.budgetTokens < match.minBudgetTokens)
		failedOn.push("minBudgetTokens");
	if (match.maxBudgetTokens !== undefined && inputs.budgetTokens > match.maxBudgetTokens)
		failedOn.push("maxBudgetTokens");
	return { failedOn, inputs };
}

/**
 * Name a rule's numeric thresholds in the direction a reader expects.
 *
 * The field names are lower bounds, so a `deny` rule that sets `minBudgetTokens`
 * refuses everything at or above it: the number is a ceiling in effect. Saying
 * "最大预算" here rather than echoing the raw field name is what stops an operator
 * from reading the refusal as a floor they fell below.
 */
function limitsOf(rule: ApprovalPolicy["rules"][number]): string[] {
	const limits: string[] = [];
	const match = rule.match;
	if (match.minBudgetTokens !== undefined)
		limits.push(
			rule.effect === "deny"
				? `最大预算 ${match.minBudgetTokens} token（达到或超过即拒绝）`
				: `预算至少 ${match.minBudgetTokens} token 才适用`,
		);
	if (match.maxBudgetTokens !== undefined) limits.push(`最大预算 ${match.maxBudgetTokens} token`);
	if (match.maxDepthMin !== undefined) limits.push(`至少 ${match.maxDepthMin} 层委派才适用`);
	return limits;
}

/**
 * Decide whether a Task may run without a human, and explain the decision.
 *
 * The order matters and is deliberate:
 *
 * 1. A rule that says `deny` always wins. Nothing below it can authorize the Task.
 * 2. A rule that says `ask` always wins over automatic approval. Extra rules are
 *    allowed to be stricter than the baseline.
 * 3. A Task that fits inside the approved baseline is authorized automatically.
 *    The baseline is what the human approved, so a Task inside it needs no second
 *    signature.
 * 4. A Task outside the baseline needs a human, and the diagnosis says what has
 *    to change first — usually the baseline itself.
 *
 * The `deny` default of a strict project still applies to the case no rule covers,
 * so an operator who chose strict keeps that refusal.
 */
export function evaluateTaskApproval(
	policy: ApprovalPolicy | undefined,
	projectRevision: number | null,
	task: TaskContract,
	taskKind: ApprovalEvaluation["inputs"]["taskKind"],
	baseline?: ProjectContract | null,
): ApprovalEvaluation {
	const inputs = {
		taskKind,
		paths: [...task.authority.paths],
		tools: [...task.authority.tools],
		writeWorkspace: task.authority.writeWorkspace,
		commitBranch: task.authority.commitBranch,
		integrateBranch: task.authority.integrateBranch,
		maxDepth: task.maxDepth,
		budgetTokens: task.budgetTokens,
	};
	if (!policy)
		return {
			effect: "ask",
			ruleId: "legacy-no-policy",
			risk: "unknown",
			policyDigest: null,
			projectRevision,
			inputs,
		};
	const policyDigest = `sha256:${createHash("sha256").update(JSON.stringify(policy)).digest("hex")}`;

	// Every rule is evaluated, not just the first hit, so the ledger can explain
	// which rule decided and which ones were considered.
	const evaluated = policy.rules.map((rule) => {
		const { failedOn } = evaluateRule(rule, task, taskKind);
		return { id: rule.id, effect: rule.effect, matched: failedOn.length === 0, failedOn, limits: limitsOf(rule) };
	});
	const decided = evaluated.find((entry) => entry.matched) ?? null;
	const decidedRule = decided ? policy.rules.find((rule) => rule.id === decided.id) : undefined;

	let effect: ApprovalEffect;
	let ruleId: string;
	let risk: ApprovalEvaluation["risk"];

	// Automatic approval is for work an agent asked for on its own. A Task a human
	// created, and any revision of an existing Task, keep the human in the loop:
	// a revision changes what was already agreed, and an ordinary Task is a human
	// typing the command.
	const autoEligible = taskKind === "internal";

	if (decided?.effect === "deny") {
		effect = "deny";
		ruleId = decided.id;
		risk = decidedRule?.risk ?? "unknown";
	} else if (decided?.effect === "ask") {
		effect = "ask";
		ruleId = decided.id;
		risk = decidedRule?.risk ?? "unknown";
	} else if (baseline && autoEligible) {
		const exceeded = baselineExceeded(baseline, task);
		if (exceededIsEmpty(exceeded)) {
			// Inside the baseline: authorized without a second signature. This is the
			// path an agent's own Task takes, because the agent cannot ask a human
			// mid-flight.
			effect = "auto";
			ruleId = decided?.id ?? "baseline-subset";
			risk = decidedRule?.risk ?? "low";
		} else if (policy.defaultEffect === "deny") {
			effect = "deny";
			ruleId = decided?.id ?? "default";
			risk = decidedRule?.risk ?? "unknown";
		} else {
			effect = "ask";
			ruleId = decided?.id ?? "default";
			risk = decidedRule?.risk ?? "unknown";
		}
	} else if (decided?.effect === "auto") {
		effect = "auto";
		ruleId = decided.id;
		risk = decidedRule?.risk ?? "low";
	} else {
		effect = policy.defaultEffect;
		ruleId = decided?.id ?? "default";
		risk = decidedRule?.risk ?? "unknown";
	}

	const evaluation: ApprovalEvaluation = {
		effect,
		ruleId,
		risk,
		policyDigest,
		projectRevision,
		inputs,
	};
	if (baseline) {
		const exceeded = baselineExceeded(baseline, task);
		const baselineSubset = exceededIsEmpty(exceeded);
		evaluation.diagnosis = {
			baselineSubset,
			exceeded,
			rules: evaluated,
			requiresBaselineRevision: !baselineSubset,
			summary: describeDecision(effect, baselineSubset, exceeded, decided),
		};
	}
	return evaluation;
}

/** One sentence an operator can act on. */
function describeDecision(
	effect: ApprovalEffect,
	baselineSubset: boolean,
	exceeded: ApprovalDiagnosis["exceeded"],
	decided: { id: string; effect: ApprovalEffect } | null,
): string {
	if (effect === "deny") return decided ? `Denied by rule ${decided.id}.` : "Denied by the project policy.";
	if (effect === "auto")
		return baselineSubset
			? "Inside the approved project baseline, so no second signature is required."
			: "Rule would allow it, but the request exceeds the project baseline.";
	const parts: string[] = [];
	if (!baselineSubset) {
		const what: string[] = [];
		if (exceeded.paths.length) what.push(`paths ${exceeded.paths.join(", ")}`);
		if (exceeded.tools.length) what.push(`tools ${exceeded.tools.join(", ")}`);
		if (exceeded.flags.length) what.push(`flags ${exceeded.flags.join(", ")}`);
		if (exceeded.budgetTokens !== null) what.push(`budget +${exceeded.budgetTokens} tokens`);
		if (exceeded.maxDepth !== null) what.push(`depth +${exceeded.maxDepth}`);
		if (exceeded.maxConcurrent !== null) what.push(`concurrency +${exceeded.maxConcurrent}`);
		parts.push(`exceeds the project baseline (${what.join("; ")})`);
	}
	if (decided) parts.push(`rule ${decided.id} requires review`);
	return parts.length ? `${parts.join("; ")}.` : "Needs a human decision.";
}
