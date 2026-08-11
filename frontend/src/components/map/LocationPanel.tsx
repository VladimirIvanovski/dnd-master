type Props = {
  name?: string;
  description?: string;
  locationType?: string;
};

export function LocationPanel({ name, description, locationType }: Props) {
  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Location</p>
      {name ? (
        <div className="rounded border border-border bg-panel-2 p-2">
          <p className="display-text text-accent">{name}</p>
          {locationType ? <p className="text-xs uppercase tracking-wide text-muted">{locationType}</p> : null}
          {description ? <p className="mt-2 text-sm text-muted">{description}</p> : null}
        </div>
      ) : (
        <p className="text-sm text-muted">Unknown lands.</p>
      )}
    </section>
  );
}
