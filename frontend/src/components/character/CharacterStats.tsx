type Props = {
  name: string;
  race: string;
  className: string;
  level: number;
  xp: number;
  hp: number;
  maxHp: number;
  ac: number;
  gold: number;
  silver: number;
  copper: number;
  abilities: Record<string, number>;
};

export function CharacterStats({
  name,
  race,
  className,
  level,
  xp,
  hp,
  maxHp,
  ac,
  gold,
  silver,
  copper,
  abilities,
}: Props) {
  const hpPct = Math.max(0, Math.min(100, (hp / Math.max(maxHp, 1)) * 100));

  return (
    <div className="space-y-3">
      <div>
        <h2 className="display-text text-lg text-accent">{name}</h2>
        <p className="text-sm text-muted">
          Level {level} {race} {className}
        </p>
      </div>

      <div>
        <div className="mb-1 flex justify-between text-xs text-muted">
          <span>HP</span>
          <span>
            {hp}/{maxHp}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded bg-ink">
          <div
            className="h-full bg-danger transition-all duration-500"
            style={{ width: `${hpPct}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-sm">
        <Stat label="AC" value={ac} />
        <Stat label="XP" value={xp} />
        <Stat label="GP" value={gold} />
      </div>
      <div className="grid grid-cols-2 gap-2 text-center text-sm">
        <Stat label="SP" value={silver} />
        <Stat label="CP" value={copper} />
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        {Object.entries(abilities).map(([key, value]) => (
          <Stat key={key} label={key.slice(0, 3).toUpperCase()} value={value} />
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded border border-border bg-panel-2 px-1.5 py-1">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className="text-sm font-medium">{value}</div>
    </div>
  );
}
