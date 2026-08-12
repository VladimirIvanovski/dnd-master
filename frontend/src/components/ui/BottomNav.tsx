import type { PanelId } from "../../stores/uiStore";

const ITEMS: Array<{ id: PanelId; label: string; icon: string; tip: string }> = [
  // { id: "map", label: "Map", icon: "🗺", tip: "World map" },
  { id: "party", label: "Party", icon: "⚔", tip: "Your companions" },
  { id: "character", label: "Character", icon: "⚜", tip: "Character sheet" },
  { id: "inventory", label: "Inventory", icon: "🎒", tip: "Pack and gear" },
  { id: "quests", label: "Quests", icon: "📜", tip: "Active quests" },
  { id: "journal", label: "Journal", icon: "📔", tip: "Adventure journal" },
];

type Props = {
  active: PanelId | null;
  onToggle: (id: PanelId) => void;
  /** Compact icon rail for the top bar */
  variant?: "top" | "bottom";
};

export function BottomNav({ active, onToggle, variant = "top" }: Props) {
  if (variant === "top") {
    return (
      <nav className="flex items-center gap-1" aria-label="Game systems">
        {ITEMS.map((item) => {
          const isOn = active === item.id;
          return (
            <button
              key={item.id}
              type="button"
              title={`${item.label} — ${item.tip}`}
              aria-label={item.label}
              aria-pressed={isOn}
              onClick={() => onToggle(item.id)}
              className={`btn-fantasy group relative flex h-9 w-9 items-center justify-center text-base transition duration-200 ${
                isOn ? "is-active" : "text-parchment/80 hover:text-accent"
              }`}
            >
              <span aria-hidden>{item.icon}</span>
              <span className="pointer-events-none absolute left-1/2 top-full z-30 mt-1.5 -translate-x-1/2 whitespace-nowrap rounded border border-accent/30 bg-ink/95 px-2 py-0.5 text-[0.6rem] uppercase tracking-[0.14em] text-parchment opacity-0 shadow-lg transition group-hover:opacity-100">
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>
    );
  }

  return (
    <nav
      className="flex flex-wrap items-center justify-center gap-2 sm:gap-3"
      aria-label="Game systems"
    >
      {ITEMS.map((item) => {
        const isOn = active === item.id;
        return (
          <button
            key={item.id}
            type="button"
            title={item.tip}
            aria-label={item.label}
            aria-pressed={isOn}
            onClick={() => onToggle(item.id)}
            className={`btn-fantasy flex min-w-[4.75rem] flex-col items-center gap-1 px-3 py-2 text-[0.68rem] uppercase tracking-[0.14em] sm:min-w-[5.5rem] ${
              isOn ? "is-active" : ""
            }`}
          >
            <span className="text-lg leading-none text-accent" aria-hidden>
              {item.icon}
            </span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
