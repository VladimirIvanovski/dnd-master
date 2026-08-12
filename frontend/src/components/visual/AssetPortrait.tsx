import { useEffect, useState } from "react";
import { loadAssetObjectUrl, visualApi } from "../../api/visuals";

type Props = {
  kind: "npc" | "character" | "item";
  entityId: string;
  label?: string;
  size?: number;
};

export function AssetPortrait({ kind, entityId, label, size = 40 }: Props) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    let timer: number | undefined;

    async function poll() {
      try {
        const meta =
          kind === "npc"
            ? await visualApi.npcPortrait(entityId)
            : kind === "character"
              ? await visualApi.characterPortrait(entityId)
              : await visualApi.itemIcon(entityId);
        if (cancelled) return;
        if (meta.status === "READY" && meta.url) {
          objectUrl = await loadAssetObjectUrl(meta.url);
          if (!cancelled) setUrl(objectUrl);
          return;
        }
        timer = window.setTimeout(() => void poll(), 2500);
      } catch {
        /* ignore */
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [kind, entityId]);

  return (
    <div
      className="shrink-0 overflow-hidden rounded border border-border bg-panel-2"
      style={{ width: size, height: size }}
      title={label}
    >
      {url ? (
        <img src={url} alt={label || kind} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-[10px] text-muted">…</div>
      )}
    </div>
  );
}
