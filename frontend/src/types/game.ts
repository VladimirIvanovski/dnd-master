export type Campaign = {
  id: string;
  name: string;
  description: string;
  current_time: string;
  weather: string;
  world_state: Record<string, unknown>;
  created_at: string;
};

export type Character = {
  id: string;
  campaign_id: string;
  name: string;
  race: string;
  class_name: string;
  level: number;
  xp: number;
  hp: number;
  max_hp: number;
  temp_hp?: number;
  ac: number;
  gold: number;
  silver?: number;
  copper?: number;
  location_id: string | null;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
};

export type InventoryItem = {
  id: string;
  item_id: string;
  name: string;
  quantity: number;
  equipped: boolean;
  item_type: string;
  description: string;
};

export type QuestObjective = {
  id: string;
  description: string;
  is_completed: boolean;
  sort_order: number;
};

export type Quest = {
  id: string;
  title: string;
  description: string;
  status: string;
  reward_xp: number;
  reward_gold: number;
  objectives: QuestObjective[];
};

export type DialogueLine = {
  speaker: string;
  text: string;
};

export type DiceResult = {
  notation: string;
  total: number;
  rolls: number[];
  purpose: string;
  success: boolean | null;
  ability?: string | null;
  skill?: string | null;
  modifier?: number;
  dc?: number | null;
  natural?: number | null;
  critical?: string | null;
};

export type GameStateSnapshot = {
  campaign_id: string;
  campaign_name: string;
  character: {
    id: string;
    name: string;
    race: string;
    class_name: string;
    level: number;
    xp: number;
    hp: number;
    max_hp: number;
    temp_hp?: number;
    ac: number;
    gold: number;
    silver?: number;
    copper?: number;
    abilities: Record<string, number>;
    conditions?: string[];
    stamina?: number;
    hunger?: number;
    thirst?: number;
    carry_weight?: number;
    carry_capacity?: number;
    known_facts?: string[];
    death_saves_success?: number;
    death_saves_fail?: number;
  };
  current_location: {
    id: string;
    name: string;
    description: string;
    location_type: string;
    lighting?: string;
    containers?: Array<{ id: string; name: string; locked: boolean }>;
    traps?: Array<{ id: string; name: string; armed: boolean }>;
  } | null;
  nearby_npcs: Array<{
    id: string;
    name: string;
    title: string;
    personality: string;
    is_alive: boolean;
    faction?: string;
    stock?: Array<{ name: string; quantity: number; price: number; item_type?: string }>;
    topics?: Array<{ id: string; label: string }>;
    asked?: string[];
    trust?: number;
    fear?: number;
    respect?: number;
  }>;
  inventory: Array<{
    item_id: string;
    name: string;
    quantity: number;
    equipped: boolean;
    item_type: string;
    durability?: number | null;
    weight?: number;
  }>;
  active_quests: Array<{
    id: string;
    title: string;
    description: string;
    status: string;
    objectives: string[];
  }>;
  world_state: Record<string, unknown>;
  current_time: string;
  weather: string;
  heard_rumors?: string[];
  unheard_rumor_ids?: string[];
  checkpoints?: string[];
  known_locations?: Array<{
    id: string;
    name: string;
    location_type: string;
    here: boolean;
  }>;
  combat: {
    id: string;
    status: string;
    round_number: number;
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
};

export type GameplayResponse = {
  narration: string;
  dialogue: DialogueLine[];
  dice_results: DiceResult[];
  applied_events: string[];
  applied_changes: string[];
  rejected_changes: string[];
  state_snapshot: GameStateSnapshot;
  suggested_actions?: string[];
};

export type SceneMessage =
  | { id: string; kind: "player"; text: string }
  | { id: string; kind: "narration"; text: string }
  | { id: string; kind: "dialogue"; speaker: string; text: string }
  | { id: string; kind: "event"; text: string }
  | { id: string; kind: "dice"; result: DiceResult }
  | { id: string; kind: "system"; text: string };

export type ConnectionState = "idle" | "connecting" | "connected" | "disconnected" | "error";
