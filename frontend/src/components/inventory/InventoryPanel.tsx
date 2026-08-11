type Item = {
  item_id?: string;
  name: string;
  quantity: number;
  equipped?: boolean;
  item_type: string;
};

type Props = {
  items: Item[];
};

const GROUPS: Array<{ key: string; label: string; match: (t: string) => boolean }> = [
  { key: "weapon", label: "Weapons", match: (t) => t.includes("weapon") },
  { key: "armor", label: "Armor", match: (t) => t.includes("armor") },
  { key: "consumable", label: "Consumables", match: (t) => t.includes("consumable") || t.includes("potion") },
  { key: "quest", label: "Quest Items", match: (t) => t.includes("quest") },
  { key: "misc", label: "Miscellaneous", match: () => true },
];

export function InventoryPanel({ items }: Props) {
  const used = new Set<string>();
  const grouped = GROUPS.map((group) => {
    const list = items.filter((item) => {
      const id = item.item_id ?? item.name;
      if (used.has(id)) return false;
      if (group.key === "misc") {
        used.add(id);
        return true;
      }
      if (group.match(item.item_type.toLowerCase())) {
        used.add(id);
        return true;
      }
      return false;
    });
    return { ...group, list };
  }).filter((g) => g.list.length > 0);

  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Inventory</p>
      {items.length === 0 ? (
        <p className="text-sm text-muted">Pack is empty.</p>
      ) : (
        <div className="space-y-3">
          {grouped.map((group) => (
            <div key={group.key}>
              <p className="mb-1 text-xs text-accent-soft">{group.label}</p>
              <ul className="space-y-1 text-sm">
                {group.list.map((item) => (
                  <li
                    key={item.item_id ?? item.name}
                    className="flex items-center justify-between rounded border border-border/70 bg-panel-2 px-2 py-1"
                  >
                    <span>
                      {item.name}
                      {item.equipped ? <span className="ml-2 text-xs text-accent">eq</span> : null}
                    </span>
                    <span className="text-muted">×{item.quantity}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
