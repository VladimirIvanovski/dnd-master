import { apiRequest } from "./client";
import type { Quest } from "../types/game";

export const questApi = {
  list: (campaignId: string, characterId?: string) => {
    const params = new URLSearchParams({ campaign_id: campaignId });
    if (characterId) params.set("character_id", characterId);
    return apiRequest<Quest[]>(`/api/quests?${params.toString()}`);
  },

  create: (payload: {
    campaign_id: string;
    title: string;
    description?: string;
    character_id?: string;
    objectives?: string[];
  }) =>
    apiRequest<Quest>("/api/quests", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
