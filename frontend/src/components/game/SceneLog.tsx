import { useEffect, useRef } from "react";
import type { SceneMessage } from "../../types/game";
import { Dialogue } from "./Dialogue";
import { DiceRoll } from "../dice/DiceRoll";
import { GameEvent } from "./GameEvent";
import { Narration } from "./Narration";

type Props = {
  messages: SceneMessage[];
  streamingNarration: string;
};

export function SceneLog({ messages, streamingNarration }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingNarration]);

  return (
    <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
      {messages.length === 0 && !streamingNarration ? (
        <p className="story-text text-muted">
          The scene awaits your first action. Speak, explore, or draw steel.
        </p>
      ) : null}

      {messages.map((msg) => {
        if (msg.kind === "player") {
          return (
            <div key={msg.id} className="ml-auto max-w-[85%] rounded-lg border border-border bg-panel px-3 py-2 text-sm">
              <p className="text-xs uppercase tracking-wide text-muted">You</p>
              <p>{msg.text}</p>
            </div>
          );
        }
        if (msg.kind === "narration") {
          return (
            <div key={msg.id} className="max-w-3xl">
              <Narration text={msg.text} />
            </div>
          );
        }
        if (msg.kind === "dialogue") {
          return <Dialogue key={msg.id} speaker={msg.speaker} text={msg.text} />;
        }
        if (msg.kind === "dice") {
          return <DiceRoll key={msg.id} result={msg.result} />;
        }
        if (msg.kind === "event") {
          return <GameEvent key={msg.id} text={msg.text} />;
        }
        return (
          <p key={msg.id} className="text-sm text-danger">
            {msg.text}
          </p>
        );
      })}

      {streamingNarration ? (
        <div className="max-w-3xl">
          <Narration text={streamingNarration} streaming />
        </div>
      ) : null}
      <div ref={endRef} />
    </div>
  );
}
