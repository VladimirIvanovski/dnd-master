import { useEffect, useRef, type ReactNode } from "react";

type Props = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  widthClass?: string;
};

export function SlideOver({
  open,
  title,
  onClose,
  children,
  widthClass = "w-full max-w-md",
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const t = window.setTimeout(() => {
      panelRef.current?.querySelector<HTMLElement>("button, [href], input, textarea")?.focus();
    }, 50);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(t);
      previouslyFocused.current?.focus?.();
    };
  }, [open, onClose]);

  return (
    <div
      className={`fixed inset-0 z-40 ${open ? "pointer-events-auto" : "pointer-events-none"}`}
      aria-hidden={!open}
    >
      <button
        type="button"
        className={`absolute inset-0 bg-black/55 transition-opacity duration-300 motion-reduce:transition-none ${
          open ? "opacity-100" : "opacity-0"
        }`}
        aria-label="Close panel"
        tabIndex={open ? 0 : -1}
        onClick={onClose}
      />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`absolute inset-y-0 right-0 flex ${widthClass} flex-col border-l border-accent/25 bg-panel shadow-2xl transition-transform duration-300 ease-out motion-reduce:transition-none max-md:inset-x-0 max-md:top-auto max-md:h-[85vh] max-md:rounded-t-lg max-md:border-l-0 max-md:border-t ${
          open ? "translate-x-0 max-md:translate-y-0" : "translate-x-full max-md:translate-y-full"
        }`}
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-accent/20 px-4 py-3">
          <h2 className="display-text text-lg text-accent">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="btn-fantasy px-2 py-1 text-muted hover:text-text"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">{children}</div>
      </aside>
    </div>
  );
}
