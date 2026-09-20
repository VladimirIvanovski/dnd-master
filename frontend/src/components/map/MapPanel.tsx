import { WorldMapPanel } from "../visual/WorldMapPanel";

type Place = {
  id: string;
  name: string;
  location_type: string;
  here?: boolean;
};

type Props = {
  places?: Place[];
  onTravel?: (name: string) => void;
  campaignId?: string;
  currentLocationId?: string | null;
};

export function MapPanel({
  places = [],
  onTravel,
  campaignId,
  currentLocationId,
}: Props) {
  return (
    <section>
      {campaignId ? (
        <div className="mb-3">
          <WorldMapPanel
            campaignId={campaignId}
            currentLocationId={currentLocationId}
            onSelect={onTravel}
          />
        </div>
      ) : null}
      {places.length === 0 ? (
        <p className="text-sm text-muted">No discovered places yet.</p>
      ) : (
        <>
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Known places</p>
          <ul className="space-y-2">
            {places.map((place) => (
              <li key={place.id}>
                <button
                  type="button"
                  disabled={place.here || !onTravel}
                  onClick={() => onTravel?.(place.name)}
                  className={`flex w-full items-center justify-between rounded border px-3 py-2 text-left ${
                    place.here
                      ? "border-accent/50 bg-accent/10 text-accent"
                      : "border-border/60 bg-panel-2 text-parchment hover:border-accent/40"
                  }`}
                >
                  <span>
                    {place.name}
                    <span className="ml-2 text-xs uppercase tracking-[0.12em] text-muted">
                      {place.location_type}
                    </span>
                  </span>
                  <span className="text-xs text-muted">{place.here ? "here" : "travel"}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
