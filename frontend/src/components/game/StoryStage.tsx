import { useMemo } from "react";
import type { SceneMessage } from "../../types/game";
import { SceneLog } from "./SceneLog";
import { CombatPanel } from "../combat/CombatPanel";
import { AssetPortrait } from "../visual/AssetPortrait";
import { LoadingState } from "../common/LoadingState";

type Npc = {
  id: string;
  name: string;
  title: string;
};

type Props = {
  locationId?: string | null;
  locationName?: string;
  locationType?: string;
  timeOfDay?: string;
  messages: SceneMessage[];
  streamingNarration: string;
  nearbyNpcs: Npc[];
  combat: {
    round_number: number;
    status: string;
    whose_turn?: string;
    can_move?: boolean;
    can_strike?: boolean;
    combatants: Array<{
      id: string;
      name: string;
      combatant_type: string;
      hp: number;
      max_hp: number;
      ac: number;
      initiative: number;
      cover?: number;
      range_ft?: number;
      x?: number;
      y?: number;
    }>;
  } | null;
  busy?: boolean;
  onCombatCommand?: (command: string) => void;
};

export function StoryStage({
  locationName,
  locationType,
  timeOfDay,
  messages,
  streamingNarration,
  nearbyNpcs,
  combat,
  busy,
  onCombatCommand,
}: Props) {
  const activeSpeaker = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.kind === "dialogue") {
        const npc = nearbyNpcs.find(
          (n) => n.name.toLowerCase() === m.speaker.toLowerCase() || m.speaker.includes(n.name),
        );
        return { speaker: m.speaker, npc };
      }
      if (m.kind === "player" || m.kind === "narration") break;
    }
    return null;
  }, [messages, nearbyNpcs]);

  if (combat) {
    return (
      <div className="flex h-full min-h-0 flex-col gap-3 p-3 md:p-4">
        <div className="grid min-h-0 flex-1 gap-3 md:grid-cols-[1.1fr_0.9fr]">
          <div className="flex min-h-0 flex-col border border-danger/25 bg-panel/40 p-3">
            <p className="mb-2 text-xs uppercase tracking-[0.2em] text-danger">Tactical field</p>
            <CombatPanel combat={combat} onCommand={onCombatCommand} disabled={busy} />
          </div>
          <div className="flex min-h-0 flex-col overflow-hidden">
            <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Combat log</p>
            <SceneLog messages={messages.slice(-20)} streamingNarration={streamingNarration} compact />
          </div>
        </div>
        {busy ? <LoadingState label="Resolving the clash…" /> : null}
      </div>
    );
  }

  const tint = timeTintClass(timeOfDay);

  return (
    <div className={`story-heart flex h-full min-h-0 flex-col overflow-hidden ${tint}`}>
      <div className="relative z-[3] flex shrink-0 items-end justify-between gap-3 border-b border-border/30 px-5 py-1.5 md:px-8">
        <div className="min-w-0">
          <p className="display-text truncate text-[0.95rem] tracking-[0.06em] text-accent md:text-base">
            {locationName || "Unknown lands"}
          </p>
          {locationType ? (
            <p className="text-[0.6rem] uppercase tracking-[0.14em] text-muted">{locationType}</p>
          ) : null}
        </div>
        {activeSpeaker ? (
          <div className="flex min-w-0 items-center gap-2">
            {activeSpeaker.npc ? (
              <AssetPortrait
                kind="npc"
                entityId={activeSpeaker.npc.id}
                label={activeSpeaker.npc.name}
                size={36}
              />
            ) : null}
            <div className="min-w-0 text-right">
              <p className="label-caps mb-0.5">Speaking</p>
              <p className="display-text truncate text-sm text-accent">{activeSpeaker.speaker}</p>
            </div>
          </div>
        ) : null}
      </div>

      <div className="relative z-[3] flex min-h-0 flex-1 flex-col overflow-hidden">
        <SceneLog messages={messages} streamingNarration={streamingNarration} />
      </div>

      {busy ? (
        <div className="relative z-[3] shrink-0 px-6 pb-2 md:px-10">
          <LoadingState label="The dungeon master considers your fate…" className="text-sm" />
        </div>
      ) : null}
    </div>
  );
}

function timeTintClass(time?: string): string {
  const t = (time || "").toLowerCase();
  if (t.includes("night") || t.includes("midnight")) return "story-tint-night";
  if (t.includes("dusk") || t.includes("sunset") || t.includes("evening")) return "story-tint-dusk";
  if (t.includes("dawn") || t.includes("morning")) return "story-tint-dawn";
  return "story-tint-day";
}
