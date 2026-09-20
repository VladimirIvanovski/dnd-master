import { useCallback, useEffect, useRef, useState } from "react";
import type { SceneMessage } from "../../types/game";
import { Dialogue } from "./Dialogue";
import { DiceRoll } from "../dice/DiceRoll";
import { GameEvent } from "./GameEvent";
import { Narration } from "./Narration";
import { playerActionLabel } from "../../lib/sysAction";

type Props = {
  messages: SceneMessage[];
  streamingNarration: string;
  compact?: boolean;
};

function isStoryBeat(m: SceneMessage): boolean {
  return m.kind === "narration" || m.kind === "dialogue";
}

export function SceneLog({ messages, streamingNarration, compact }: Props) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const revealedRef = useRef(new Set<string>());
  const seededRef = useRef(false);
  const skipFnRef = useRef<(() => void) | null>(null);
  const [, bump] = useState(0);

  const markRevealed = useCallback((id: string) => {
    if (revealedRef.current.has(id)) return;
    revealedRef.current.add(id);
    bump((n) => n + 1);
  }, []);

  // First non-empty message load: history = instant; opening-only = typewriter
  useEffect(() => {
    if (seededRef.current || messages.length === 0) return;
    seededRef.current = true;
    const narrations = messages.filter((m) => m.kind === "narration");
    const hasHistory =
      messages.some((m) => m.kind === "player") || narrations.length > 1;
    if (hasHistory) {
      for (const m of messages) revealedRef.current.add(m.id);
    } else {
      for (const m of messages) {
        if (!isStoryBeat(m)) revealedRef.current.add(m.id);
      }
    }
    bump((n) => n + 1);
  }, [messages]);

  const activeRevealId =
    messages.find((m) => isStoryBeat(m) && !revealedRef.current.has(m.id))?.id ?? null;

  const bindSkip = useCallback((fn: () => void) => {
    skipFnRef.current = fn;
  }, []);

  const skipReveal = useCallback(() => {
    skipFnRef.current?.();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!activeRevealId) return;
      if (e.key !== " " && e.key !== "Enter" && e.key !== "Escape") return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable) {
        return;
      }
      e.preventDefault();
      skipReveal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeRevealId, skipReveal]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || !stickToBottom.current) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, streamingNarration, activeRevealId]);

  return (
    <div
      ref={scrollerRef}
      className={`story-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain ${
        compact ? "space-y-3 px-2 py-2" : "space-y-5 px-5 py-3 md:px-8 md:py-4"
      }`}
      onScroll={() => {
        const el = scrollerRef.current;
        if (!el) return;
        const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
        stickToBottom.current = dist < 80;
      }}
      onClick={() => {
        if (activeRevealId) skipReveal();
      }}
      role="log"
      aria-live="polite"
      title={activeRevealId ? "Click or press Space to skip" : undefined}
    >
      {messages.length === 0 && !streamingNarration ? (
        <div className="story-column">
          <p className="story-text text-center text-lg leading-relaxed text-muted">
            The scene awaits your first action.
          </p>
        </div>
      ) : null}

      {messages.map((msg, idx) => {
        const prev = messages[idx - 1];
        const majorBeat =
          msg.kind === "narration" &&
          prev &&
          (prev.kind === "player" || prev.kind === "dialogue" || prev.kind === "event");
        const revealed = revealedRef.current.has(msg.id);
        const revealing = activeRevealId === msg.id;
        // Queue later story beats so they don't flash full text early
        if (isStoryBeat(msg) && !revealed && !revealing) return null;

        if (msg.kind === "player") {
          const shown = playerActionLabel(msg.text);
          return (
            <div key={msg.id} className="story-column ml-auto mr-0 max-w-lg text-right">
              <p className="text-[0.62rem] uppercase tracking-[0.2em] text-muted">You</p>
              <p className="story-text mt-1 text-[1.02rem] italic leading-relaxed text-parchment/65">
                {shown}
              </p>
            </div>
          );
        }
        if (msg.kind === "narration") {
          return (
            <div key={msg.id} className="story-column">
              {majorBeat ? <div className="story-beat-rule" aria-hidden /> : null}
              <Narration
                text={msg.text}
                reveal={revealing}
                onRevealDone={() => markRevealed(msg.id)}
                onSkipReady={revealing ? bindSkip : undefined}
              />
            </div>
          );
        }
        if (msg.kind === "dialogue") {
          return (
            <div key={msg.id} className="story-column">
              <Dialogue
                speaker={msg.speaker}
                text={msg.text}
                reveal={revealing}
                onRevealDone={() => markRevealed(msg.id)}
                onSkipReady={revealing ? bindSkip : undefined}
              />
            </div>
          );
        }
        if (msg.kind === "dice") {
          return (
            <div key={msg.id} className="story-column">
              <DiceRoll result={msg.result} compact />
            </div>
          );
        }
        if (msg.kind === "event") {
          return (
            <div key={msg.id} className="story-column opacity-75">
              <GameEvent text={msg.text} />
            </div>
          );
        }
        return (
          <p key={msg.id} className="story-column text-center text-sm text-danger">
            {msg.text}
          </p>
        );
      })}

      {streamingNarration ? (
        <div className="story-column">
          <Narration text={streamingNarration} streaming />
        </div>
      ) : null}

      {activeRevealId ? (
        <p className="story-column pt-1 text-center text-[0.65rem] tracking-[0.14em] text-muted/70">
          Click or Space — skip
        </p>
      ) : null}
    </div>
  );
}
