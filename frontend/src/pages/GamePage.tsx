import { useEffect, useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { campaignApi, characterApi, gameplayApi, questApi } from "../api";
import { ActionInput } from "../components/game/ActionInput";
import { CharacterPanel } from "../components/character/CharacterPanel";
import { CombatPanel } from "../components/combat/CombatPanel";
import { ErrorState } from "../components/common/ErrorState";
import { GameHeader } from "../components/game/GameHeader";
import { GameLayout } from "../components/game/GameLayout";
import { InventoryPanel } from "../components/inventory/InventoryPanel";
import { LoadingState } from "../components/common/LoadingState";
import { LocationPanel } from "../components/map/LocationPanel";
import { MapPanel } from "../components/map/MapPanel";
import { NPCPanel } from "../components/game/NPCPanel";
import { QuestPanel } from "../components/quests/QuestPanel";
import { SceneLog } from "../components/game/SceneLog";
import { useGameStore } from "../stores/gameStore";

export function GamePage() {
  const { campaignId = "", characterId = "" } = useParams();
  const {
    campaign,
    character,
    state,
    quests,
    messages,
    streamingNarration,
    connection,
    busy,
    error,
    setSession,
    setStateSnapshot,
    setQuests,
    setError,
    seedOpening,
    connect,
    disconnect,
    sendAction,
    clearScene,
  } = useGameStore();

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        setError(null);
        clearScene();
        const [camp, char, questList, snapshot, opening] = await Promise.all([
          campaignApi.get(campaignId),
          characterApi.get(characterId),
          questApi.list(campaignId, characterId),
          gameplayApi.state(campaignId, characterId),
          gameplayApi.opening(campaignId),
        ]);
        if (cancelled) return;
        setSession(camp, char);
        setQuests(questList);
        setStateSnapshot(snapshot);
        localStorage.setItem(
          "dnd-session",
          JSON.stringify({ campaignId, characterId }),
        );
        if (opening.opening_narration && !opening.opening_delivered) {
          seedOpening(opening.opening_narration, opening.tone);
          void gameplayApi.ackOpening(campaignId);
        }
        connect();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load game");
        }
      }
    }

    if (campaignId && characterId) {
      void boot();
    }
    return () => {
      cancelled = true;
      disconnect();
    };
  }, [
    campaignId,
    characterId,
    clearScene,
    connect,
    disconnect,
    setError,
    seedOpening,
    connect,
    disconnect,
    setQuests,
    setSession,
    setStateSnapshot,
  ]);

  const connectionMeta = useMemo(() => {
    if (connection === "connected") return { label: "Connected", tone: "ok" as const };
    if (connection === "connecting") return { label: "Connecting…", tone: "warn" as const };
    if (connection === "disconnected") return { label: "Reconnecting…", tone: "warn" as const };
    if (connection === "error") return { label: "Connection error", tone: "bad" as const };
    return { label: "Idle", tone: "warn" as const };
  }, [connection]);

  if (!campaignId || !characterId) {
    return (
      <div className="p-8">
        <ErrorState title="Invalid session" message="Campaign or character id is missing." />
      </div>
    );
  }

  if (!campaign || !character || !state) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        {error ? (
          <ErrorState
            title="Campaign not found"
            message={error}
            onRetry={() => window.location.reload()}
          />
        ) : (
          <LoadingState label="Opening the campaign ledger…" />
        )}
      </div>
    );
  }

  const snapshot = state;

  return (
    <div className="h-full">
      <GameLayout
        header={
          <GameHeader
            campaignName={snapshot.campaign_name || campaign.name}
            time={snapshot.current_time || campaign.current_time}
            weather={snapshot.weather || campaign.weather}
            connectionLabel={connectionMeta.label}
            connectionTone={connectionMeta.tone}
          />
        }
        left={
          <CharacterPanel
            character={snapshot.character}
            questsSlot={
              <div className="mt-4">
                <QuestPanel quests={quests.length ? quests : snapshot.active_quests} />
              </div>
            }
          />
        }
        center={
          <div className="flex h-full min-h-0 flex-col bg-[radial-gradient(ellipse_at_top,rgba(196,163,90,0.06),transparent_55%)]">
            {error ? (
              <div className="px-4 pt-3">
                <ErrorState
                  message={error}
                  onRetry={() => {
                    setError(null);
                    connect();
                  }}
                />
              </div>
            ) : null}
            <SceneLog messages={messages} streamingNarration={streamingNarration} />
            {busy ? (
              <div className="px-4 pb-2">
                <LoadingState label="The dungeon master considers your fate…" />
              </div>
            ) : null}
          </div>
        }
        right={
          <div className="space-y-5">
            <LocationPanel
              name={snapshot.current_location?.name}
              description={snapshot.current_location?.description}
              locationType={snapshot.current_location?.location_type}
            />
            <NPCPanel npcs={snapshot.nearby_npcs} />
            <InventoryPanel items={snapshot.inventory} />
            <CombatPanel combat={snapshot.combat} />
            <MapPanel locationName={snapshot.current_location?.name} />
            <Link to="/" className="block text-xs text-muted hover:text-accent">
              Leave table
            </Link>
          </div>
        }
        footer={
          <ActionInput
            disabled={busy}
            onSubmit={(action) => {
              void sendAction(action);
            }}
          />
        }
      />
    </div>
  );
}
