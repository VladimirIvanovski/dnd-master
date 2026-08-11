type Props = {
  label?: string;
  className?: string;
};

export function LoadingState({ label = "Loading…", className = "" }: Props) {
  return (
    <div className={`flex items-center gap-3 text-muted ${className}`}>
      <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-accent" />
      <span>{label}</span>
    </div>
  );
}
