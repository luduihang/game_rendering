/**
 * Draft text boundary (GOV-001, GOV-002).
 *
 * Models sometimes double-encode document strings: the tool payload then
 * carries literal two-character `\n` / `\"` sequences instead of real
 * newlines and quotes, producing one-line "Markdown" files. Normalization
 * happens exactly once, here, before a draft is stored. The event ledger
 * is never rewritten, so historical documents keep whatever bytes were
 * recorded.
 */

export type DraftNormalization = {
	text: string;
	normalized: boolean;
};

const ESCAPES: Record<string, string> = {
	n: "\n",
	t: "\t",
	r: "\r",
	b: "\b",
	f: "\f",
	'"': '"',
	"'": "'",
	"/": "/",
	"\\": "\\",
};

/**
 * Decode one layer of backslash escapes in a single left-to-right pass.
 * A single pass (not sequential replaces) means `\\n` becomes a literal
 * backslash-n, so escapes that were already correct inside code blocks
 * survive decoding.
 */
export function decodeOneEscapeLayer(text: string): string {
	let out = "";
	for (let index = 0; index < text.length; index++) {
		const char = text[index];
		if (char !== "\\") {
			out += char;
			continue;
		}
		const next = text[index + 1];
		if (next === "u") {
			const hex = text.slice(index + 2, index + 6);
			if (/^[0-9a-fA-F]{4}$/.test(hex)) {
				out += String.fromCharCode(Number.parseInt(hex, 16));
				index += 5;
			} else {
				out += char;
			}
			continue;
		}
		const decoded = ESCAPES[next];
		if (decoded !== undefined) {
			out += decoded;
			index++;
		} else {
			out += char;
		}
	}
	return out;
}

function countSequence(text: string, sequence: string): number {
	let count = 0;
	for (let index = 0; index + sequence.length <= text.length; index++) if (text.startsWith(sequence, index)) count++;
	return count;
}

/**
 * Decode one escape layer only when the document is clearly broken:
 * at least three literal `\n` sequences and more literal escapes than real
 * newlines. A well-formed multi-line document that legitimately mentions
 * a literal `\n` in prose or a code block is returned byte-identical.
 */
export function normalizeDraftText(text: string): DraftNormalization {
	const literalNewlines = countSequence(text, "\\n");
	const realNewlines = countSequence(text, "\n");
	if (literalNewlines < 3 || literalNewlines <= realNewlines) return { text, normalized: false };
	return { text: decodeOneEscapeLayer(text), normalized: true };
}

/**
 * Structural validation for PRD and plan (GOV-002). Drafts must be
 * readable, structured Markdown; this rejects one-liners and payloads
 * that failed normalization with an actionable error instead of storing
 * them. Content quality (evidence, verified vs unverified claims) is a
 * review concern documented in the tool description.
 */
export function validateDraftDocument(name: string, text: string): void {
	const realNewlines = countSequence(text, "\n");
	const hasHeading = text.split("\n").some((line) => /^#{1,6}\s+\S/.test(line));
	if (realNewlines < 2 || !hasHeading)
		throw new Error(
			`Invalid ${name}: must be structured multi-line Markdown with at least one heading ` +
				`(found ${realNewlines} real line break(s), ${hasHeading ? "heading present" : "no heading"}). ` +
				"Use real newlines, not literal backslash-n sequences.",
		);
}
