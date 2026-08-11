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
        <Stat label="Gold" value={gold} />
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
    <div className="rounded border border-border bg-panel-2 px-2 py-1.5">
      <div className="text-muted">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}
