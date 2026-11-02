// Installed-copy facts shared by init, upgrade and the CLI.
//
// The installed copy is a plain directory of `.ts` files under
// `.pi/governance/`. Node has to decide whether each file is CommonJS or an ES
// module. With no `package.json` in that directory it has nothing to go on, so
// it parses the file as CommonJS, fails on the first `import`, reparses as ESM
// and prints MODULE_TYPELESS_PACKAGE_JSON on every invocation. The project's own
// package.json is not a substitute: it is usually absent, and when present a
// missing `"type"` field produces the same warning.
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

/**
 * Installation format version, not the governance feature version. `0.2.1` is
 * what shipped before `gov upgrade` existed; `0.2.2` adds the module type marker
 * and records the source version that produced the copy. An installed copy may
 * be upgraded only when this number is known: an unknown number means a newer
 * Governance wrote it and this code cannot reason about its layout.
 */
export const INSTALL_VERSION = "0.2.2";

/**
 * Module type marker written into the installed directory.
 *
 * `{"type":"module"}` is the whole fix for the warning: it tells Node the
 * `.ts` files are ESM before parsing, so there is no failed CommonJS parse.
 * `private` keeps the directory from looking like a publishable package.
 */
export const INSTALL_PACKAGE_JSON = `${JSON.stringify({ name: "pi-governance-installed", private: true, type: "module" }, null, 2)}\n`;

/**
 * The extension entry Pi loads. It only re-exports the bridge so the module that
 * holds hooks lives inside the installed copy and is upgraded with it.
 */
export const BRIDGE_SHIM = 'export { default } from "../governance/pi-bridge.ts";\n';

export type Installation = {
	version: string;
	projectId: string;
	approvalProfile?: string;
	/**
	 * Absolute path of the source directory this copy was built from.
	 *
	 * Without it an installation cannot answer "where did I come from", which is
	 * how copies drifted: `gov init` copies the directory it was loaded from, so
	 * running the same command from an old project's `.pi/governance/` installed
	 * that old project's version. Absent on copies written before this field
	 * existed - readers treat that as unknown, not as an error.
	 */
	sourcePath?: string;
};

export function installationPath(project: string): string {
	return path.join(project, ".pi", "governance", "installation.json");
}

export function installPackageJsonPath(project: string): string {
	return path.join(project, ".pi", "governance", "package.json");
}

export function bridgeEntryPath(project: string): string {
	return path.join(project, ".pi", "extensions", "governance-bridge.ts");
}

/**
 * Modules an installed copy needs, discovered by following relative imports from
 * the entry points instead of a hand-maintained list.
 *
 * The list used to be manual and failed the same way twice: a new module was
 * added, the list was not, and the installed CLI died with `ERR_MODULE_NOT_FOUND`
 * only when someone ran it. A missing entry surfaced as a runtime failure in a
 * different directory, which is the worst place to find it.
 *
 * Entries are `index.ts` and `cli.ts` because those are what an installed project
 * executes; `pi-bridge.ts` is reached through the bridge shim, so it is seeded
 * too. Anything they import transitively is included. Bare imports (node:
 * builtins, nothing else is used) are ignored: the installed copy has no
 * `node_modules` and must not start needing one.
 */
export function sourceFiles(source: string): string[] {
	const found = new Set<string>();
	// `extension-shim.ts` is seeded because the user-level extension is generated
	// from it. Leaving it out is what forced that file to be copied by hand, so it
	// never moved with an upgrade.
	const queue = ["index.ts", "cli.ts", "pi-bridge.ts", "extension-shim.ts", "OPERATOR-GUIDE.md"];
	while (queue.length) {
		const name = queue.shift() as string;
		if (found.has(name)) continue;
		const file = path.join(source, name);
		if (!fs.statSync(file).isFile()) throw new Error(`Governance source is missing ${name}`);
		found.add(name);
		const body = fs.readFileSync(file, "utf8");
		for (const match of body.matchAll(/from\s+"(\.\/[^"]+)"/g)) {
			const specifier = match[1];
			if (!specifier.endsWith(".ts")) throw new Error(`Unexpected import extension in ${name}: ${specifier}`);
			queue.push(specifier.slice(2));
		}
	}
	// Deterministic order keeps the installed directory listing stable.
	return [...found].sort();
}

export function readInstallation(project: string): Installation | null {
	const file = installationPath(project);
	if (!fs.existsSync(file)) return null;
	const value: unknown = JSON.parse(fs.readFileSync(file, "utf8"));
	if (!value || typeof value !== "object" || Array.isArray(value)) return null;
	const record = value as Record<string, unknown>;
	if (typeof record.version !== "string" || typeof record.projectId !== "string") return null;
	return {
		version: record.version,
		projectId: record.projectId,
		...(typeof record.approvalProfile === "string" ? { approvalProfile: record.approvalProfile } : {}),
		...(typeof record.sourcePath === "string" && record.sourcePath.trim()
			? { sourcePath: record.sourcePath.trim() }
			: {}),
	};
}

/**
 * Write a file that Node reads before it parses any module in the installed
 * directory. `wx` is deliberate: callers decide first whether overwriting is
 * correct, so an unexpected existing file must not be replaced silently.
 */
export function writeInstallPackageJson(project: string, flag: "wx" | "w" = "wx"): string {
	const file = installPackageJsonPath(project);
	fs.writeFileSync(file, INSTALL_PACKAGE_JSON, { flag });
	return file;
}

/** Where the user-level extension lives, independent of any project. */
export function userExtensionPath(home: string): string {
	return path.join(home, ".pi", "agent", "extensions", "governance", "index.ts");
}

export type UserExtensionResult = {
	path: string;
	/** `written` the first time, `unchanged` when it already matched. */
	state: "written" | "unchanged";
	/** Where a differing previous file was copied before being replaced. */
	backup: string | null;
};

/**
 * Install the extension that pi loads from any working directory.
 *
 * Overwriting is conditional because this file lives outside the repository and
 * so has no version control behind it: a local edit someone made deliberately is
 * still recoverable, and silence would not be. Identical content is the common
 * case on upgrade and writes nothing.
 */
export function writeUserExtension(source: string, home = os.homedir()): UserExtensionResult {
	// Same reason the project copy gets one: without a `type` marker Node parses the
	// .ts file as CommonJS, fails on the first import, reparses as ESM and warns on
	// every load. The extension is loaded once per session, so the cost is paid at
	// startup in the place hardest to attribute.
	const marker = path.join(path.dirname(userExtensionPath(home)), "package.json");
	if (!fs.existsSync(marker)) {
		fs.mkdirSync(path.dirname(marker), { recursive: true });
		fs.writeFileSync(marker, INSTALL_PACKAGE_JSON.replace("pi-governance-installed", "pi-governance-extension"));
	}
	const body = fs.readFileSync(path.join(source, "extension-shim.ts"), "utf8");
	const target = userExtensionPath(home);
	if (fs.existsSync(target) && fs.readFileSync(target, "utf8") === body)
		return { path: target, state: "unchanged", backup: null };
	let backup: string | null = null;
	if (fs.existsSync(target)) {
		const existing = fs.readFileSync(target);
		// A stack of identical backups is noise that hides the one that matters.
		// Reusing the newest one keeps the previous content recoverable without
		// growing a directory listing nobody reads.
		const previous = fs
			.readdirSync(path.dirname(target))
			.filter((name) => name.startsWith(`${path.basename(target)}.`) && name.endsWith(".bak"))
			.sort()
			.at(-1);
		const reusable =
			previous && fs.readFileSync(path.join(path.dirname(target), previous)).equals(existing)
				? path.join(path.dirname(target), previous)
				: null;
		backup =
			reusable ??
			(() => {
				const file = `${target}.${new Date().toISOString().replace(/[:.]/g, "-")}.bak`;
				fs.copyFileSync(target, file);
				return file;
			})();
	}
	fs.mkdirSync(path.dirname(target), { recursive: true });
	fs.writeFileSync(target, body);
	return { path: target, state: "written", backup };
}
