import { apiRequest } from "./client";
import type { InventoryItem } from "../types/game";

export const inventoryApi = {
  list: (characterId: string) =>
    apiRequest<InventoryItem[]>(`/api/inventory/${characterId}`),
};
