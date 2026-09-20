import { useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";
import { campaignApi, characterApi, gameplayApi, questApi } from "../api";
import { ErrorState } from "../components/common/ErrorState";
import { GameLayout } from "../components/game/GameLayout";
import { JournalPanel } from "../components/game/JournalPanel";
import { PartyPanel } from "../components/game/PartyPanel";
import { StoryStage } from "../components/game/StoryStage";
import { CharacterPanel } from "../components/character/CharacterPanel";
import { InventoryPanel } from "../components/inventory/InventoryPanel";
import { LoadingState } from "../components/common/LoadingState";
import { NPCPanel } from "../components/game/NPCPanel";
import { QuestPanel } from "../components/quests/QuestPanel";
import { LocationArt } from "../components/visual/LocationArt";
import { MapPanel } from "../components/map/MapPanel";
import { SlideOver } from "../components/ui/SlideOver";
import { ToastStack } from "../components/ui/ToastStack";
import { DiceFocus } from "../components/ui/DiceFocus";
import { useGameStore } from "../stores/gameStore";
import { useUiStore, type PanelId } from "../stores/uiStore";

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
    suggestedActions,
    setSession,
    setStateSnapshot,
    setQuests,
    setError,
    seedHistory,
    connect,
    disconnect,
    sendAction,
    clearScene,
  } = useGameStore();

  const openPanel = useUiStore((s) => s.openPanel);
  const mountedPanels = useUiStore((s) => s.mountedPanels);
  const togglePanel = useUiStore((s) => s.togglePanel);
  const closePanel = useUiStore((s) => s.closePanel);
  const openPanelById = useUiStore((s) => s.openPanelById);
  const setCombatActive = useUiStore((s) => s.setCombatActive);
  const setDialogueActive = useUiStore((s) => s.setDialogueActive);
  const setAmbientHint = useUiStore((s) => s.setAmbientHint);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        setError(null);
        clearScene();
        const [camp, char, questList, snapshot, opening, history] = await Promise.all([
          campaignApi.get(campaignId),
          characterApi.get(characterId),
          questApi.list(campaignId, characterId),
          gameplayApi.state(campaignId, characterId),
          gameplayApi.opening(campaignId),
          gameplayApi.history(campaignId, characterId),
        ]);
        if (cancelled) return;
        setSession(camp, char);
        setQuests(questList);
        setStateSnapshot(snapshot);
        localStorage.setItem(
          "dnd-session",
          JSON.stringify({ campaignId, characterId }),
        );
        seedHistory(
          {
            narration: opening.opening_narration,
            tone: opening.tone,
            dnaSummary: opening.campaign_dna_summary,
            dnaVersion: opening.campaign_dna_version,
          },
          history,
        );
        if (opening.opening_narration && !opening.opening_delivered) {
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
    seedHistory,
    setQuests,
    setSession,
    setStateSnapshot,
  ]);

  useEffect(() => {
    setCombatActive(Boolean(state?.combat));
  }, [state?.combat, setCombatActive]);

  useEffect(() => {
    const last = [...messages].reverse().find((m) => m.kind === "dialogue" || m.kind === "narration" || m.kind === "player");
    setDialogueActive(last?.kind === "dialogue");
  }, [messages, setDialogueActive]);

  useEffect(() => {
    const loc = state?.current_location?.location_type || "";
    const weather = state?.weather || "";
    setAmbientHint([loc, weather].filter(Boolean).join(":") || null);
  }, [state?.current_location?.location_type, state?.weather, setAmbientHint]);

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
  const loc = snapshot.current_location;
  const panelOpen = (id: PanelId) => openPanel === id;
  const shouldRender = (id: PanelId) => Boolean(mountedPanels[id]) || openPanel === id;

  return (
    <div className="h-full min-h-0 overflow-hidden">
      <GameLayout
        locationName={loc?.name || snapshot.campaign_name || campaign.name}
        time={snapshot.current_time || campaign.current_time}
        weather={snapshot.weather || campaign.weather}
        gold={snapshot.character.gold}
        hp={snapshot.character.hp}
        maxHp={snapshot.character.max_hp}
        xp={snapshot.character.xp}
        level={snapshot.character.level}
        connectionTone={connectionMeta.tone}
        combatMode={Boolean(snapshot.combat)}
        activePanel={openPanel}
        onTogglePanel={togglePanel}
        busy={busy}
        suggestions={suggestedActions}
        onAction={(action) => {
          void sendAction(action);
        }}
        leftDock={
          !snapshot.combat ? (
            <div className="flex flex-col gap-4">
              <CharacterPanel character={snapshot.character} inventory={snapshot.inventory} />
              <NPCPanel
                npcs={snapshot.nearby_npcs.filter((n) => n.is_alive !== false)}
                activeSpeaker={
                  [...messages].reverse().find((m) => m.kind === "dialogue")?.speaker ?? null
                }
                onAsk={(npcId, topicId) => {
                  void sendAction(`sys:ask:${npcId}:${topicId}`);
                }}
              />
              <InventoryPanel items={snapshot.inventory} />
            </div>
          ) : null
        }
        rightDock={
          !snapshot.combat ? (
            <div className="flex flex-col gap-4">
              <div>
                <p className="label-caps mb-1.5">Location</p>
                {loc ? (
                  <>
                    <p className="display-text text-lg text-accent/90">{loc.name}</p>
                    <p className="text-sm uppercase tracking-[0.14em] text-muted">
                      {loc.location_type}
                      {loc.lighting ? ` · ${loc.lighting}` : ""}
                    </p>
                    {loc.description ? (
                      <p className="mt-2 text-base leading-relaxed text-muted">{loc.description}</p>
                    ) : null}
                    {loc.traps && loc.traps.length > 0 ? (
                      <p className="mt-2 text-sm text-muted">
                        Traps: {loc.traps.map((t) => `${t.name}${t.armed ? "" : " (safe)"}`).join(", ")}
                      </p>
                    ) : null}
                    {(snapshot.unheard_rumor_ids || []).length > 0 ? (
                      <div className="mt-3">
                        <p className="text-xs uppercase tracking-[0.12em] text-muted">Rumors</p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {(snapshot.unheard_rumor_ids || []).map((id) => (
                            <button
                              key={id}
                              type="button"
                              className="rounded border border-border/50 px-1.5 py-0.5 text-[0.65rem] uppercase tracking-[0.08em] text-muted hover:border-accent/50 hover:text-parchment"
                              onClick={() => void sendAction(`sys:hear:${id}`)}
                            >
                              {id}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <p className="text-sm text-muted">Unknown region.</p>
                )}
              </div>
              <LocationArt
                locationId={loc?.id}
                locationName={loc?.name}
                locationType={loc?.location_type}
                variant="panel"
              />
            </div>
          ) : null
        }
        overlays={
          <>
            {shouldRender("map") ? (
              <SlideOver open={panelOpen("map")} title="Map" onClose={closePanel}>
                <MapPanel
                  campaignId={campaignId}
                  currentLocationId={loc?.id}
                  places={snapshot.known_locations || []}
                  onTravel={(name) => {
                    closePanel();
                    void sendAction(`Travel to ${name}`);
                  }}
                />
              </SlideOver>
            ) : null}

            {shouldRender("party") ? (
              <SlideOver open={panelOpen("party")} title="Party" onClose={closePanel}>
                <PartyPanel
                  character={{
                    id: snapshot.character.id,
                    name: snapshot.character.name,
                    hp: snapshot.character.hp,
                    max_hp: snapshot.character.max_hp,
                    ac: snapshot.character.ac,
                    class_name: snapshot.character.class_name,
                    level: snapshot.character.level,
                  }}
                  onOpenCharacter={() => openPanelById("character")}
                />
              </SlideOver>
            ) : null}

            {shouldRender("character") ? (
              <SlideOver open={panelOpen("character")} title="Character" onClose={closePanel}>
                <CharacterPanel character={snapshot.character} inventory={snapshot.inventory} />
              </SlideOver>
            ) : null}

            {shouldRender("inventory") ? (
              <SlideOver open={panelOpen("inventory")} title="Inventory" onClose={closePanel}>
                <InventoryPanel items={snapshot.inventory} />
              </SlideOver>
            ) : null}

            {shouldRender("quests") ? (
              <SlideOver open={panelOpen("quests")} title="Quests" onClose={closePanel}>
                <QuestPanel quests={quests.length ? quests : snapshot.active_quests} />
              </SlideOver>
            ) : null}

            {shouldRender("journal") ? (
              <SlideOver open={panelOpen("journal")} title="Journal" onClose={closePanel}>
                <JournalPanel
                  messages={messages}
                  currentTime={snapshot.current_time || campaign.current_time}
                  checkpoints={snapshot.checkpoints || []}
                  onSave={() => {
                    closePanel();
                    void sendAction("sys:save:camp");
                  }}
                  onLoad={(name) => {
                    closePanel();
                    void sendAction(`sys:load:${name}`);
                  }}
                />
              </SlideOver>
            ) : null}

            <ToastStack />
            <DiceFocus />
          </>
        }
      >
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
        <StoryStage
          locationId={loc?.id}
          locationName={loc?.name}
          locationType={loc?.location_type}
          timeOfDay={snapshot.current_time || campaign.current_time}
          messages={messages}
          streamingNarration={streamingNarration}
          nearbyNpcs={snapshot.nearby_npcs.filter((n) => n.is_alive !== false)}
          combat={snapshot.combat}
          busy={busy}
          onCombatCommand={(command) => {
            void sendAction(command);
          }}
        />
      </GameLayout>
    </div>
  );
}
