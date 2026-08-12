import { AssetPortrait } from "../visual/AssetPortrait";

type Npc = {
  id: string;
  name: string;
  title?: string;
  is_alive?: boolean;
};

type Props = {
  npcs: Npc[];
  activeSpeaker?: string | null;
};

export function NPCPanel({ npcs, activeSpeaker }: Props) {
  const present = npcs.filter((n) => n.is_alive !== false);
  return (
    <section>
      <p className="label-caps mb-2.5">People nearby</p>
      {present.length === 0 ? (
        <p className="text-sm text-muted">No one nearby.</p>
      ) : (
        <ul className="space-y-2">
          {present.map((npc) => {
            const important =
              activeSpeaker &&
              (npc.name.toLowerCase() === activeSpeaker.toLowerCase() ||
                activeSpeaker.toLowerCase().includes(npc.name.toLowerCase()));
            return (
              <li key={npc.id}>
                <div
                  className={`npc-card flex w-full items-center gap-3 px-2 py-2 ${
                    important ? "is-active" : ""
                  }`}
                  title={npc.title || npc.name}
                >
                  <AssetPortrait kind="npc" entityId={npc.id} label={npc.name} size={56} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-base text-parchment">{npc.name}</p>
                    <p className="truncate text-sm text-muted">{npc.title || "Unknown"}</p>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
