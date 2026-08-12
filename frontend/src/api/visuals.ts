import { apiRequest, getToken } from "./client";

export type VisualStatus = {
  status: string;
  url?: string | null;
  asset_id?: string;
  job_id?: string;
  version?: number;
};

export type MapData = {
  campaign_id: string;
  locations: Array<{
    id: string;
    name: string;
    type: string;
    parent_id: string | null;
    x: number;
    y: number;
    active_visual_id: string | null;
  }>;
  art_status?: string;
  art_url?: string | null;
  art_asset_id?: string | null;
};

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Authenticated image URL fetch → object URL for <img>. */
export async function loadAssetObjectUrl(path: string): Promise<string | null> {
  if (!path) return null;
  const res = await fetch(path, { headers: authHeaders() });
  if (!res.ok) return null;
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export const visualApi = {
  locationVisual: (locationId: string) =>
    apiRequest<VisualStatus>(`/api/locations/${locationId}/visual`),
  npcPortrait: (npcId: string) => apiRequest<VisualStatus>(`/api/npcs/${npcId}/portrait`),
  characterPortrait: (characterId: string) =>
    apiRequest<VisualStatus>(`/api/characters/${characterId}/portrait`),
  itemIcon: (itemId: string) => apiRequest<VisualStatus>(`/api/items/${itemId}/icon`),
  campaignMap: (campaignId: string) => apiRequest<MapData>(`/api/campaigns/${campaignId}/map`),
};
