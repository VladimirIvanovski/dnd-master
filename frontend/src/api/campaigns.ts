import { apiRequest } from "./client";
import type { Campaign } from "../types/game";

export const campaignApi = {
  list: () => apiRequest<Campaign[]>("/api/campaigns"),

  get: (id: string) => apiRequest<Campaign>(`/api/campaigns/${id}`),

  create: (payload: { name: string; description?: string }) =>
    apiRequest<Campaign>("/api/campaigns", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
