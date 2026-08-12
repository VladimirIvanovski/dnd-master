import { apiRequest } from "./client";
import type { GameplayResponse, GameStateSnapshot } from "../types/game";

export type CampaignOpening = {
  tone: string;
  themes: string[];
  opening_narration: string;
  opening_delivered: boolean;
  user_campaign_description?: string;
  campaign_dna?: Record<string, unknown>;
  campaign_dna_version?: number | null;
  campaign_dna_summary?: string[];
};

export const gameplayApi = {
  action: (payload: { campaign_id: string; character_id: string; action: string }) =>
    apiRequest<GameplayResponse>("/api/gameplay/action", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  state: (campaignId: string, characterId: string) =>
    apiRequest<GameStateSnapshot>(
      `/api/gameplay/state?campaign_id=${encodeURIComponent(campaignId)}&character_id=${encodeURIComponent(characterId)}`,
    ),

  opening: (campaignId: string) =>
    apiRequest<CampaignOpening>(
      `/api/gameplay/opening?campaign_id=${encodeURIComponent(campaignId)}`,
    ),

  history: (campaignId: string, characterId: string, limit = 40) =>
    apiRequest<Array<{ id: string; event_type: string; summary: string; created_at?: string | null }>>(
      `/api/gameplay/history?campaign_id=${encodeURIComponent(campaignId)}&character_id=${encodeURIComponent(characterId)}&limit=${limit}`,
    ),

  ackOpening: (campaignId: string) =>
    apiRequest<CampaignOpening>(
      `/api/gameplay/opening/ack?campaign_id=${encodeURIComponent(campaignId)}`,
      { method: "POST" },
    ),
};
