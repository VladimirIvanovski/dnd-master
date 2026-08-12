import { AssetPortrait } from "../visual/AssetPortrait";

type Char = {
  id: string;
  name: string;
  hp: number;
  max_hp: number;
  ac: number;
  class_name?: string;
  level?: number;
};

type Props = {
  character: Char | null;
  onOpenCharacter: () => void;
};

export function PartyPanel({ character, onOpenCharacter }: Props) {
  if (!character) {
    return <p className="text-sm text-muted">No companions at your side.</p>;
  }

  return (
    <div>
      <p className="mb-3 text-xs uppercase tracking-[0.18em] text-muted">Party</p>
      <button
        type="button"
        onClick={onOpenCharacter}
        className="flex w-full items-center gap-3 border border-border/70 bg-panel-2/60 px-3 py-2 text-left hover:border-accent/40"
      >
        <AssetPortrait kind="character" entityId={character.id} label={character.name} size={48} />
        <div className="min-w-0 flex-1">
          <p className="display-text text-sm text-accent">{character.name}</p>
          <p className="text-xs text-muted">
            {character.class_name ? `${character.class_name} · ` : ""}
            {character.hp}/{character.max_hp} HP · AC {character.ac}
          </p>
        </div>
      </button>
    </div>
  );
}
