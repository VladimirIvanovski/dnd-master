import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { BottomNav } from "../ui/BottomNav";
import { formatGameTime, weatherIcon } from "../../lib/hud";
import type { PanelId } from "../../stores/uiStore";

type Props = {
  locationName: string;
  time: string;
  weather?: string;
  gold: number;
  connectionTone: "ok" | "warn" | "bad";
  hp?: number;
  maxHp?: number;
  xp?: number;
  level?: number;
  activePanel?: PanelId | null;
  onTogglePanel?: (id: PanelId) => void;
};

export function TopBar({
  locationName,
  time,
  weather,
  gold,
  connectionTone,
  xp = 0,
  level = 1,
  activePanel = null,
  onTogglePanel,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [gain, setGain] = useState<string | null>(null);
  const [levelUp, setLevelUp] = useState(false);
  const prev = useRef({ gold, xp, level });

  useEffect(() => {
    const p = prev.current;
    if (gold > p.gold) setGain(`+${gold - p.gold} GP`);
    else if (xp > p.xp) setGain(`+${xp - p.xp} XP`);
    if (level > p.level) {
      setLevelUp(true);
      const t = window.setTimeout(() => setLevelUp(false), 1400);
      prev.current = { gold, xp, level };
      return () => window.clearTimeout(t);
    }
    prev.current = { gold, xp, level };
  }, [gold, xp, level]);

  useEffect(() => {
    if (!gain) return;
    const t = window.setTimeout(() => setGain(null), 1200);
    return () => window.clearTimeout(t);
  }, [gain]);

  const dot =
    connectionTone === "ok"
      ? "bg-success"
      : connectionTone === "warn"
        ? "bg-accent"
        : "bg-danger";

  return (
    <header className="relative flex shrink-0 items-center justify-between gap-3 border-b border-accent/20 bg-gradient-to-b from-[#1a1712]/90 to-[#0e1016]/95 px-4 py-2.5">
      <div className="min-w-0">
        <h1 className="display-text truncate text-base text-accent sm:text-lg">{locationName}</h1>
        <p className="flex items-center gap-1.5 truncate text-xs text-muted">
          <span aria-hidden>{weatherIcon(weather)}</span>
          <span>
            {formatGameTime(time)}
            {weather ? ` · ${weather}` : ""}
          </span>
        </p>
      </div>

      <div className="relative flex shrink-0 items-center gap-2 sm:gap-3">
        {gain ? <span className="float-gain">{gain}</span> : null}
        {levelUp ? <span className="level-flare" aria-hidden /> : null}
        {onTogglePanel ? (
          <BottomNav active={activePanel} onToggle={onTogglePanel} variant="top" />
        ) : null}
        <span className={`h-2 w-2 rounded-full ${dot}`} title="Connection" aria-hidden />
        <div className="relative">
          <button
            type="button"
            className="btn-fantasy px-2 py-1 text-muted hover:text-accent"
            aria-label="Menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            ☰
          </button>
          {menuOpen ? (
            <div className="panel-ornate absolute right-0 top-full z-20 mt-2 min-w-[10rem] py-1">
              <Link
                to="/"
                className="block px-3 py-2 text-sm text-muted hover:bg-panel-2 hover:text-accent"
                onClick={() => setMenuOpen(false)}
              >
                Leave table
              </Link>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
