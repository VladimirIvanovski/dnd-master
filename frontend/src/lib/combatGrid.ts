export type GridCombatant = {
  id: string;
  name: string;
  combatant_type: string;
  x?: number;
  y?: number;
};

export type GridCombat = {
  whose_turn?: string;
  can_move?: boolean;
  can_strike?: boolean;
  combatants: GridCombatant[];
};

export function heroOf(combat: GridCombat): GridCombatant | undefined {
  return combat.combatants.find(
    (c) => c.combatant_type === "player" || c.combatant_type === "character",
  );
}

export function isYourTurn(combat: GridCombat): boolean {
  const hero = heroOf(combat);
  return Boolean(hero && hero.name.toLowerCase() === (combat.whose_turn || "").toLowerCase());
}

export function cellIntent(
  combat: GridCombat,
  x: number,
  y: number,
): "strike" | "move" | null {
  const hero = heroOf(combat);
  if (!hero || !isYourTurn(combat)) return null;
  const here = combat.combatants.filter((c) => (c.x ?? 3) === x && (c.y ?? 3) === y);
  const foe = here.find((c) => c.combatant_type === "enemy" || c.combatant_type === "npc");
  const dist = Math.max(Math.abs(x - (hero.x ?? 3)), Math.abs(y - (hero.y ?? 3)));
  if (foe && combat.can_strike !== false) return "strike";
  if (!foe && dist === 1 && combat.can_move !== false) return "move";
  return null;
}

export function combatFlagLine(combat: {
  round_number: number;
  whose_turn?: string;
  can_move?: boolean;
  can_strike?: boolean;
}): string {
  let line = `Combat · Round ${combat.round_number}`;
  if (combat.whose_turn) line += ` · ${combat.whose_turn}`;
  if (combat.can_move === false) line += " · moved";
  if (combat.can_strike === false) line += " · struck";
  return line;
}
