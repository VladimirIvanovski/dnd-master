import type { ReactNode } from "react";
import { ActionInput } from "./ActionInput";
import { TopBar } from "./TopBar";
import { DockResizeHandle } from "../ui/DockResizeHandle";
import { useUiStore, type PanelId } from "../../stores/uiStore";

type Props = {
  locationName: string;
  time: string;
  weather?: string;
  gold: number;
  hp?: number;
  maxHp?: number;
  xp?: number;
  level?: number;
  connectionTone: "ok" | "warn" | "bad";
  combatMode?: boolean;
  activePanel: PanelId | null;
  onTogglePanel: (id: PanelId) => void;
  busy?: boolean;
  suggestions?: string[];
  onAction: (action: string) => void;
  leftDock?: ReactNode;
  rightDock?: ReactNode;
  children: ReactNode;
  overlays?: ReactNode;
};

export function GameLayout({
  locationName,
  time,
  weather,
  gold,
  hp,
  maxHp,
  xp,
  level,
  connectionTone,
  combatMode,
  activePanel,
  onTogglePanel,
  busy,
  suggestions,
  onAction,
  leftDock,
  rightDock,
  children,
  overlays,
}: Props) {
  const leftW = useUiStore((s) => s.leftDockWidth);
  const rightW = useUiStore((s) => s.rightDockWidth);
  const setLeft = useUiStore((s) => s.setLeftDockWidth);
  const setRight = useUiStore((s) => s.setRightDockWidth);

  return (
    <div className="game-stage-outer flex h-full min-h-0 overflow-hidden">
      <div
        className={`game-stage relative flex h-full w-full flex-col overflow-hidden border border-border/40 bg-ink/50 ${
          combatMode ? "ring-1 ring-inset ring-danger/35" : ""
        }`}
      >
        <TopBar
          locationName={locationName}
          time={time}
          weather={weather}
          gold={gold}
          hp={hp}
          maxHp={maxHp}
          xp={xp}
          level={level}
          connectionTone={connectionTone}
          activePanel={activePanel}
          onTogglePanel={onTogglePanel}
        />
        <div className="flex min-h-0 flex-1 overflow-hidden">
          {leftDock ? (
            <>
              <aside
                className="dock-panel hidden shrink-0 overflow-y-auto border-r border-border/35 p-4 lg:block"
                style={{ width: leftW }}
              >
                {leftDock}
              </aside>
              <DockResizeHandle side="left" onResize={(dx) => setLeft(leftW + dx)} />
            </>
          ) : null}

          <main className="story-stage-main relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
            <div className="action-dock shrink-0 px-4 pb-3 pt-1.5 sm:px-6 md:px-8">
              <ActionInput disabled={busy} suggestions={suggestions} onSubmit={onAction} />
            </div>
          </main>

          {rightDock ? (
            <>
              <DockResizeHandle side="right" onResize={(dx) => setRight(rightW + dx)} />
              <aside
                className="dock-panel dock-panel-secondary hidden shrink-0 overflow-y-auto border-l border-border/35 p-4 lg:flex lg:flex-col lg:gap-4"
                style={{ width: rightW }}
              >
                {rightDock}
              </aside>
            </>
          ) : null}
        </div>
        {overlays}
      </div>
    </div>
  );
}
