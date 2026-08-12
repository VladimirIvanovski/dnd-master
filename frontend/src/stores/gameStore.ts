import { create } from "zustand";
import { gameplayApi } from "../api";
import { GameplaySocket } from "../lib/gameplaySocket";
import { uid } from "../lib/id";
import { stripEmbeddedDialogue } from "../lib/dedupeDialogue";
import type {
  Campaign,
  Character,
  ConnectionState,
  DiceResult,
  GameStateSnapshot,
  GameplayResponse,
  Quest,
  SceneMessage,
} from "../types/game";
import { useUiStore } from "./uiStore";

type GameStore = {
  campaignId: string | null;
  characterId: string | null;
  campaign: Campaign | null;
  character: Character | null;
  state: GameStateSnapshot | null;
  quests: Quest[];
  messages: SceneMessage[];
  streamingNarration: string;
  latestDice: DiceResult[];
  suggestedActions: string[];
  connection: ConnectionState;
  busy: boolean;
  error: string | null;
  setSession: (campaign: Campaign, character: Character) => void;
  setStateSnapshot: (state: GameStateSnapshot) => void;
  setQuests: (quests: Quest[]) => void;
  setError: (error: string | null) => void;
  setSuggestedActions: (actions: string[]) => void;
  seedOpening: (narration: string, tone?: string) => void;
  seedHistory: (
    opening: {
      narration?: string;
      tone?: string;
      dnaSummary?: string[];
      dnaVersion?: number | null;
    },
    beats: Array<{ id: string; event_type: string; summary: string }>,
  ) => void;
  connect: () => void;
  disconnect: () => void;
  sendAction: (action: string) => Promise<void>;
  clearScene: () => void;
};

const socket = new GameplaySocket();
let actionTimeout: number | null = null;

function clearActionTimeout() {
  if (actionTimeout) {
    window.clearTimeout(actionTimeout);
    actionTimeout = null;
  }
}

function questsFromSnapshot(state: GameStateSnapshot): Quest[] {
  return state.active_quests.map((q) => ({
    id: q.id,
    title: q.title,
    description: q.description,
    status: q.status,
    reward_xp: 0,
    reward_gold: 0,
    objectives: q.objectives.map((description, sort_order) => ({
      id: `${q.id}-${sort_order}`,
      description,
      is_completed: false,
      sort_order,
    })),
  }));
}

function applyResult(
  set: (partial: Partial<GameStore> | ((s: GameStore) => Partial<GameStore>)) => void,
  get: () => GameStore,
  data: GameplayResponse,
  playerAction?: string,
) {
  clearActionTimeout();
  const messages: SceneMessage[] = [...get().messages];
  if (playerAction) {
    messages.push({ id: uid("player"), kind: "player", text: playerAction });
  }
  // Show dice outcome immediately (before typewriter narration)
  for (const dice of data.dice_results) {
    messages.push({ id: uid("dice"), kind: "dice", result: dice });
  }
  if (data.narration) {
    const cleaned = stripEmbeddedDialogue(data.narration, data.dialogue || []);
    if (cleaned.trim()) {
      messages.push({ id: uid("narration"), kind: "narration", text: cleaned });
    }
  }
  for (const line of data.dialogue) {
    messages.push({
      id: uid("dialogue"),
      kind: "dialogue",
      speaker: line.speaker,
      text: line.text,
    });
  }
  for (const event of data.applied_events) {
    messages.push({ id: uid("event"), kind: "event", text: event });
  }
  for (const change of data.applied_changes) {
    messages.push({ id: uid("event"), kind: "event", text: `Applied: ${change}` });
  }
  for (const change of data.rejected_changes) {
    useUiStore.getState().pushNotification("Couldn't apply", change);
  }

  set({
    state: data.state_snapshot,
    quests: questsFromSnapshot(data.state_snapshot),
    messages,
    streamingNarration: "",
    latestDice: data.dice_results,
    suggestedActions: (data.suggested_actions || []).slice(0, 3),
    busy: false,
    error: null,
  });

  const ui = useUiStore.getState();
  if (data.dice_results.length) {
    ui.setDiceOverlay(data.dice_results[data.dice_results.length - 1]);
  }
  for (const event of data.applied_events) {
    const lower = event.toLowerCase();
    if (lower.includes("quest")) {
      ui.pushNotification("Quest updated", event);
    } else if (lower.includes("level")) {
      ui.pushNotification("Level up", event);
    } else if (lower.includes("discover") || lower.includes("location")) {
      ui.pushNotification("Discovery", event);
    }
  }
  for (const change of data.applied_changes) {
    const lower = change.toLowerCase();
    if (lower.includes("item") || lower.includes("gold") || lower.includes("gain")) {
      ui.pushNotification("Loot", change);
    }
  }
}

export const useGameStore = create<GameStore>((set, get) => ({
  campaignId: null,
  characterId: null,
  campaign: null,
  character: null,
  state: null,
  quests: [],
  messages: [],
  streamingNarration: "",
  latestDice: [],
  suggestedActions: [
    "Look around carefully",
    "Talk to someone nearby",
    "Check your belongings",
  ],
  connection: "idle",
  busy: false,
  error: null,

  setSession: (campaign, character) => {
    set({
      campaign,
      character,
      campaignId: campaign.id,
      characterId: character.id,
      error: null,
    });
  },

  setStateSnapshot: (state) => set({ state, quests: questsFromSnapshot(state) }),

  setQuests: (quests) => set({ quests }),

  setError: (error) => set({ error, busy: false }),

  setSuggestedActions: (actions) => set({ suggestedActions: actions.slice(0, 3) }),

  seedOpening: (narration) => {
    if (!narration.trim()) return;
    set({
      messages: [{ id: uid("narration"), kind: "narration", text: narration.trim() }],
    });
  },

  seedHistory: (opening, beats) => {
    const messages: SceneMessage[] = [];
    if (opening.narration?.trim()) {
      messages.push({
        id: uid("narration"),
        kind: "narration",
        text: opening.narration.trim(),
      });
    }
    for (const beat of beats) {
      if (beat.event_type === "PLAYER_ACTION") {
        messages.push({ id: beat.id, kind: "player", text: beat.summary });
      } else if (beat.event_type === "SCENE_NARRATION") {
        messages.push({ id: beat.id, kind: "narration", text: beat.summary });
      }
      // Skip tone/DNA/system meta events in the main story view
    }
    set({ messages });
  },

  clearScene: () =>
    set({
      messages: [],
      streamingNarration: "",
      latestDice: [],
      suggestedActions: [
        "Look around carefully",
        "Talk to someone nearby",
        "Check your belongings",
      ],
    }),

  connect: () => {
    set({ connection: "connecting" });
    socket.connect({
      onOpen: () => set({ connection: "connected" }),
      onClose: () => set({ connection: "disconnected" }),
      onStatus: () => set({ busy: true }),
      onNarrationChunk: (text) =>
        set((s) => ({ streamingNarration: s.streamingNarration + text, busy: true })),
      onResult: (data) => applyResult(set, get, data),
      onError: (detail) => {
        clearActionTimeout();
        set({ error: detail, busy: false });
      },
    });
  },

  disconnect: () => {
    clearActionTimeout();
    socket.disconnect();
    set({ connection: "idle" });
  },

  sendAction: async (action) => {
    const { campaignId, characterId, connection, busy } = get();
    if (busy) return;
    if (!campaignId || !characterId) {
      set({ error: "Missing campaign or character session." });
      return;
    }

    const trimmed = action.trim();
    if (!trimmed) return;
    const playerId = uid("player");

    set({
      busy: true,
      error: null,
      streamingNarration: "",
      messages: [...get().messages, { id: playerId, kind: "player", text: trimmed }],
    });

    actionTimeout = window.setTimeout(() => {
      set((s) => ({
        busy: false,
        error: s.error ?? "The dungeon master took too long. Try again.",
      }));
    }, 20000);

    try {
      if (connection === "connected" && socket.connected) {
        socket.sendAction({
          campaign_id: campaignId,
          character_id: characterId,
          action: trimmed,
        });
        return;
      }

      const data = await gameplayApi.action({
        campaign_id: campaignId,
        character_id: characterId,
        action: trimmed,
      });
      set((s) => ({ messages: s.messages.filter((m) => m.id !== playerId) }));
      applyResult(set, get, data, trimmed);
    } catch (err) {
      clearActionTimeout();
      const message = err instanceof Error ? err.message : "Action failed";
      set({
        busy: false,
        error: message,
        messages: [
          ...get().messages,
          { id: uid("system"), kind: "system", text: message },
        ],
      });
    }
  },
}));
