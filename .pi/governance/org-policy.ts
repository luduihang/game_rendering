// Org-level hard deny baseline.
//
// Some rules should not be re-decided per project: "never merge branches",
// "never touch credentials". They live in one file outside every repository and
// can only deny. Their rules are evaluated first, so no project auto/ask rule
// can out-vote them. The file is optional; when it is missing the feature is off.
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { validateApprovalPolicy } from "./approval-policy.ts";
import type { ApprovalPolicy, ApprovalRule } from "./types.ts";

const RULE_ID_PREFIX = "org-";

/**
 * `GOV_ORG_POLICY` selects the file. The literal value `off` disables the
 * baseline explicitly: an empty path would otherwise fall back to the default
 * location, and a missing file is already treated as "no baseline", so a
 * disabled switch must not be spelled as an empty string.
 */
export function orgPolicyPath(): string {
	const override = process.env.GOV_ORG_POLICY;
	if (override === "off") return "";
	if (override?.trim()) return path.resolve(override.trim());
	return path.join(os.homedir(), ".pi", "agent", "governance", "org-policy.json");
}

let cache: { key: string; policy: ApprovalPolicy } | null = null;

/**
 * Load and validate the org policy. Deny-only is enforced here, at the trust
 * boundary: a permissive org file would recreate the "AI decides" problem this
 * mechanism exists to remove.
 */
export function loadOrgApprovalPolicy(): ApprovalPolicy | null {
	const file = orgPolicyPath();
	if (!file) {
		cache = null;
		return null;
	}
	let stat: fs.Stats;
	try {
		stat = fs.statSync(file);
	} catch {
		cache = null;
		return null;
	}
	const key = `${file}:${stat.mtimeMs}:${stat.size}`;
	if (cache?.key === key) return cache.policy;

	let raw: string;
	try {
		raw = fs.readFileSync(file, "utf8");
	} catch (error) {
		throw new Error(`Org policy is unreadable: ${error instanceof Error ? error.message : String(error)}`);
	}
	let parsed: { version?: unknown; rules?: unknown };
	try {
		parsed = JSON.parse(raw) as { version?: unknown; rules?: unknown };
	} catch (error) {
		throw new Error(`Org policy is not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
	}
	if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.rules))
		throw new Error("Org policy must be an object with a rules array");
	const rules: ApprovalRule[] = parsed.rules.map((entry) => {
		if (!entry || typeof entry !== "object" || Array.isArray(entry))
			throw new Error("Org policy rule must be an object");
		const rule = entry as { id?: unknown; effect?: unknown; risk?: unknown; match?: unknown };
		if (typeof rule.id !== "string" || !rule.id.trim()) throw new Error("Org policy rule is missing an id");
		if (rule.effect !== "deny")
			throw new Error(`Org policy rule ${rule.id} must use effect deny (only deny is allowed at org level)`);
		const risk = rule.risk === "low" || rule.risk === "medium" || rule.risk === "high" ? rule.risk : "high";
		if (!rule.match || typeof rule.match !== "object" || Array.isArray(rule.match))
			throw new Error(`Org policy rule ${rule.id} is missing match`);
		return { id: rule.id, effect: "deny" as const, risk, match: rule.match as ApprovalRule["match"] };
	});
	const policy: ApprovalPolicy = { version: 1, defaultEffect: "deny", rules };
	validateApprovalPolicy(policy);
	cache = { key, policy };
	return policy;
}

/**
 * Prepend org rules to the project policy. Prefixing the id keeps the ledger
 * able to answer "who denied this": the evaluation records `org-<rule>`.
 */
export function mergeOrgDeny(
	org: ApprovalPolicy | null,
	project: ApprovalPolicy | undefined,
): ApprovalPolicy | undefined {
	if (!org) return project;
	const rules = org.rules.map((rule) => ({ ...rule, id: `${RULE_ID_PREFIX}${rule.id}` }));
	if (!project) return { version: 1, defaultEffect: "deny", rules };
	return {
		version: project.version,
		defaultEffect: project.defaultEffect,
		rules: [...rules, ...project.rules.map((rule) => ({ ...rule }))],
	};
}
