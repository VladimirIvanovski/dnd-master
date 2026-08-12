import { useState } from "react";
import { AssetPortrait } from "../visual/AssetPortrait";
import { useUiStore } from "../../stores/uiStore";

type Item = {
  item_id?: string;
  name: string;
  quantity: number;
  equipped?: boolean;
  item_type: string;
  description?: string;
};

type Props = {
  items: Item[];
};

export function InventoryPanel({ items }: Props) {
  const tab = useUiStore((s) => s.panelPrefs.inventory?.tab) || "all";
  const setPanelTab = useUiStore((s) => s.setPanelTab);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const filtered =
    tab === "all"
      ? items
      : items.filter((i) => i.item_type.toLowerCase().includes(tab));

  const tabs = [
    { id: "all", label: "All" },
    { id: "weapon", label: "Weapons" },
    { id: "armor", label: "Armor" },
    { id: "consumable", label: "Consumables" },
  ];

  const itemKey = (item: Item) => item.item_id ?? item.name;
  const selected = filtered.find((i) => itemKey(i) === selectedKey) ?? null;

  const toggleItem = (item: Item) => {
    const key = itemKey(item);
    setSelectedKey((cur) => (cur === key ? null : key));
  };

  return (
    <section>
      <p className="label-caps mb-2.5">Inventory</p>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setPanelTab("inventory", t.id)}
            className={`btn-fantasy px-2.5 py-1.5 text-[0.75rem] uppercase tracking-[0.12em] ${
              tab === t.id ? "is-active" : ""
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {items.length === 0 ? (
        <p className="text-base text-muted">Pack is empty.</p>
      ) : (
        <div className="grid grid-cols-4 gap-2.5">
          {filtered.map((item) => {
            const key = itemKey(item);
            const isOpen = selectedKey === key;
            return (
              <button
                key={key}
                type="button"
                title={item.name}
                aria-expanded={isOpen}
                onClick={() => toggleItem(item)}
                className={`flex aspect-square flex-col items-center justify-center gap-1 border p-1.5 text-center transition-[border-color,box-shadow,transform] duration-200 ${
                  isOpen
                    ? "border-accent/55 bg-accent/10 shadow-[0_0_10px_rgba(201,162,39,0.12)]"
                    : "border-accent/20 bg-panel-2/50 hover:-translate-y-0.5 hover:border-accent/40"
                }`}
              >
                {item.item_id ? (
                  <AssetPortrait kind="item" entityId={item.item_id} label={item.name} size={42} />
                ) : (
                  <span className="text-xl text-muted">?</span>
                )}
                <span className="w-full truncate text-xs text-muted">×{item.quantity}</span>
              </button>
            );
          })}
        </div>
      )}
      {selected ? (
        <button
          type="button"
          className="panel-ornate mt-4 w-full p-3.5 text-left"
          onClick={() => setSelectedKey(null)}
          title="Click to collapse"
        >
          <p className="display-text text-base text-accent">{selected.name}</p>
          <p className="mt-1 text-sm text-muted capitalize">{selected.item_type}</p>
          {selected.description ? (
            <p className="mt-2 text-base leading-relaxed text-parchment/85">{selected.description}</p>
          ) : null}
          <p className="mt-2 text-sm text-muted">
            Qty {selected.quantity}
            {selected.equipped ? " · Equipped" : ""}
          </p>
          <p className="mt-2 text-xs uppercase tracking-[0.14em] text-muted/70">
            Click to close
          </p>
        </button>
      ) : null}
    </section>
  );
}
