/**
 * Who is speaking, kept separate from how much that claim is worth.
 *
 * The two used to be one string. `local:<username>` was the only identity the CLI could
 * produce, and the reader of the ledger treated that prefix as proof of a human. A child
 * agent's review was therefore recorded as the operator's own work, and the independence
 * check compared an agent against a human - so it passed every time.
 *
 * Nothing here authenticates. The four levels below are ordered by how much the *ledger*
 * can vouch for, not by how much a person should be trusted:
 *
 * - `governance-run` - the Run exists in the ledger, so the actor is a real execution.
 * - `pi-session` - a session the ledger has observed. Says which conversation, not who.
 * - `os-user` - an account name from the OS. Says which account, not who is at the keyboard.
 * - `unknown` - nothing available.
 *
 * `session` and `host` are deliberately not called "human": an agent and a person running
 * the same command are indistinguishable at those levels, and a record that claims more
 * than it can prove is worse than one that admits the gap.
 */

/**
 * Where an identity came from.
 *
 * `absent` exists for events written before this model, which carry only a bare string.
 * It is never inferred - a legacy record is reported as unpriced provenance rather than
 * guessed into one of the four levels.
 */
export type IdentitySource = "governance-run" | "pi-session" | "os-user" | "unknown" | "absent";

/**
 * How far the identity can be trusted.
 *
 * There is no `authenticated-human` and there will not be one until the ruling's deferred
 * work lands (TTY or signature authentication). Adding the value before the mechanism
 * exists would let a caller claim it, which is the defect this replaces.
 */
export type IdentityAssurance = "governed" | "session" | "host" | "unverified";

export type Identity = {
	/** Ledger-shaped actor string, the form `GovernanceEventInput.actor` and events use. */
	id: string;
	source: IdentitySource;
	assurance: IdentityAssurance;
	runId: string | null;
	sessionId: string | null;
	/**
	 * Why this level was used and not a higher one.
	 *
	 * Always populated. A silent fallback from "we know the Run" to "we know the account"
	 * is the failure being fixed, so the downgrade itself has to be readable afterwards.
	 */
	reason: string;
};

/**
 * What the caller could find out about itself.
 *
 * Gathered by the caller rather than read here, so that resolving an identity stays a
 * pure function and every level can be exercised in a test without an OS or a session.
 */
export type IdentityFacts = {
	/** Run the caller claims to be. Only used if the ledger knows it. */
	runId: string | null;
	runKnown: boolean;
	/** Session the caller claims to belong to. Only used if the ledger has observed it. */
	sessionId: string | null;
	sessionKnown: boolean;
	/** OS account name, or null if the platform did not give one. */
	username: string | null;
	/**
	 * Whether the caller is attached to a terminal.
	 *
	 * Not authentication: an agent can allocate a pty. It is only used to pick between
	 * `host` and `unverified` at the `os-user` level, so that a command run through a pipe
	 * does not get recorded as if a person had typed it.
	 */
	interactive: boolean;
};

/**
 * Pick the strongest identity the facts support, saying which level was used and why.
 *
 * The order is the ruling's: a governed Run, then a session, then the OS account, then
 * nothing. Every step down records the reason it stepped, because "we fell back" and
 * "we were never given anything" produce the same `unknown` if the reason is dropped.
 */
export function resolveIdentity(facts: IdentityFacts): Identity {
	if (facts.runId && facts.runKnown)
		return {
			id: `agent-run:${facts.runId}`,
			source: "governance-run",
			assurance: "governed",
			runId: facts.runId,
			sessionId: facts.sessionId,
			reason: "the ledger holds this Run, so the actor is identified by an execution it recorded",
		};
	if (facts.sessionId && facts.sessionKnown)
		return {
			id: `pi-session:${facts.sessionId}`,
			source: "pi-session",
			assurance: "session",
			runId: null,
			sessionId: facts.sessionId,
			reason: facts.runId
				? "the Run named is not in the ledger, so the session it belongs to is the strongest surviving fact"
				: "a session was observed but no Run was named",
		};
	if (facts.username)
		return {
			id: `local:${facts.username}`,
			source: "os-user",
			assurance: facts.interactive ? "host" : "unverified",
			runId: null,
			sessionId: null,
			// Both branches say the same thing about *who*, and differ only in whether a
			// terminal was attached. Neither is authentication and the wording must not
			// suggest otherwise.
			reason: facts.interactive
				? "no Run or session was available; identified by the OS account of an interactive terminal, which is not proof of a human"
				: "no Run or session was available; identified by the OS account, with no terminal attached, so a person at the keyboard cannot be assumed",
		};
	return {
		id: "unknown",
		source: "unknown",
		assurance: "unverified",
		runId: null,
		sessionId: null,
		reason: "no Run, session, or OS account was available",
	};
}

/**
 * Build the facts a CLI process can observe about itself.
 *
 * Separate from `resolveIdentity` so the OS and environment reads happen in one place and
 * the judgement stays testable. `sessionKnown` and `runKnown` are the caller's job: only
 * the ledger can say whether an ID it was handed actually exists.
 */
export function observeIdentity(options: {
	readonly env: Record<string, string | undefined>;
	readonly username: string | null;
	readonly interactive: boolean;
}): IdentityFacts {
	const raw = options.env.PI_SESSION_ID;
	const sessionId = typeof raw === "string" && raw.trim() ? raw.trim() : null;
	return {
		runId: null,
		runKnown: false,
		sessionId,
		// Being present in the environment is not the same as being in the ledger. A stale
		// or forged value must not be promoted to `pi-session`, so the caller confirms it
		// against `agent.session-observed` before this becomes true.
		sessionKnown: false,
		username: options.username,
		interactive: options.interactive,
	};
}

/**
 * Whether a stored actor string has provenance worth reading.
 *
 * Used to keep legacy records out of the four levels instead of inventing one for them.
 */
export function isKnownIdentitySource(source: IdentitySource | undefined): boolean {
	return source !== undefined && source !== "absent" && source !== "unknown";
}
