import { useCallback, useEffect, useRef, useState } from "react";
import { splitCharChunks, splitChunks } from "../lib/reveal";

/** Reveal text in small chunks; call skip() to finish instantly. */
export function useRevealText(
  fullText: string,
  {
    active,
    msPerChunk = 48,
    wordsPerChunk = 1,
    charsPerChunk,
    onDone,
  }: {
    active: boolean;
    msPerChunk?: number;
    wordsPerChunk?: number;
    /** When set, reveal by characters instead of words. */
    charsPerChunk?: number;
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

    const parts =
      charsPerChunk != null
        ? splitCharChunks(fullText, charsPerChunk)
        : splitChunks(fullText, wordsPerChunk);
    let idx = 0;
    timerRef.current = window.setInterval(() => {
      idx += 1;
      setShown(parts.slice(0, idx).join(""));
      if (idx >= parts.length) finish();
    }, msPerChunk);

    return clearTimer;
  }, [fullText, active, msPerChunk, wordsPerChunk, charsPerChunk, finish]);

  return { shown, done, skip: finish };
}
