import { apiRequest } from "./client";
import type { Character } from "../types/game";

export type CharacterCreatePayload = {
  campaign_id: string;
  name: string;
  race?: string;
  class_name?: string;
  owner_username?: string;
  strength?: number;
  dexterity?: number;
  constitution?: number;
  intelligence?: number;
  wisdom?: number;
  charisma?: number;
  background?: string;
};

export const characterApi = {
  get: (id: string) => apiRequest<Character>(`/api/characters/${id}`),

  list: (campaignId: string) =>
    apiRequest<Character[]>(`/api/characters?campaign_id=${encodeURIComponent(campaignId)}`),

  create: (payload: CharacterCreatePayload) =>
    apiRequest<Character>("/api/characters", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
