import type { GameplayResponse } from "../types/game";

function wsBase(): string {
  const fromEnv = import.meta.env.VITE_WS_BASE_URL;
  if (fromEnv) return fromEnv;
  if (typeof window === "undefined") return "ws://127.0.0.1:8000";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}`;
}

type WsHandlers = {
  onStatus?: (message: string) => void;
  onNarrationChunk?: (text: string) => void;
  onResult?: (data: GameplayResponse) => void;
  onError?: (detail: string) => void;
  onOpen?: () => void;
  onClose?: () => void;
};

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return JSON.stringify(detail);
  return "Server error";
}

export class GameplaySocket {
  private socket: WebSocket | null = null;
  private handlers: WsHandlers = {};
  private shouldReconnect = false;
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;

  connect(handlers: WsHandlers) {
    this.handlers = handlers;
    this.shouldReconnect = true;
    this.open();
  }

  private open() {
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const username = localStorage.getItem("dnd-username") || "player";
    const url = `${wsBase()}/ws/gameplay?username=${encodeURIComponent(username)}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.handlers.onOpen?.();
    };

    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data as string) as Record<string, unknown>;
        if (payload.type === "status") {
          this.handlers.onStatus?.(String(payload.message ?? "processing"));
          return;
        }
        if (payload.type === "narration_chunk") {
          this.handlers.onNarrationChunk?.(String(payload.text ?? ""));
          return;
        }
        if (payload.type === "result") {
          this.handlers.onResult?.(payload.data as GameplayResponse);
          return;
        }
        if (payload.type === "error" || payload.error) {
          this.handlers.onError?.(formatDetail(payload.detail ?? payload.error));
        }
      } catch {
        this.handlers.onError?.("Malformed server message");
      }
    };

    this.socket.onerror = () => {
      // Transient; onclose handles reconnect messaging.
    };

    this.socket.onclose = () => {
      this.handlers.onClose?.();
      if (this.shouldReconnect) {
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 10000);
        this.reconnectAttempts += 1;
        this.reconnectTimer = window.setTimeout(() => this.open(), delay);
      }
    };
  }

  sendAction(payload: { campaign_id: string; character_id: string; action: string }) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not connected");
    }
    this.socket.send(JSON.stringify(payload));
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
  }

  get connected() {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}
