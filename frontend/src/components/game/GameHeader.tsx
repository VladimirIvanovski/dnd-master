type Props = {
  campaignName: string;
  time: string;
  weather?: string;
  connectionLabel: string;
  connectionTone: "ok" | "warn" | "bad";
};

export function GameHeader({
  campaignName,
  time,
  weather,
  connectionLabel,
  connectionTone,
}: Props) {
  const tone =
    connectionTone === "ok"
      ? "text-success"
      : connectionTone === "warn"
        ? "text-accent"
        : "text-danger";

  return (
    <header className="panel flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-muted">Campaign</p>
        <h1 className="display-text text-xl text-accent">{campaignName}</h1>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <div className="text-right">
          <p className="text-muted">Time</p>
          <p>{time}{weather ? ` · ${weather}` : ""}</p>
        </div>
        <div className="text-right">
          <p className="text-muted">Link</p>
          <p className={tone}>{connectionLabel}</p>
        </div>
      </div>
    </header>
  );
}
