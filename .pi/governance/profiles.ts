// Approval profile presets.
//
// A profile is only a starting point: `gov init --profile <name>` records the
// name, and `governance_project_draft` fills the contract's approvalPolicy from
// it when the draft omits the field. The contract still has to be drafted and
// human-approved, so the policy that governs the project is always the one the
// operator approved, never a silently changing global default.
import * as fs from "node:fs";
import * as path from "node:path";
import type { ApprovalPolicy } from "./types.ts";

export type ApprovalProfileName = "strict" | "balanced" | "loose";

const NO_INTEGRATE = {
	id: "no-integrate",
	effect: "deny" as const,
	risk: "high" as const,
	match: { integrateBranch: true },
};
const PUSH_REVIEW = {
	id: "push-review",
	effect: "ask" as const,
	risk: "high" as const,
	match: { commitBranch: true },
};
const DELEGATION_REVIEW = {
	id: "delegation-review",
	effect: "ask" as const,
	risk: "medium" as const,
	match: { maxDepthMin: 1 },
};

/**
 * Profiles are ordered broadest-last: a human approves one, and every rule is
 * bounded on the dimensions that can cause damage outside the workspace.
 */
export const APPROVAL_PROFILES: Record<ApprovalProfileName, ApprovalPolicy> = {
	strict: {
		version: 1,
		defaultEffect: "deny",
		rules: [
			{ ...NO_INTEGRATE, match: { ...NO_INTEGRATE.match } },
			{ ...PUSH_REVIEW, match: { ...PUSH_REVIEW.match } },
			{ ...DELEGATION_REVIEW, match: { ...DELEGATION_REVIEW.match } },
			{
				id: "read-only-auto",
				effect: "auto",
				risk: "low",
				match: {
					taskKind: "internal",
					pathsAny: ["src"],
					toolsAll: ["read", "grep", "find", "ls"],
					writeWorkspace: false,
					commitBranch: false,
					maxBudgetTokens: 20_000,
				},
			},
		],
	},
	balanced: {
		version: 1,
		defaultEffect: "ask",
		rules: [
			{ ...NO_INTEGRATE, match: { ...NO_INTEGRATE.match } },
			{ ...PUSH_REVIEW, match: { ...PUSH_REVIEW.match } },
			{
				id: "read-only-auto",
				effect: "auto",
				risk: "low",
				match: {
					taskKind: "internal",
					pathsAny: ["src"],
					toolsAll: ["read", "grep", "find", "ls"],
					writeWorkspace: false,
					commitBranch: false,
					maxBudgetTokens: 50_000,
				},
			},
			{
				id: "edit-auto",
				effect: "auto",
				risk: "low",
				match: {
					taskKind: "internal",
					pathsAny: ["src"],
					toolsAll: ["read", "edit"],
					writeWorkspace: true,
					commitBranch: false,
					maxBudgetTokens: 20_000,
				},
			},
		],
	},
	loose: {
		version: 1,
		defaultEffect: "ask",
		rules: [
			{ ...NO_INTEGRATE, match: { ...NO_INTEGRATE.match } },
			{ ...PUSH_REVIEW, match: { ...PUSH_REVIEW.match } },
			{
				id: "edit-auto",
				effect: "auto",
				risk: "low",
				match: {
					taskKind: "internal",
					pathsAny: ["src"],
					toolsAll: ["read", "edit"],
					writeWorkspace: true,
					commitBranch: false,
					maxBudgetTokens: 100_000,
				},
			},
		],
	},
};

function copyPolicy(policy: ApprovalPolicy): ApprovalPolicy {
	return JSON.parse(JSON.stringify(policy)) as ApprovalPolicy;
}

export function isApprovalProfileName(value: unknown): value is ApprovalProfileName {
	return value === "strict" || value === "balanced" || value === "loose";
}

export function resolveApprovalProfile(name: string): ApprovalPolicy {
	if (!isApprovalProfileName(name)) throw new Error(`Unknown approval profile: ${name}`);
	return copyPolicy(APPROVAL_PROFILES[name]);
}

/**
 * Read the profile recorded by `gov init`. Old installations predate the field,
 * so null is normal and means "no default was declared".
 */
export function readInstalledProfile(project: string): ApprovalProfileName | null {
	try {
		const installed = JSON.parse(
			fs.readFileSync(path.join(project, ".pi", "governance", "installation.json"), "utf8"),
		) as { approvalProfile?: unknown };
		return isApprovalProfileName(installed.approvalProfile) ? installed.approvalProfile : null;
	} catch {
		return null;
	}
}

/**
 * Fill the draft's approvalPolicy from the installed profile when the model did
 * not provide one. An explicit policy always wins, and the injected policy is
 * still shown in the draft the human has to approve.
 */
export function withProfileDefault<T extends { approvalPolicy?: ApprovalPolicy }>(project: string, input: T): T {
	if (input.approvalPolicy) return input;
	const profile = readInstalledProfile(project) ?? "balanced";
	return { ...input, approvalPolicy: resolveApprovalProfile(profile) };
}
