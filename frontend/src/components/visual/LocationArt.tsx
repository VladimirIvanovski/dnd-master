import { useEffect, useState } from "react";
import { loadAssetObjectUrl, visualApi } from "../../api/visuals";

type Props = {
  locationId?: string | null;
  locationName?: string;
  locationType?: string;
  variant?: "hero" | "panel";
};

export function LocationArt({
  locationId,
  locationName,
  locationType,
  variant = "panel",
}: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [artKey, setArtKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    let timer: number | undefined;

    setUrl(null);
    setStatus(locationId ? "PENDING" : "idle");
    setArtKey((k) => k + 1);

    async function poll() {
      if (!locationId) return;
      try {
        const meta = await visualApi.locationVisual(locationId);
        if (cancelled) return;
        setStatus(meta.status);
        if (meta.status === "READY" && meta.url) {
          objectUrl = await loadAssetObjectUrl(meta.url);
          if (!cancelled) {
            setUrl(objectUrl);
            setArtKey((k) => k + 1);
          }
          return;
        }
        timer = window.setTimeout(() => void poll(), 1600);
      } catch {
        if (!cancelled) setStatus("MISSING");
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [locationId]);

  const waiting =
    status === "QUEUED" || status === "GENERATING" || status === "PENDING";
  const waitLabel = locationName
    ? waiting
      ? `Drawing ${locationName} and its surroundings…`
      : `Approaching ${locationName}`
    : waiting
      ? "Drawing the surroundings…"
      : "Uncharted lands";

  if (variant === "hero") {
    return (
      <div className="scene-hero relative">
        <div className="scene-hero-frame overflow-hidden">
          {url ? (
            <img
              key={artKey}
              src={url}
              alt={locationName || "Location"}
              className="h-full w-full object-cover object-center"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-panel-2/40">
              <p className="px-4 text-center text-xs text-muted">{waitLabel}</p>
            </div>
          )}
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#0a090c] via-[#0a090c]/75 to-transparent px-6 pb-3 pt-14 md:px-10">
          <p className="display-text text-base tracking-[0.08em] text-accent sm:text-lg">
            {locationName || "Unknown"}
          </p>
          {locationType ? (
            <p className="mt-0.5 text-[0.65rem] uppercase tracking-[0.16em] text-muted">
              {locationType}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="map-frame relative w-full overflow-hidden">
      {url ? (
        <img
          key={artKey}
          src={url}
          alt={locationName || "Location"}
          className="aspect-[14/9] w-full object-cover"
        />
      ) : (
        <div className="flex aspect-[14/9] items-center justify-center px-3 text-center text-xs text-muted">
          {waiting ? waitLabel : locationName || "Uncharted"}
        </div>
      )}
    </div>
  );
}
