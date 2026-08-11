const API = process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const WS = process.env.VITE_WS_BASE_URL || "ws://127.0.0.1:8000";
const HEADERS = { "Content-Type": "application/json", "X-Username": "player" };

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { ...HEADERS, ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status} ${await res.text()}`);
  return res.json();
}

async function restFlow() {
  const campaign = await api("/api/campaigns", {
    method: "POST",
    body: JSON.stringify({ name: `FE Verify ${Date.now()}`, description: "frontend e2e" }),
  });
  const character = await api("/api/characters", {
    method: "POST",
    body: JSON.stringify({
      campaign_id: campaign.id,
      name: "Elya",
      class_name: "Ranger",
    }),
  });
  const state = await api(
    `/api/gameplay/state?campaign_id=${campaign.id}&character_id=${character.id}`,
  );
  if (!state.current_location) throw new Error("missing location on boot state");

  const result = await api("/api/gameplay/action", {
    method: "POST",
    body: JSON.stringify({
      campaign_id: campaign.id,
      character_id: character.id,
      action: "I approach and meet Elira",
    }),
  });
  if (!result.narration) throw new Error("missing narration");
  console.log("REST_OK", {
    campaign: campaign.id,
    character: character.id,
    narration: result.narration.slice(0, 80),
  });
  return { campaign, character };
}

function wsFlow(campaignId, characterId) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(`${WS}/ws/gameplay?username=player`);
    let chunks = "";
    const timer = setTimeout(() => reject(new Error("ws timeout")), 15000);

    socket.onopen = () => {
      socket.send(
        JSON.stringify({
          campaign_id: campaignId,
          character_id: characterId,
          action: "I promise to help Elira",
        }),
      );
    };
    socket.onmessage = (event) => {
      const msg = JSON.parse(String(event.data));
      if (msg.type === "narration_chunk") chunks += msg.text;
      if (msg.type === "result") {
        clearTimeout(timer);
        console.log("WS_OK", { streamed: chunks.slice(0, 80), events: msg.data.applied_events?.length ?? 0 });
        socket.close();
        resolve();
      }
      if (msg.type === "error") {
        clearTimeout(timer);
        reject(new Error(JSON.stringify(msg)));
      }
    };
    socket.onerror = () => {
      clearTimeout(timer);
      reject(new Error("ws error"));
    };
  });
}

const { campaign, character } = await restFlow();
await wsFlow(campaign.id, character.id);
console.log("E2E_OK", API);
