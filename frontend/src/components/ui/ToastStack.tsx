import { useUiStore } from "../../stores/uiStore";

export function ToastStack() {
  const notifications = useUiStore((s) => s.notifications);
  const dismiss = useUiStore((s) => s.dismissNotification);

  if (!notifications.length) return null;

  return (
    <div
      className="pointer-events-none fixed right-4 top-4 z-50 flex w-72 max-w-[90vw] flex-col gap-2"
      aria-live="polite"
    >
      {notifications.map((n) => (
        <div
          key={n.id}
          className="pointer-events-auto animate-[toast-in_0.3s_ease-out] border border-accent/25 bg-panel/95 px-3 py-2 shadow-lg backdrop-blur-sm motion-reduce:animate-none"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="display-text text-sm text-accent">{n.title}</p>
              {n.body ? <p className="mt-0.5 text-xs text-muted">{n.body}</p> : null}
            </div>
            <button
              type="button"
              className="text-muted hover:text-text"
              aria-label="Dismiss"
              onClick={() => dismiss(n.id)}
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
