type Props = {
  locationName?: string;
};

export function MapPanel({ locationName }: Props) {
  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Map</p>
      <div className="flex h-24 items-center justify-center rounded border border-dashed border-border bg-ink/50 text-sm text-muted">
        {locationName ? `Region around ${locationName}` : "Uncharted"}
      </div>
    </section>
  );
}
