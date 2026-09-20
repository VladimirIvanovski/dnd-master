import { CharacterStats } from "./CharacterStats";
import { AssetPortrait } from "../visual/AssetPortrait";
import { HudBar } from "../ui/HudBar";
import { useUiStore } from "../../stores/uiStore";
import { xpProgress } from "../../lib/hud";

type Props = {
  character: {
    id?: string;
    name: string;
    race: string;
    class_name: string;
    level: number;
    xp: number;
    hp: number;
    max_hp: number;
    temp_hp?: number;
    ac: number;
    gold: number;
    silver?: number;
    copper?: number;
    abilities: Record<string, number>;
    conditions?: string[];
    stamina?: number;
    hunger?: number;
    thirst?: number;
    carry_weight?: number;
    carry_capacity?: number;
    death_saves_success?: number;
    death_saves_fail?: number;
  } | null;
  inventory?: Array<{
    item_id?: string;
    name: string;
    quantity: number;
    equipped?: boolean;
    item_type: string;
    durability?: number | null;
  }>;
};

export function CharacterPanel({ character, inventory = [] }: Props) {
  const tab = useUiStore((s) => s.panelPrefs.character?.tab) || "overview";
  const setPanelTab = useUiStore((s) => s.setPanelTab);

  if (!character) {
    return <p className="text-sm text-muted">No character loaded.</p>;
  }

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "stats", label: "Stats" },
    { id: "equipment", label: "Equipment" },
    { id: "abilities", label: "Abilities" },
  ];
  const xpInfo = xpProgress(character.level, character.xp);
  const hpMax = Math.max(character.max_hp, 1);
  const hpPct = Math.max(0, Math.min(100, (character.hp / hpMax) * 100));
  const tempHp = character.temp_hp ?? 0;
  const equipped = inventory.filter((i) => i.equipped);
  const conditions = character.conditions ?? [];

  return (
    <section className="character-panel">
      <div className="mb-3 flex items-start gap-3">
        {character.id ? (
          <AssetPortrait kind="character" entityId={character.id} label={character.name} size={88} />
        ) : null}
        <div className="min-w-0 flex-1">
          <p className="display-text text-xl text-accent md:text-[1.35rem]">{character.name}</p>
          <p className="text-sm text-muted">
            Lv {character.level} {character.race} {character.class_name}
          </p>
          <div className="mt-2.5 space-y-1.5">
            <HudBar
              label="HP"
              icon="♥"
              valueText={
                tempHp > 0
                  ? `${character.hp}/${character.max_hp} +${tempHp}`
                  : `${character.hp}/${character.max_hp}`
              }
              pct={hpPct}
              fillClass="bg-gradient-to-r from-[#6a1c1c] to-[#c45c5c]"
            />
            <p className="text-sm text-muted">AC {character.ac}</p>
            {conditions.length ? (
              <p className="text-xs uppercase tracking-[0.12em] text-danger/80">
                {conditions.join(" · ")}
              </p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-1.5">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setPanelTab("character", t.id)}
            className={`btn-fantasy px-2.5 py-1 text-[0.72rem] uppercase tracking-[0.12em] ${
              tab === t.id ? "is-active" : ""
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <div className="space-y-2.5 text-base">
          <HudBar
            label="XP"
            icon="✦"
            valueText={xpInfo.label}
            pct={xpInfo.pct}
            fillClass="bg-gradient-to-r from-[#4a3a2a] to-[#a89050]"
          />
          <div className="flex flex-wrap gap-3 text-sm text-muted">
            <span>
              <span className="text-accent-soft">{character.gold}</span> GP
            </span>
            <span>
              <span className="text-parchment/75">{character.silver ?? 0}</span> SP
            </span>
            <span>
              <span className="text-parchment/65">{character.copper ?? 0}</span> CP
            </span>
          </div>
          {character.carry_capacity ? (
            <p className="text-xs text-muted">
              Pack {character.carry_weight ?? 0}/{character.carry_capacity}
            </p>
          ) : null}
          <p className="text-xs text-muted">
            Stamina {character.stamina ?? 100} · Hunger {character.hunger ?? 0} · Thirst{" "}
            {character.thirst ?? 0}
          </p>
          {character.hp <= 0 ? (
            <p className="text-xs text-danger">
              Death saves {character.death_saves_success ?? 0} ok / {character.death_saves_fail ?? 0} fail
            </p>
          ) : null}
        </div>
      ) : null}

      {tab === "stats" ? (
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
          silver={character.silver ?? 0}
          copper={character.copper ?? 0}
          abilities={character.abilities}
        />
      ) : null}

      {tab === "equipment" ? (
        equipped.length === 0 ? (
          <p className="text-sm text-muted">Nothing equipped yet.</p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {equipped.map((item) => (
              <li
                key={item.item_id ?? item.name}
                className="flex justify-between border border-accent/20 bg-panel-2/50 px-2 py-1"
              >
                <span>{item.name}</span>
                <span className="uppercase tracking-wide text-muted">{item.item_type}</span>
              </li>
            ))}
          </ul>
        )
      ) : null}

      {tab === "abilities" ? (
        <ul className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(character.abilities).map(([k, v]) => (
            <li
              key={k}
              className="flex justify-between border border-accent/20 bg-panel-2/50 px-2 py-1"
            >
              <span className="uppercase tracking-wide text-muted">{k.slice(0, 3)}</span>
              <span className="text-accent">{v}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
