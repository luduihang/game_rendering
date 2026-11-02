// The user-level extension: installed once per machine, governs whichever
// project the session belongs to.
//
// Two questions this file keeps apart, because conflating them is what made the
// extension invisible:
//
//   1. Where is governance installed? Here, under ~/.pi/agent/extensions, so pi
//      loads it from any working directory. Installing it inside one project made
//      loading depend on which directory pi happened to start in.
//   2. Which project does it govern? Decided per session by git, not by this
//      directory. A Child working in src/module-a/ belongs to the same project as
//      its Main in the root.
//
// So the shim resolves the project on session start and then loads that project's
// own installed copy. A directory that is not a repository, or one where `gov init`
// was never run, gets no governance tools - no error, no half-loaded state.
//
// The project's own copy is loaded rather than a shared one on purpose: `gov
// upgrade` updates each project independently, and a project must keep running the
// version it was installed with instead of silently picking up whatever source
// happens to be on disk.
//
// Deferring matters. pi calls a factory once per process load, and the process
// directory is not the session directory - a session can be started anywhere and
// each session carries its own cwd. Resolving in the factory therefore binds the
// tools to the wrong project, or to none: verified by loading from /tmp, which
// registered zero tools even though a repository was one argument away.
//
// The three commands below exist because the bootstrap used to be a terminal
// command nobody could remember, and because a project with no installation had no
// way to create one from inside pi: every command was registered by the bridge,
// and the bridge only loads when an installation already exists.

import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

/** Where a project keeps its installed governance copy. */
function installedBridge(root: string): string | null {
	const candidate = path.join(root, ".pi", "governance", "pi-bridge.ts");
	return fs.existsSync(candidate) ? candidate : null;
}

/**
 * The repository root this session belongs to, or null when not in one.
 *
 * Uses the primary worktree rather than the nearest `.git` so a child working in a
 * linked worktree still resolves to the same project as its parent: governance
 * records belong to the project, not to the directory a task happens to run in.
 */
function projectRoot(cwd: string): string | null {
	try {
		const listing = execFileSync("git", ["worktree", "list", "--porcelain"], { cwd, encoding: "utf8" });
		const first = listing.split("\n").find((line) => line.startsWith("worktree "));
		return first ? first.slice("worktree ".length) : null;
	} catch {
		return null;
	}
}

type BridgeFactory = (pi: ExtensionAPI, ctx?: ExtensionContext) => unknown;

/**
 * Run the governance entry point that actually performs an install.
 *
 * It is executed rather than imported because `gov.ts` is a script: importing it
 * would run its argument parsing against pi's own argv.
 */
function runGov(source: string, args: string[], cwd: string): { ok: boolean; output: string } {
	try {
		const output = execFileSync(
			process.execPath,
			["--experimental-strip-types", path.join(source, "gov.ts"), ...args],
			{ cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], env: process.env },
		);
		return { ok: true, output: output.trim() };
	} catch (error) {
		const failure = error as { stdout?: string; stderr?: string; message?: string };
		const text = [failure.stdout, failure.stderr].filter(Boolean).join("\n").trim();
		return { ok: false, output: text || failure.message || "governance command failed" };
	}
}

export default function globalGovernance(pi: ExtensionAPI): void {
	// Loaded at most once per project per process: a session switch within the same
	// repository must not register a second copy of every tool.
	const loaded = new Set<string>();
	let pending: Promise<void> | null = null;

	const load = async (ctx: ExtensionContext): Promise<void> => {
		const root = projectRoot(ctx.cwd);
		if (!root || loaded.has(root)) return;
		const bridge = installedBridge(root);
		if (!bridge) return;
		// Marked before the import so a failing bridge is not retried on every event.
		loaded.add(root);
		const module = (await import(bridge)) as { default: BridgeFactory };
		// Handing over the context lets the bridge adopt this session immediately.
		// Its own session_start handler is registered during the dispatch that is
		// running this import, so that handler misses the event and the session would
		// stay unpublished until the first turn.
		await module.default(pi, ctx);
	};

	// session_start is the first hook that knows the session's directory. Loading
	// inside it also means the bridge's own session_start handler is registered in
	// time for the event that is already being dispatched.
	pi.on("session_start", async (_event, ctx) => {
		if (pending) await pending;
		pending = load(ctx).finally(() => {
			pending = null;
		});
		await pending;
	});

	// Backstop for a session that began before this extension finished loading: the
	// first turn still needs the tools, and by then the cwd is known.
	pi.on("before_agent_start", async (_event, ctx) => {
		if (loaded.size) return;
		if (pending) await pending;
		pending = load(ctx).finally(() => {
			pending = null;
		});
		await pending;
	});

	// `/gov-source` answers "which code am I actually running" without touching
	// anything. The resolution is repeated here rather than imported, because this
	// shim must work in a repository that has no installed copy yet - the one case
	// where the question matters most and the module is not available. The order is
	// the same as `resolveGovernanceSource`, and a test asserts the two agree.
	pi.registerCommand("gov-source", {
		description: "Show which governance source would be used right now: /gov-source",
		handler: async (_args, ctx) => {
			const root = projectRoot(ctx.cwd);
			const project = root ?? ctx.cwd;
			const valid = (candidate: string | null | undefined): string | null => {
				if (!candidate || !candidate.trim()) return null;
				const directory = path.resolve(candidate.trim());
				if (!fs.existsSync(directory)) return null;
				// Both files: a path aimed at the package instead of its src directory
				// exists and looks right, and would fail later for an unrelated reason.
				if (!fs.existsSync(path.join(directory, "gov.ts"))) return null;
				if (!fs.existsSync(path.join(directory, "init.ts"))) return null;
				return directory;
			};

			const env = process.env.PI_GOVERNANCE_SOURCE;
			const userConfig = path.join(os.homedir(), ".pi", "agent", "governance", "source.json");
			let configured: string | null = null;
			if (fs.existsSync(userConfig)) {
				try {
					const record = JSON.parse(fs.readFileSync(userConfig, "utf8")) as { source?: unknown };
					if (typeof record.source === "string") configured = record.source;
				} catch {
					configured = null;
				}
			}
			let recorded: string | null = null;
			// Three different states, reported differently: no installation at all, an
			// installation written before this field existed, and a recorded path. The
			// first two both yield no candidate, but "absent" for a project that does
			// have governance reads as a missing install and sends the reader looking.
			const installed = path.join(project, ".pi", "governance", "installation.json");
			let installationNote = "no installation in this project";
			if (fs.existsSync(installed)) {
				try {
					const record = JSON.parse(fs.readFileSync(installed, "utf8")) as { sourcePath?: unknown };
					if (typeof record.sourcePath === "string") recorded = record.sourcePath;
					else installationNote = "installation present but written before sourcePath existed";
				} catch {
					installationNote = "installation record is unreadable";
				}
			}

			const rows: Array<[string, string | null, string]> = [
				["1 argument", null, "no path passed"],
				["2 environment", env ?? null, `${"PI_GOVERNANCE_SOURCE"} is not set`],
				["3 user config", configured, "no user config"],
				["4 installation", recorded, installationNote],
			];
			let hit: string | null = null;
			const lines: string[] = [];
			for (const [label, candidate, note] of rows) {
				const directory = valid(candidate);
				const state = directory ? "VALID" : candidate ? "rejected" : "absent";
				lines.push(`${state.padEnd(9)} ${label}: ${candidate ?? `- (${note})`}`);
				if (directory && !hit) hit = `${label} -> ${directory}`;
			}
			lines.unshift(
				hit ? `Resolved: ${hit}` : "Resolved: none. /gov-init will fail; set PI_GOVERNANCE_SOURCE or pass a path.",
			);
			if (!root) lines.push("", "Not a git repository; governance cannot be installed here.");
			ctx.ui.notify(lines.join("\n"), hit ? "info" : "error");
		},
	});

	// `/gov-init` exists to break a circular dependency: every other governance
	// command is registered by the bridge, and the bridge only loads when an
	// installation already exists. A new repository therefore had no way to install
	// itself from inside pi.
	pi.registerCommand("gov-init", {
		description: "Initialize governance in this repository: /gov-init [source-dir]",
		handler: async (args, ctx) => {
			const root = projectRoot(ctx.cwd);
			if (!root) {
				ctx.ui.notify("Not a git repository. Run git init, then /gov-init.", "error");
				return;
			}
			if (fs.existsSync(path.join(root, ".pi", "governance", "installation.json"))) {
				ctx.ui.notify("This project already has governance. Use /gov-upgrade to update it.", "info");
				return;
			}
			const explicit = args.trim();
			const source = explicit || process.env.PI_GOVERNANCE_SOURCE;
			const config = path.join(os.homedir(), ".pi", "agent", "governance", "source.json");
			let resolved = source;
			if (!resolved && fs.existsSync(config)) {
				try {
					const record = JSON.parse(fs.readFileSync(config, "utf8")) as { source?: unknown };
					if (typeof record.source === "string") resolved = record.source;
				} catch {
					// A corrupt config is reported by the failure message below.
				}
			}
			if (!resolved) {
				ctx.ui.notify(
					[
						"No governance source is configured.",
						"Set the environment variable once:",
						"  export PI_GOVERNANCE_SOURCE=/path/to/pi/packages/governance/src",
						"or pass the directory to this command:",
						"  /gov-init /path/to/pi/packages/governance/src",
					].join("\n"),
					"error",
				);
				return;
			}
			const result = runGov(resolved, ["init", root], root);
			if (!result.ok) {
				ctx.ui.notify(`Governance init failed:\n${result.output}`, "error");
				return;
			}
			// Remembering the working source is what makes the next project a
			// one-word command instead of another path to paste.
			try {
				fs.mkdirSync(path.dirname(config), { recursive: true });
				fs.writeFileSync(config, `${JSON.stringify({ source: path.resolve(resolved) }, null, 2)}\n`);
			} catch {
				// Failing to persist is a convenience loss, not an install failure.
			}
			// Loading immediately is the point of doing this in-session, but the
			// installed copy has no node_modules: its third-party imports resolve only
			// where the host project provides them. So a failed immediate load is a
			// known, quotable condition rather than a broken install, and saying
			// "restart" is honest where "done" would not be.
			let loadedNow = true;
			let loadError: string | null = null;
			try {
				await load(ctx);
			} catch (error) {
				loadedNow = false;
				loadError = error instanceof Error ? error.message : String(error);
			}
			ctx.ui.notify(
				[
					`Governance initialized from ${resolved}.`,
					result.output,
					"",
					loadedNow
						? "Governance tools are available in this session."
						: [
								"Tools are NOT available yet in this session.",
								`Reason: ${loadError}`,
								"pi resolves extension imports through its own virtual modules, so this may be a",
								"transient failure. Restart pi and it will load at startup.",
							].join("\n"),
				].join("\n"),
				loadedNow ? "info" : "error",
			);
		},
	});

	// `/gov-upgrade` reports what it cannot promise: this process already imported
	// the old bridge, so claiming the session now runs the new code would be false.
	pi.registerCommand("gov-upgrade", {
		description: "Upgrade this project's governance copy: /gov-upgrade [source-dir]",
		handler: async (args, ctx) => {
			const root = projectRoot(ctx.cwd);
			if (!root) {
				ctx.ui.notify("Not a git repository; there is nothing to upgrade.", "error");
				return;
			}
			const recorded = path.join(root, ".pi", "governance", "installation.json");
			if (!fs.existsSync(recorded)) {
				ctx.ui.notify("This project has no governance yet. Use /gov-init first.", "error");
				return;
			}
			// Same rungs as `/gov-source`, minus the explicit argument which is being
			// read here. Skipping the user config would make the command that reports
			// "resolved from user config" refuse to use it.
			let source = args.trim() || process.env.PI_GOVERNANCE_SOURCE || null;
			if (!source) {
				const configFile = path.join(os.homedir(), ".pi", "agent", "governance", "source.json");
				if (fs.existsSync(configFile)) {
					try {
						const config = JSON.parse(fs.readFileSync(configFile, "utf8")) as { source?: unknown };
						if (typeof config.source === "string") source = config.source;
					} catch {
						// Falls through to the installation record.
					}
				}
			}
			if (!source) {
				try {
					const record = JSON.parse(fs.readFileSync(recorded, "utf8")) as { sourcePath?: unknown };
					if (typeof record.sourcePath === "string") source = record.sourcePath;
				} catch {
					// Reported below as a missing source.
				}
			}
			if (!source) {
				ctx.ui.notify(
					[
						"This installation does not record where it came from, and no source is configured.",
						"Pass the source once; the result will be recorded for next time:",
						"  /gov-upgrade /path/to/pi/packages/governance/src",
					].join("\n"),
					"error",
				);
				return;
			}
			const result = runGov(source, ["upgrade", root], root);
			if (!result.ok) {
				ctx.ui.notify(`Governance upgrade failed:\n${result.output}`, "error");
				return;
			}
			ctx.ui.notify(
				[
					`Upgraded from ${source}.`,
					result.output,
					"",
					"This session is still running the code it loaded at startup.",
					"Restart pi (or /reload) before relying on the new behaviour.",
				].join("\n"),
				"info",
			);
		},
	});
}
