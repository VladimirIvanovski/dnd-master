type Npc = {
  id: string;
  name: string;
  title?: string;
  is_alive?: boolean;
};

type Props = {
  npcs: Npc[];
};

export function NPCPanel({ npcs }: Props) {
  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Nearby NPCs</p>
      {npcs.length === 0 ? (
        <p className="text-sm text-muted">No one nearby.</p>
      ) : (
        <ul className="space-y-2">
          {npcs.map((npc) => (
            <li key={npc.id} className="rounded border border-border bg-panel-2 px-2 py-1.5 text-sm">
              <p className="font-medium">{npc.name}</p>
              <p className="text-xs text-muted">
                {npc.title || "Unknown"}
                {npc.is_alive === false ? " · fallen" : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
