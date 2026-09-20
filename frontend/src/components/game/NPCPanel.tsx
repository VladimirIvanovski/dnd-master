import { AssetPortrait } from "../visual/AssetPortrait";

type Npc = {
  id: string;
  name: string;
  title?: string;
  is_alive?: boolean;
  faction?: string;
  stock?: Array<{ name: string; quantity: number; price: number }>;
  topics?: Array<{ id: string; label: string }>;
  asked?: string[];
  trust?: number;
  fear?: number;
  respect?: number;
};

type Props = {
  npcs: Npc[];
  activeSpeaker?: string | null;
  onAsk?: (npcId: string, topicId: string) => void;
};

export function NPCPanel({ npcs, activeSpeaker, onAsk }: Props) {
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
                    {npc.stock && npc.stock.length > 0 ? (
                      <p className="truncate text-xs text-muted">
                        {npc.stock
                          .slice(0, 3)
                          .map((s) => `${s.name} ${s.price}gp`)
                          .join(" · ")}
                      </p>
                    ) : null}
                    {npc.topics && npc.topics.length > 0 ? (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {npc.topics.slice(0, 4).map((t) => {
                          const asked = (npc.asked || []).includes(t.id);
                          return (
                            <button
                              key={t.id}
                              type="button"
                              disabled={asked || !onAsk}
                              onClick={() => onAsk?.(npc.id, t.id)}
                              className="rounded border border-border/50 px-1.5 py-0.5 text-[0.65rem] uppercase tracking-[0.08em] text-muted hover:border-accent/50 hover:text-parchment disabled:opacity-40"
                            >
                              {t.label || t.id}
                            </button>
                          );
                        })}
                      </div>
                    ) : null}
                    {typeof npc.trust === "number" &&
                    (npc.trust || npc.fear || npc.respect) ? (
                      <p className="truncate text-xs text-muted">
                        Trust {Math.round(npc.trust)} · Fear {Math.round(npc.fear ?? 0)} · Respect{" "}
                        {Math.round(npc.respect ?? 0)}
                      </p>
                    ) : null}
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
