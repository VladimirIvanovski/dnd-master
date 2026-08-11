import type { ReactNode } from "react";
import { CharacterStats } from "./CharacterStats";

type Props = {
  character: {
    name: string;
    race: string;
    class_name: string;
    level: number;
    xp: number;
    hp: number;
    max_hp: number;
    ac: number;
    gold: number;
    abilities: Record<string, number>;
  } | null;
  questsSlot?: ReactNode;
};

export function CharacterPanel({ character, questsSlot }: Props) {
  if (!character) {
    return <p className="text-sm text-muted">No character loaded.</p>;
  }

  return (
    <div className="space-y-4">
      <section>
        <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Character</p>
        <CharacterStats
          name={character.name}
          race={character.race}
          className={character.class_name}
          level={character.level}
          xp={character.xp}
          hp={character.hp}
          maxHp={character.max_hp}
          ac={character.ac}
          gold={character.gold}
          abilities={character.abilities}
        />
      </section>
      {questsSlot}
    </div>
  );
}
