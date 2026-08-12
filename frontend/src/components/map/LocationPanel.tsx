type Props = {
  name?: string;
  description?: string;
  locationType?: string;
};

export function LocationPanel({ name, description, locationType }: Props) {
  const short =
    description && description.length > 140
      ? `${description.slice(0, 140).trim()}…`
      : description;

  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">Location</p>
      {name ? (
        <div className="rounded border border-border bg-panel-2 p-2">
          <p className="display-text text-accent">{name}</p>
          {locationType ? (
            <p className="text-xs uppercase tracking-wide text-muted">{locationType}</p>
          ) : null}
          {short ? <p className="mt-2 text-xs leading-relaxed text-muted">{short}</p> : null}
        </div>
      ) : (
        <p className="text-sm text-muted">Unknown lands.</p>
      )}
    </section>
  );
}
