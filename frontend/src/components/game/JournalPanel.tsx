import type { SceneMessage } from "../../types/game";

type Props = {
  messages: SceneMessage[];
  currentTime?: string;
  checkpoints?: string[];
  onSave?: () => void;
  onLoad?: (name: string) => void;
};

export function JournalPanel({ messages, currentTime, checkpoints = [], onSave, onLoad }: Props) {
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
      {onSave ? (
        <div className="space-y-2 border-b border-border/40 pb-3">
          <button
            type="button"
            className="btn-fantasy w-full px-2 py-1 text-[0.7rem] uppercase tracking-[0.12em]"
            onClick={onSave}
          >
            Save checkpoint
          </button>
          {checkpoints.length ? (
            <div className="flex flex-wrap gap-1">
              {checkpoints.map((name) => (
                <button
                  key={name}
                  type="button"
                  className="rounded border border-border/50 px-1.5 py-0.5 text-[0.65rem] uppercase tracking-[0.08em] text-muted hover:border-accent/50 hover:text-parchment"
                  onClick={() => onLoad?.(name)}
                >
                  Load {name}
                </button>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted">No checkpoints yet.</p>
          )}
        </div>
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
