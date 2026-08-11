type Combatant = {
  id: string;
  name: string;
  combatant_type: string;
  hp: number;
  max_hp: number;
  ac: number;
  initiative: number;
};

type Props = {
  combat: {
    round_number: number;
    status: string;
    combatants: Combatant[];
  } | null;
};

export function CombatPanel({ combat }: Props) {
  if (!combat) return null;
  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-danger">
        Combat · Round {combat.round_number}
      </p>
      <ul className="space-y-1 text-sm">
        {combat.combatants.map((c) => (
          <li key={c.id} className="flex justify-between rounded border border-danger/30 bg-panel-2 px-2 py-1">
            <span>
              {c.name} <span className="text-xs text-muted">({c.combatant_type})</span>
            </span>
            <span className="text-muted">
              {c.hp}/{c.max_hp} · AC {c.ac}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
