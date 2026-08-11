type Props = {
  text: string;
};

export function GameEvent({ text }: Props) {
  return (
    <div className="rounded border border-border/80 bg-ink/40 px-3 py-1.5 text-xs uppercase tracking-wide text-muted">
      {text}
    </div>
  );
}
