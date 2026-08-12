import { create } from "zustand";
import type { DiceResult } from "../types/game";

export type PanelId =
  | "map"
  | "party"
  | "character"
  | "inventory"
  | "quests"
  | "journal"
  | "settings";

export type UiMode =
  | "exploration"
  | "dialogue"
  | "combat"
  | "inventory"
  | "map"
  | "character"
  | "quests"
  | "journal";

export type NotificationItem = {
  id: string;
  title: string;
  body?: string;
  createdAt: number;
};

type PanelPrefs = {
  tab?: string;
  scrollTop?: number;
};

type UiStore = {
  openPanel: PanelId | null;
  combatActive: boolean;
  dialogueActive: boolean;
  panelPrefs: Partial<Record<PanelId, PanelPrefs>>;
  mountedPanels: Partial<Record<PanelId, boolean>>;
  notifications: NotificationItem[];
  diceOverlay: DiceResult | null;
  ambientHint: string | null;
  leftDockWidth: number;
  rightDockWidth: number;
  mode: () => UiMode;
  openPanelById: (id: PanelId) => void;
  closePanel: () => void;
  togglePanel: (id: PanelId) => void;
  setPanelTab: (id: PanelId, tab: string) => void;
  setPanelScroll: (id: PanelId, scrollTop: number) => void;
  setCombatActive: (active: boolean) => void;
  setDialogueActive: (active: boolean) => void;
  pushNotification: (title: string, body?: string) => void;
  dismissNotification: (id: string) => void;
  setDiceOverlay: (dice: DiceResult | null) => void;
  clearDiceOverlay: () => void;
  setAmbientHint: (hint: string | null) => void;
  setLeftDockWidth: (w: number) => void;
  setRightDockWidth: (w: number) => void;
};

const LEFT_MIN = 280;
const LEFT_MAX = 460;
const RIGHT_MIN = 300;
const RIGHT_MAX = 480;

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

let notifSeq = 0;
let diceClearTimer: number | null = null;

function loadWidth(key: string, fallback: number) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const n = Number(raw);
    return Number.isFinite(n) ? n : fallback;
  } catch {
    return fallback;
  }
}

export const useUiStore = create<UiStore>((set, get) => ({
  openPanel: null,
  combatActive: false,
  dialogueActive: false,
  panelPrefs: {},
  mountedPanels: {},
  notifications: [],
  diceOverlay: null,
  ambientHint: null,
  leftDockWidth: loadWidth("dnd-left-dock-v6", 360),
  rightDockWidth: loadWidth("dnd-right-dock-v6", 380),

  mode: () => {
    const s = get();
    if (s.combatActive) return "combat";
    if (s.openPanel === "map") return "map";
    if (s.openPanel === "inventory") return "inventory";
    if (s.openPanel === "character" || s.openPanel === "party") return "character";
    if (s.openPanel === "quests") return "quests";
    if (s.openPanel === "journal") return "journal";
    if (s.dialogueActive) return "dialogue";
    return "exploration";
  },

  openPanelById: (id) =>
    set((s) => ({
      openPanel: id,
      mountedPanels: { ...s.mountedPanels, [id]: true },
    })),

  closePanel: () => set({ openPanel: null }),

  togglePanel: (id) => {
    const { openPanel, openPanelById, closePanel } = get();
    if (openPanel === id) closePanel();
    else openPanelById(id);
  },

  setPanelTab: (id, tab) =>
    set((s) => ({
      panelPrefs: {
        ...s.panelPrefs,
        [id]: { ...s.panelPrefs[id], tab },
      },
    })),

  setPanelScroll: (id, scrollTop) =>
    set((s) => ({
      panelPrefs: {
        ...s.panelPrefs,
        [id]: { ...s.panelPrefs[id], scrollTop },
      },
    })),

  setCombatActive: (active) => set({ combatActive: active }),

  setDialogueActive: (active) => set({ dialogueActive: active }),

  pushNotification: (title, body) => {
    const id = `n-${++notifSeq}`;
    set((s) => ({
      notifications: [...s.notifications.slice(-4), { id, title, body, createdAt: Date.now() }],
    }));
    window.setTimeout(() => {
      get().dismissNotification(id);
    }, 4500);
  },

  dismissNotification: (id) =>
    set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),

  setDiceOverlay: (dice) => {
    if (diceClearTimer) {
      window.clearTimeout(diceClearTimer);
      diceClearTimer = null;
    }
    // Pending click-to-reveal — do not auto-clear (that would spoil the ritual).
    set({ diceOverlay: dice });
  },

  clearDiceOverlay: () => {
    if (diceClearTimer) {
      window.clearTimeout(diceClearTimer);
      diceClearTimer = null;
    }
    set({ diceOverlay: null });
  },

  setAmbientHint: (hint) => set({ ambientHint: hint }),

  setLeftDockWidth: (w) => {
    const next = clamp(w, LEFT_MIN, LEFT_MAX);
    try {
      localStorage.setItem("dnd-left-dock-v6", String(next));
    } catch {
      /* ignore */
    }
    set({ leftDockWidth: next });
  },

  setRightDockWidth: (w) => {
    const next = clamp(w, RIGHT_MIN, RIGHT_MAX);
    try {
      localStorage.setItem("dnd-right-dock-v6", String(next));
    } catch {
      /* ignore */
    }
    set({ rightDockWidth: next });
  },
}));
