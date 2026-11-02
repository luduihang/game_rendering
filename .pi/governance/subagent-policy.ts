import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { AGENT_TEMPLATES } from "./agent-templates.ts";
import type { GovernanceKernel } from "./kernel.ts";
import type { GovernanceState } from "./types.ts";

export type LegacySubagentPolicy = {
	version: 1;
	model: string;
	defaultTier: string;
	maxConcurrent: number;
	tiers: Record<string, { contextTokens: number; maxConcurrent: number; useFor: string }>;
};

export type SubagentRole = {
	modelProfiles: string[];
	defaultModelProfile: string;
	maxConcurrent: number;
	maxAllocationTokens: number;
	timeoutMs: number;
	useFor: string;
};

export type SubagentPolicy = {
	version: 2;
	models: Record<string, string>;
	defaultAgent: string;
	maxConcurrent: number;
	maxRunsPerTask: number;
	agents: Record<string, SubagentRole>;
};

export type SubagentPolicyV3 = Omit<SubagentPolicy, "version" | "agents" | "defaultAgent"> & {
	version: 3;
	agents: Record<
		string,
		SubagentRole & {
			description: string;
			enabled: boolean;
			tools: string[];
		}
	>;
};

export type LoadedSubagentPolicy = { policy: LegacySubagentPolicy | SubagentPolicy | SubagentPolicyV3; digest: string };
export type ResolvedSubagentRoute = {
	model: string;
	policyDigest: string;
	maxConcurrent: number;
	roleMaxConcurrent: number;
	maxRunsPerTask: number | null;
	maxAllocationTokens: number | null;
	timeoutMs: number | null;
	modelProfile: string | null;
	legacyTier: string | null;
	contextTokens: number | null;
};

export const DEFAULT_SUBAGENT_POLICY: SubagentPolicy = {
	version: 2,
	models: { "local-qwen": "vllm-local/Qwen3.8-27B" },
	defaultAgent: "scout",
	maxConcurrent: 2,
	maxRunsPerTask: 20,
	agents: {
		scout: {
			modelProfiles: ["local-qwen"],
			defaultModelProfile: "local-qwen",
			maxConcurrent: 2,
			maxAllocationTokens: 30000,
			timeoutMs: 900000,
			useFor: "资料定位、只读调查",
		},
		worker: {
			modelProfiles: ["local-qwen"],
			defaultModelProfile: "local-qwen",
			maxConcurrent: 1,
			maxAllocationTokens: 120000,
			timeoutMs: 1800000,
			useFor: "范围明确的实现",
		},
		reviewer: {
			modelProfiles: ["local-qwen"],
			defaultModelProfile: "local-qwen",
			maxConcurrent: 1,
			maxAllocationTokens: 60000,
			timeoutMs: 900000,
			useFor: "独立审核与验证",
		},
	},
};

/**
 * Template copied into `management/policies/subagents.json` by `gov init`.
 *
 * This is the default shape a new project starts from, edited here rather than in
 * each project: worker roles run on the local model while the Main Agent keeps
 * whatever model the session is already using. Child models are an explicit
 * launch parameter (pi-subagents passes `model` to the child session), so pinning
 * them here is what stops a child from silently inheriting a cloud model.
 *
 * A project may edit its own copy afterwards; `policy approve` is what makes the
 * edit effective, so the template is a starting point, not an override.
 */
export const INITIAL_SUBAGENT_POLICY: SubagentPolicyV3 = {
	version: 3,
	models: { qwen38: "vllm-local/Qwen3.8-27B" },
	maxConcurrent: 5,
	maxRunsPerTask: 20,
	// Built from the same template `gov init` writes into `.pi/agents/`, so the
	// policy and the definitions pi-subagents actually launches cannot drift.
	agents: Object.fromEntries(
		AGENT_TEMPLATES.map((template) => [
			template.id,
			{
				description: template.description,
				useFor: template.useFor,
				enabled: true,
				modelProfiles: ["qwen38"],
				defaultModelProfile: "qwen38",
				tools: template.tools,
				maxConcurrent: template.maxConcurrent,
				maxAllocationTokens: template.maxAllocationTokens,
				timeoutMs: template.timeoutMs,
			},
		]),
	),
};

const positive = (value: unknown) => Number.isSafeInteger(value) && (value as number) > 0;
const keys = (value: Record<string, unknown>, allowed: string[]) =>
	Object.keys(value).every((key) => allowed.includes(key));
const profileName = (value: string) => /^[a-z][a-z0-9-]*$/.test(value);

export function subagentPolicyPath(project: string): string {
	return path.join(project, "management", "policies", "subagents.json");
}

export function loadSubagentPolicy(project: string): LoadedSubagentPolicy {
	const file = subagentPolicyPath(project);
	const raw = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : JSON.stringify(DEFAULT_SUBAGENT_POLICY);
	const value: unknown = JSON.parse(raw);
	if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid subagent policy");
	const candidate = value as Record<string, unknown>;
	if (candidate.version === 1) {
		if (
			!keys(candidate, ["version", "model", "defaultTier", "maxConcurrent", "tiers"]) ||
			typeof candidate.model !== "string" ||
			!/^\S+\/\S+$/.test(candidate.model) ||
			typeof candidate.defaultTier !== "string" ||
			!positive(candidate.maxConcurrent) ||
			!candidate.tiers ||
			typeof candidate.tiers !== "object" ||
			Array.isArray(candidate.tiers)
		)
			throw new Error("Invalid subagent policy fields");
		const tiers = candidate.tiers as Record<string, unknown>;
		if (!Object.hasOwn(tiers, candidate.defaultTier) || !Object.keys(tiers).length)
			throw new Error("Subagent policy default tier is missing");
		for (const [name, entry] of Object.entries(tiers)) {
			if (!name.trim() || !entry || typeof entry !== "object" || Array.isArray(entry))
				throw new Error(`Invalid subagent tier ${name}`);
			const tier = entry as Record<string, unknown>;
			if (
				!positive(tier.contextTokens) ||
				!positive(tier.maxConcurrent) ||
				(tier.maxConcurrent as number) > (candidate.maxConcurrent as number) ||
				typeof tier.useFor !== "string" ||
				!tier.useFor.trim()
			)
				throw new Error(`Invalid subagent tier ${name}`);
		}
		return { policy: candidate as LegacySubagentPolicy, digest: createHash("sha256").update(raw).digest("hex") };
	}
	if (
		(candidate.version !== 2 && candidate.version !== 3) ||
		!keys(candidate, ["version", "models", "defaultAgent", "maxConcurrent", "maxRunsPerTask", "agents"]) ||
		!candidate.models ||
		typeof candidate.models !== "object" ||
		Array.isArray(candidate.models) ||
		!candidate.agents ||
		typeof candidate.agents !== "object" ||
		Array.isArray(candidate.agents) ||
		!positive(candidate.maxConcurrent) ||
		!positive(candidate.maxRunsPerTask) ||
		(candidate.version === 2 && typeof candidate.defaultAgent !== "string")
	)
		throw new Error("Invalid subagent policy V2 fields");
	const models = candidate.models as Record<string, unknown>;
	const agents = candidate.agents as Record<string, unknown>;
	if (
		candidate.version === 2 &&
		(!Object.keys(models).length ||
			!Object.keys(agents).length ||
			!Object.hasOwn(agents, candidate.defaultAgent as string))
	)
		throw new Error("Subagent policy requires models and a default Agent");
	if (candidate.version === 3 && Object.keys(candidate).some((key) => key === "defaultAgent"))
		throw new Error("V3 policy requires an explicit Agent for each delegation");
	for (const [name, model] of Object.entries(models))
		if (!profileName(name) || typeof model !== "string" || !/^\S+\/\S+$/.test(model))
			throw new Error(`Invalid subagent model profile ${name}`);
	for (const [name, entry] of Object.entries(agents)) {
		if (!profileName(name) || !entry || typeof entry !== "object" || Array.isArray(entry))
			throw new Error(`Invalid subagent Agent ${name}`);
		const role = entry as Record<string, unknown>;
		if (
			!keys(role, [
				...(candidate.version === 3 ? ["description", "enabled", "tools"] : []),
				"modelProfiles",
				"defaultModelProfile",
				"maxConcurrent",
				"maxAllocationTokens",
				"timeoutMs",
				"useFor",
			]) ||
			!Array.isArray(role.modelProfiles) ||
			!role.modelProfiles.length ||
			role.modelProfiles.some((item) => typeof item !== "string" || !Object.hasOwn(models, item)) ||
			new Set(role.modelProfiles).size !== role.modelProfiles.length ||
			typeof role.defaultModelProfile !== "string" ||
			!role.modelProfiles.includes(role.defaultModelProfile) ||
			!positive(role.maxConcurrent) ||
			(role.maxConcurrent as number) > (candidate.maxConcurrent as number) ||
			!positive(role.maxAllocationTokens) ||
			!positive(role.timeoutMs) ||
			typeof role.useFor !== "string" ||
			!role.useFor.trim() ||
			(candidate.version === 3 &&
				(typeof role.description !== "string" ||
					!role.description.trim() ||
					typeof role.enabled !== "boolean" ||
					!Array.isArray(role.tools) ||
					role.tools.some((tool) => typeof tool !== "string" || !/^[a-zA-Z][a-zA-Z0-9:_-]*$/.test(tool)) ||
					new Set(role.tools).size !== role.tools.length))
		)
			throw new Error(`Invalid subagent Agent route ${name}`);
	}
	return {
		policy: candidate as SubagentPolicy | SubagentPolicyV3,
		digest: createHash("sha256")
			.update(candidate.version === 3 ? JSON.stringify(candidate) : raw)
			.digest("hex"),
	};
}

export function resolveSubagentRoute(
	loaded: LoadedSubagentPolicy,
	agent: string,
	modelProfile?: string,
	contextTier?: string,
): ResolvedSubagentRoute {
	const { policy, digest } = loaded;
	if (policy.version === 1) {
		if (modelProfile) throw new Error("V1 policy does not support modelProfile");
		const tierName = contextTier ?? policy.defaultTier;
		const tier = Object.hasOwn(policy.tiers, tierName) ? policy.tiers[tierName] : undefined;
		if (!tier) throw new Error(`Unknown context tier ${tierName}`);
		return {
			model: policy.model,
			policyDigest: digest,
			maxConcurrent: policy.maxConcurrent,
			roleMaxConcurrent: tier.maxConcurrent,
			maxRunsPerTask: null,
			maxAllocationTokens: null,
			timeoutMs: null,
			modelProfile: null,
			legacyTier: tierName,
			contextTokens: tier.contextTokens,
		};
	}
	if (contextTier) throw new Error("V2 policy uses modelProfile, not contextTier");
	const role = Object.hasOwn(policy.agents, agent) ? policy.agents[agent] : undefined;
	if (!role) throw new Error(`Agent ${agent} is not allowed by project subagent policy`);
	if (policy.version === 3 && !policy.agents[agent].enabled) throw new Error(`Agent ${agent} is disabled`);
	const profile = modelProfile ?? role.defaultModelProfile;
	if (!role.modelProfiles.includes(profile))
		throw new Error(`Model profile ${profile} is not allowed for Agent ${agent}`);
	return {
		model: policy.models[profile],
		policyDigest: digest,
		maxConcurrent: policy.maxConcurrent,
		roleMaxConcurrent: role.maxConcurrent,
		maxRunsPerTask: policy.maxRunsPerTask,
		maxAllocationTokens: role.maxAllocationTokens,
		timeoutMs: role.timeoutMs,
		modelProfile: profile,
		legacyTier: null,
		contextTokens: null,
	};
}

export function approvedSubagentPolicyDigest(state: GovernanceState): string | null {
	// A project reset clears the effective policy approval. The approval events
	// stay in the ledger, so the boundary decides which one still applies.
	const event = state.events
		.filter((item) => item.type === "policy.approved" && item.sequence > state.resetBoundary)
		.at(-1);
	return typeof event?.payload.digest === "string" ? event.payload.digest : null;
}

const hash = (value: unknown): string => createHash("sha256").update(JSON.stringify(value)).digest("hex");
const settingsFile = (project: string): string => path.join(project, ".pi", "settings.json");

function generatedOverrides(
	policy: SubagentPolicyV3,
): Record<string, { tools: string[]; description: string; disabled: boolean }> {
	return Object.fromEntries(
		Object.entries(policy.agents).map(([id, role]) => [
			id,
			{ tools: role.tools, description: role.description, disabled: !role.enabled },
		]),
	);
}

function readSettings(project: string): Record<string, unknown> {
	const file = settingsFile(project);
	if (!fs.existsSync(file)) return {};
	const value: unknown = JSON.parse(fs.readFileSync(file, "utf8"));
	if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid Pi project settings");
	return value as Record<string, unknown>;
}

function managedProjection(settings: Record<string, unknown>, ids: string[]): Record<string, unknown> {
	const subagents = settings.subagents;
	const overrides =
		subagents && typeof subagents === "object" && !Array.isArray(subagents)
			? (subagents as Record<string, unknown>).agentOverrides
			: undefined;
	const entries =
		overrides && typeof overrides === "object" && !Array.isArray(overrides)
			? (overrides as Record<string, unknown>)
			: {};
	return Object.fromEntries(
		ids.map((id) => {
			const value = entries[id];
			const fields =
				value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
			return [
				id,
				{
					tools: fields.tools,
					description: fields.description,
					disabled: fields.disabled,
				},
			];
		}),
	);
}

export function subagentPluginVersion(): string {
	const file = path.join(os.homedir(), ".pi", "agent", "npm", "node_modules", "pi-subagents", "package.json");
	const value: unknown = JSON.parse(fs.readFileSync(file, "utf8"));
	if (!value || typeof value !== "object" || !("version" in value) || typeof value.version !== "string")
		throw new Error("Installed pi-subagents version is unavailable");
	return value.version;
}

export function subagentPolicyStatus(project: string, state: GovernanceState) {
	const loaded = loadSubagentPolicy(project);
	if (loaded.policy.version !== 3)
		return {
			...loaded,
			approvedDigest: approvedSubagentPolicyDigest(state),
			approved: loaded.policy.version === 1 || approvedSubagentPolicyDigest(state) === loaded.digest,
			mode: "legacy" as const,
		};
	const expected = generatedOverrides(loaded.policy);
	const settings = readSettings(project);
	const actual = managedProjection(settings, Object.keys(expected));
	const expectedDigest = hash(expected);
	const actualDigest = hash(actual);
	const lastSync = state.events.filter((event) => event.type === "policy.native-synced").at(-1);
	const syncedDigest = typeof lastSync?.payload.generatedDigest === "string" ? lastSync.payload.generatedDigest : null;
	const priorIds = Array.isArray(lastSync?.payload.agentIds)
		? lastSync.payload.agentIds.filter((id): id is string => typeof id === "string")
		: Object.keys(expected);
	const priorObservedDigest = hash(managedProjection(settings, priorIds));
	const newlyManaged = Object.keys(expected).filter((id) => !priorIds.includes(id));
	const conflict =
		syncedDigest !== null
			? priorObservedDigest !== syncedDigest ||
				Object.values(managedProjection(settings, newlyManaged)).some(
					(entry) =>
						entry && typeof entry === "object" && Object.values(entry).some((value) => value !== undefined),
				)
			: Object.values(actual).some(
					(entry) =>
						entry && typeof entry === "object" && Object.values(entry).some((value) => value !== undefined),
				);
	const pluginVersion = subagentPluginVersion();
	const approvalDigest = hash({ policyDigest: loaded.digest, generatedDigest: expectedDigest, pluginVersion });
	return {
		...loaded,
		mode: "v3" as const,
		expectedDigest,
		actualDigest,
		syncedDigest,
		conflict,
		synchronized: !conflict && actualDigest === expectedDigest,
		pluginVersion,
		approvalDigest,
		approvedDigest: approvedSubagentPolicyDigest(state),
		approved: approvedSubagentPolicyDigest(state) === approvalDigest,
	};
}

/**
 * Write the managed `agentOverrides` into Pi's project settings.
 *
 * Only the three managed fields (tools, description, disabled) are written for
 * each role; every other Pi setting, and any unrelated key inside an existing
 * override, is preserved. Returns the digest of what was generated so the
 * caller can record it.
 *
 * Kept separate from `syncSubagentPolicy` because `gov init` needs the same
 * write without requiring pi-subagents to be installed yet: a fresh project
 * must not fail to initialize on a machine that has not installed the plugin.
 */
export function applyAgentOverrides(
	project: string,
	policy: SubagentPolicyV3,
): { generatedDigest: string; agentIds: string[] } {
	const settings = readSettings(project);
	const subagents =
		settings.subagents && typeof settings.subagents === "object" && !Array.isArray(settings.subagents)
			? (settings.subagents as Record<string, unknown>)
			: {};
	const existing =
		subagents.agentOverrides &&
		typeof subagents.agentOverrides === "object" &&
		!Array.isArray(subagents.agentOverrides)
			? (subagents.agentOverrides as Record<string, unknown>)
			: {};
	const generated = generatedOverrides(policy);
	const overrides = { ...existing };
	for (const [id, fields] of Object.entries(generated)) {
		const prior = overrides[id];
		overrides[id] = {
			...(prior && typeof prior === "object" && !Array.isArray(prior) ? (prior as Record<string, unknown>) : {}),
			...fields,
		};
	}
	const file = settingsFile(project);
	fs.mkdirSync(path.dirname(file), { recursive: true });
	const temp = `${file}.${process.pid}.tmp`;
	try {
		fs.writeFileSync(
			temp,
			`${JSON.stringify({ ...settings, subagents: { ...subagents, agentOverrides: overrides } }, null, 2)}\n`,
			{ flag: "wx" },
		);
		fs.renameSync(temp, file);
	} finally {
		fs.rmSync(temp, { force: true });
	}
	return { generatedDigest: hash(generated), agentIds: Object.keys(generated) };
}

export function syncSubagentPolicy(project: string, kernel: GovernanceKernel, actor: string) {
	const status = subagentPolicyStatus(project, kernel.getState());
	if (status.mode !== "v3" || status.policy.version !== 3) throw new Error("Only V3 policies support native sync");
	if (!Object.keys(status.policy.agents).length || !Object.keys(status.policy.models).length)
		throw new Error("Configure at least one Agent and model before synchronization");
	if (status.conflict)
		throw new Error("Managed Pi agentOverrides changed outside Governance; resolve the conflict first");
	applyAgentOverrides(project, status.policy);
	const verified = subagentPolicyStatus(project, kernel.getState());
	if (verified.mode !== "v3" || verified.actualDigest !== verified.expectedDigest)
		throw new Error("Generated Pi agentOverrides did not match policy");
	kernel.store.append({
		type: "policy.native-synced",
		actor,
		taskId: null,
		runId: null,
		delegationId: null,
		payload: {
			policyDigest: status.digest,
			generatedDigest: status.expectedDigest,
			pluginVersion: status.pluginVersion,
			agentIds: Object.keys(status.policy.agents),
		},
	});
	return subagentPolicyStatus(project, kernel.getState());
}

export function validateSubagentPolicy(candidate: unknown): SubagentPolicyV3 {
	const probe = fs.mkdtempSync(path.join(os.tmpdir(), "governance-policy-"));
	try {
		const probeFile = subagentPolicyPath(probe);
		fs.mkdirSync(path.dirname(probeFile), { recursive: true });
		fs.writeFileSync(probeFile, JSON.stringify(candidate));
		const loaded = loadSubagentPolicy(probe);
		if (loaded.policy.version !== 3) throw new Error("New Subagent configuration must use V3");
		return loaded.policy;
	} finally {
		fs.rmSync(probe, { recursive: true, force: true });
	}
}

export function saveSubagentPolicy(
	project: string,
	kernel: GovernanceKernel,
	candidate: unknown,
	expectedDigest: string,
	actor: string,
) {
	const current = subagentPolicyStatus(project, kernel.getState());
	if (current.digest !== expectedDigest) throw new Error("Subagent policy changed; reload before saving");
	if (current.mode === "v3" && current.conflict) throw new Error("Managed Pi settings changed outside Governance");
	const validated = validateSubagentPolicy(candidate);
	if (current.policy.version === 3) {
		const removed = Object.keys(current.policy.agents).filter((id) => !(id in validated.agents));
		if (removed.length) throw new Error(`Disable existing Agents instead of removing them: ${removed.join(", ")}`);
	}
	const file = subagentPolicyPath(project);
	const temp = `${file}.${process.pid}.tmp`;
	try {
		fs.writeFileSync(temp, `${JSON.stringify(candidate, null, 2)}\n`, { flag: "wx" });
		fs.renameSync(temp, file);
	} finally {
		fs.rmSync(temp, { force: true });
	}
	kernel.store.append({
		type: "policy.draft-saved",
		actor,
		taskId: null,
		runId: null,
		delegationId: null,
		payload: { digest: loadSubagentPolicy(project).digest },
	});
	return syncSubagentPolicy(project, kernel, actor);
}

export function approveSubagentPolicy(project: string, kernel: GovernanceKernel, actor: string): LoadedSubagentPolicy {
	const loaded = loadSubagentPolicy(project);
	if (loaded.policy.version === 1) throw new Error("Only V2/V3 subagent policies require explicit approval");
	const status = subagentPolicyStatus(project, kernel.getState());
	if (status.mode === "v3" && (!status.synchronized || status.conflict))
		throw new Error("V3 policy must be synchronized before approval");
	const digest = status.mode === "v3" ? status.approvalDigest : loaded.digest;
	kernel.store.append(
		{
			type: "policy.approved",
			actor,
			taskId: null,
			runId: null,
			delegationId: null,
			payload: { digest, value: loaded.policy },
		},
		(state) => {
			if (!state.events.some((event) => event.type === "project.initialized"))
				throw new Error("Governance is not initialized");
			if (approvedSubagentPolicyDigest(state) === digest) throw new Error("Subagent policy is already approved");
			const fresh = subagentPolicyStatus(project, state);
			if ((fresh.mode === "v3" ? fresh.approvalDigest : fresh.digest) !== digest)
				throw new Error("Subagent policy changed during approval");
		},
	);
	return loaded;
}
