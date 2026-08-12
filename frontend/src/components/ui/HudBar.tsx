type Props = {
  label: string;
  icon: string;
  valueText: string;
  pct: number;
  fillClass: string;
  title?: string;
};

export function HudBar({ label, icon, valueText, pct, fillClass, title }: Props) {
  return (
    <div className="min-w-[7rem]" title={title || label}>
      <div className="mb-0.5 flex items-center justify-between gap-2 text-[0.78rem]">
        <span className="flex items-center gap-1 text-muted">
          <span aria-hidden>{icon}</span>
          <span className="uppercase tracking-[0.12em]">{label}</span>
        </span>
        <span className="tabular-nums text-parchment/90">{valueText}</span>
      </div>
      <div className="hud-bar-track">
        <div className={`hud-bar-fill ${fillClass}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
