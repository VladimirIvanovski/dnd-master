/** Remove dialogue lines that the DM also embedded as quotes inside narration. */
export function stripEmbeddedDialogue(
  narration: string,
  dialogue: Array<{ text: string }>,
): string {
  const texts = dialogue
    .map((l) => (l.text || "").trim())
    .filter((t) => t.length >= 6);

  let out = narration;
  if (texts.length >= 2) {
    out = removeSpeech(out, texts.join(" "));
  }
  for (const text of texts) {
    out = removeSpeech(out, text);
  }

  return out
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\s+([,.])/g, "$1")
    .replace(/[“"'‘’]\s*[”"'‘’]/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function removeSpeech(haystack: string, speech: string): string {
  const escaped = escapeRegExp(speech);
  return haystack
    .replace(new RegExp(`[“"]\\s*${escaped}\\s*[”"]`, "g"), "")
    .replace(new RegExp(`[‘']\\s*${escaped}\\s*[’']`, "g"), "")
    .replace(new RegExp(escaped, "g"), "");
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
