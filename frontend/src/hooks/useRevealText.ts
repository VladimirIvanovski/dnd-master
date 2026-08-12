import { useCallback, useEffect, useRef, useState } from "react";

/** Reveal text in small word chunks; call skip() to finish instantly. */
export function useRevealText(
  fullText: string,
  {
    active,
    msPerChunk = 32,
    wordsPerChunk = 2,
    onDone,
  }: {
    active: boolean;
    msPerChunk?: number;
    wordsPerChunk?: number;
    onDone?: () => void;
  },
) {
  const [shown, setShown] = useState(() => (active ? "" : fullText));
  const [done, setDone] = useState(!active);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;
  const textRef = useRef(fullText);
  textRef.current = fullText;
  const timerRef = useRef<number | null>(null);
  const finishedRef = useRef(!active);

  const clearTimer = () => {
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const finish = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    clearTimer();
    setShown(textRef.current);
    setDone(true);
    onDoneRef.current?.();
  }, []);

  useEffect(() => {
    finishedRef.current = false;
    clearTimer();

    if (!active) {
      setShown(fullText);
      setDone(true);
      finishedRef.current = true;
      return;
    }

    setShown("");
    setDone(false);
    if (!fullText) {
      finish();
      return;
    }

    const parts = splitChunks(fullText, wordsPerChunk);
    let idx = 0;
    timerRef.current = window.setInterval(() => {
      idx += 1;
      setShown(parts.slice(0, idx).join(""));
      if (idx >= parts.length) finish();
    }, msPerChunk);

    return clearTimer;
  }, [fullText, active, msPerChunk, wordsPerChunk, finish]);

  return { shown, done, skip: finish };
}

function splitChunks(text: string, wordsPerChunk: number): string[] {
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
