import { cellIntent, combatFlagLine, heroOf, isYourTurn } from "../../lib/combatGrid";

type Combatant = {
  id: string;
  name: string;
  combatant_type: string;
  hp: number;
  max_hp: number;
  ac: number;
  initiative: number;
  cover?: number;
  range_ft?: number;
  x?: number;
  y?: number;
};

type Props = {
  combat: {
    round_number: number;
    status: string;
    whose_turn?: string;
    can_move?: boolean;
    can_strike?: boolean;
    combatants: Combatant[];
  } | null;
  onCommand?: (command: string) => void;
  disabled?: boolean;
};

export function CombatPanel({ combat, onCommand, disabled }: Props) {
  if (!combat) return null;
  const acting = (combat.whose_turn || "").toLowerCase();
  const hero = heroOf(combat);
  const yourTurn = isYourTurn(combat);
  const at = (x: number, y: number) =>
    combat.combatants.filter((c) => (c.x ?? 3) === x && (c.y ?? 3) === y);
  const canAct = Boolean(onCommand) && !disabled && yourTurn;

  const clickCell = (x: number, y: number) => {
    if (!canAct || !hero) return;
    const intent = cellIntent(combat, x, y);
    if (intent === "strike") {
      const foe = at(x, y).find((c) => c.combatant_type === "enemy" || c.combatant_type === "npc");
      if (foe) onCommand?.(`sys:strike:${foe.id}`);
      return;
    }
    if (intent === "move") {
      onCommand?.(`sys:move:${x - (hero.x ?? 3)}:${y - (hero.y ?? 3)}`);
    }
  };

  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-danger">
        {combatFlagLine(combat)}
      </p>
      <div className="mb-3 grid grid-cols-8 gap-0.5">
        {Array.from({ length: 64 }, (_, i) => {
          const x = i % 8;
          const y = Math.floor(i / 8);
          const here = at(x, y);
          const isTurn = here.some((c) => c.name.toLowerCase() === acting);
          const clickable = canAct && cellIntent(combat, x, y) !== null;
          return (
            <button
              key={i}
              type="button"
              disabled={!clickable}
              onClick={() => clickCell(x, y)}
              className={`flex h-7 items-center justify-center rounded border text-[0.6rem] ${
                isTurn
                  ? "border-danger bg-danger/20 text-parchment"
                  : here.length
                    ? "border-accent/40 bg-panel-2 text-accent"
                    : "border-border/40 bg-ink/40 text-muted"
              } ${clickable ? "cursor-pointer hover:border-accent" : ""}`}
              title={here.map((c) => c.name).join(", ") || `${x},${y}`}
            >
              {here[0] ? here[0].name.slice(0, 2) : ""}
            </button>
          );
        })}
      </div>
      {canAct ? (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {combat.can_move !== false
            ? (
                [
                  ["N", 0, -1],
                  ["S", 0, 1],
                  ["W", -1, 0],
                  ["E", 1, 0],
                ] as const
              ).map(([label, dx, dy]) => (
                <button
                  key={label}
                  type="button"
                  className="btn-fantasy px-2 py-1 text-[0.7rem] uppercase tracking-[0.12em]"
                  onClick={() => onCommand?.(`sys:move:${dx}:${dy}`)}
                >
                  {label}
                </button>
              ))
            : null}
          {combat.can_strike !== false
            ? combat.combatants
                .filter((c) => c.combatant_type === "enemy" || c.combatant_type === "npc")
                .map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    className="btn-fantasy px-2 py-1 text-[0.7rem] uppercase tracking-[0.12em]"
                    onClick={() => onCommand?.(`sys:strike:${c.id}`)}
                  >
                    Strike {c.name}
                  </button>
                ))
            : null}
          <button
            type="button"
            className="btn-fantasy px-2 py-1 text-[0.7rem] uppercase tracking-[0.12em]"
            onClick={() => onCommand?.("sys:advance")}
          >
            End turn
          </button>
        </div>
      ) : (
        <p className="mb-2 text-xs text-muted">Wait for your turn.</p>
      )}
      <ul className="space-y-1 text-sm">
        {combat.combatants.map((c) => (
          <li key={c.id} className="flex justify-between text-muted">
            <span className={c.name.toLowerCase() === acting ? "text-danger" : ""}>
              {c.name}
            </span>
            <span>
              {c.hp}/{c.max_hp} · {c.range_ft ?? 0}ft
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
