type Props = {
  title?: string;
  message: string;
  onRetry?: () => void;
};

export function ErrorState({ title = "Something went wrong", message, onRetry }: Props) {
  return (
    <div className="panel rounded-lg p-4 text-sm">
      <p className="display-text text-danger mb-1">{title}</p>
      <p className="text-muted mb-3">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded border border-border px-3 py-1.5 text-accent hover:bg-panel-2"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
