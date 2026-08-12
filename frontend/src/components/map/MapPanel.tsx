type Props = {
  locationName?: string;
};

export function MapPanel({ locationName }: Props) {
  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Map</p>
      <div className="flex h-20 items-center justify-center rounded border border-dashed border-border bg-ink/50 px-2 text-center text-xs text-muted">
        {locationName ? `Region around ${locationName}` : "Uncharted"}
      </div>
    </section>
  );
}
