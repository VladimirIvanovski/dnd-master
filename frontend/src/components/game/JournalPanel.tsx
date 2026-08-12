import type { SceneMessage } from "../../types/game";

type Props = {
  messages: SceneMessage[];
  currentTime?: string;
};

export function JournalPanel({ messages, currentTime }: Props) {
  const entries = messages.filter(
    (m) => m.kind === "narration" || m.kind === "player" || m.kind === "event" || m.kind === "dialogue",
  );

  return (
    <div className="journal-parchment space-y-4">
      <p className="display-text text-center text-sm tracking-[0.15em] text-accent-soft">
        Personal Journal
      </p>
      {currentTime ? (
        <p className="text-center text-xs uppercase tracking-widest text-muted">{currentTime}</p>
      ) : null}
      {entries.length === 0 ? (
        <p className="text-sm italic text-muted">The pages are blank. Your tale awaits.</p>
      ) : (
        <ul className="space-y-4">
          {entries.map((m) => (
            <li key={m.id} className="border-b border-border/40 pb-3 last:border-0">
              {m.kind === "narration" ? (
                <p className="story-text text-sm leading-relaxed">{m.text}</p>
              ) : null}
              {m.kind === "player" ? (
                <p className="text-sm italic text-muted">I: {m.text}</p>
              ) : null}
              {m.kind === "dialogue" ? (
                <p className="text-sm">
                  <span className="text-accent">{m.speaker}:</span> “{m.text}”
                </p>
              ) : null}
              {m.kind === "event" ? (
                <p className="text-xs uppercase tracking-wide text-muted">{m.text}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
