import { useEffect, useMemo, useState } from "react";
import { loadAssetObjectUrl, visualApi, type MapData } from "../../api/visuals";

type Props = {
  campaignId: string;
  currentLocationId?: string | null;
};

const W = 560;
const H = 360;

export function WorldMapPanel({ campaignId, currentLocationId }: Props) {
  const [data, setData] = useState<MapData | null>(null);
  const [artUrl, setArtUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    let timer: number | undefined;

    async function load() {
      try {
        const d = await visualApi.campaignMap(campaignId);
        if (cancelled) return;
        setData(d);
        if (d.art_status === "READY" && d.art_url) {
          objectUrl = await loadAssetObjectUrl(d.art_url);
          if (!cancelled) setArtUrl(objectUrl);
          return;
        }
        if (d.art_status === "QUEUED" || d.art_status === "GENERATING" || d.art_status === "PENDING") {
          timer = window.setTimeout(() => void load(), 2500);
        }
      } catch {
        /* keep SVG fallback */
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [campaignId]);

  const nodes = useMemo(() => {
    const locs = data?.locations ?? [];
    if (!locs.length) return [];
    return locs.map((loc, i) => {
      const angle = (Math.PI * 2 * i) / Math.max(locs.length, 1) - Math.PI / 2;
      const radius = locs.length === 1 ? 0 : 90 + (i % 3) * 28;
      const cx = W / 2 + Math.cos(angle) * radius;
      const cy = H / 2 + Math.sin(angle) * radius * 0.75;
      return {
        ...loc,
        x: locs.length === 1 ? W / 2 : cx,
        y: locs.length === 1 ? H / 2 : cy,
      };
    });
  }, [data]);

  const status = data?.art_status;

  return (
    <section>
      <div className="map-frame relative w-full overflow-hidden">
        {artUrl ? (
          <img
            src={artUrl}
            alt="World map"
            className="absolute inset-0 h-full w-full object-cover opacity-90"
          />
        ) : (
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,#2a2418,#0c100c)]" />
        )}
        {!artUrl && (status === "QUEUED" || status === "GENERATING" || status === "PENDING") ? (
          <p className="absolute inset-x-0 top-2 z-10 text-center text-[0.65rem] uppercase tracking-wide text-accent/80">
            Charting the realm…
          </p>
        ) : null}
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="relative z-[1] w-full"
          role="img"
          aria-label="World map"
        >
          {!artUrl ? (
            <>
              <defs>
                <pattern id="mapGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#2a3340" strokeWidth="0.6" />
                </pattern>
              </defs>
              <rect width={W} height={H} fill="url(#mapGrid)" opacity="0.35" />
              <ellipse cx={W * 0.35} cy={H * 0.55} rx={140} ry={70} fill="#1c261c" opacity="0.55" />
              <ellipse cx={W * 0.7} cy={H * 0.4} rx={110} ry={55} fill="#1a221a" opacity="0.5" />
            </>
          ) : (
            <rect width={W} height={H} fill="transparent" />
          )}

          {nodes.length > 1
            ? nodes.map((a, i) => {
                const b = nodes[(i + 1) % nodes.length];
                return (
                  <line
                    key={`edge-${a.id}`}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke="#c4a35a"
                    strokeWidth="1.5"
                    strokeDasharray="4 4"
                    opacity="0.7"
                  />
                );
              })
            : null}

          {nodes.map((loc) => {
            const here = loc.id === currentLocationId;
            return (
              <g key={loc.id} className="cursor-pointer">
                <title>{`${loc.name} (${loc.type})`}</title>
                {here ? (
                  <circle
                    cx={loc.x}
                    cy={loc.y}
                    r={26}
                    fill="none"
                    stroke="#c9a227"
                    className="marker-pulse"
                  />
                ) : null}
                <circle
                  cx={loc.x}
                  cy={loc.y}
                  r={here ? 14 : 9}
                  fill={here ? "#c9a227" : "#1a1f28"}
                  stroke="#c9a227"
                  strokeWidth={here ? 2.5 : 1.5}
                />
                <text
                  x={loc.x}
                  y={loc.y + (here ? 32 : 24)}
                  textAnchor="middle"
                  fill="#f2efe6"
                  fontSize="12"
                  fontFamily="Cinzel, serif"
                  style={{ paintOrder: "stroke", stroke: "#0b0d10", strokeWidth: 3 }}
                >
                  {loc.name}
                </text>
                <text
                  x={loc.x}
                  y={loc.y + (here ? 46 : 38)}
                  textAnchor="middle"
                  fill="#c4c9d1"
                  fontSize="9"
                  style={{ paintOrder: "stroke", stroke: "#0b0d10", strokeWidth: 2 }}
                >
                  {loc.type}
                </text>
              </g>
            );
          })}

          {nodes.length === 0 ? (
            <text x={W / 2} y={H / 2} textAnchor="middle" fill="#8b95a5" fontSize="13">
              No discovered locations yet
            </text>
          ) : null}
        </svg>
      </div>
    </section>
  );
}
