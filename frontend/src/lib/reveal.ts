export function splitChunks(text: string, wordsPerChunk: number): string[] {
  if (!text) return [];
  const tokens = text.match(/\S+\s*|\s+/g);
  if (!tokens) return [text];
  const chunks: string[] = [];
  let buf = "";
  let words = 0;
  for (const t of tokens) {
    buf += t;
    if (/\S/.test(t)) words += 1;
    if (words >= wordsPerChunk) {
      chunks.push(buf);
      buf = "";
      words = 0;
    }
  }
  if (buf) chunks.push(buf);
  return chunks;
}

export function splitCharChunks(text: string, charsPerChunk: number): string[] {
  const n = Math.max(1, charsPerChunk);
  const chunks: string[] = [];
  for (let i = 0; i < text.length; i += n) {
    chunks.push(text.slice(i, i + n));
  }
  return chunks;
}

export function revealedAfterSkip(fullText: string): string {
  return fullText;
}
