import { useEffect, useRef, type ReactNode } from "react";

type Props = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  breadcrumb?: string;
};

export function MapOverlay({ open, title, onClose, children, breadcrumb }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <div
      className={`fixed inset-0 z-40 flex items-center justify-center p-4 md:p-8 ${
        open ? "pointer-events-auto" : "pointer-events-none"
      }`}
      aria-hidden={!open}
    >
      <button
        type="button"
        className={`absolute inset-0 bg-black/65 transition-opacity duration-300 motion-reduce:transition-none ${
          open ? "opacity-100" : "opacity-0"
        }`}
        aria-label="Close map"
        tabIndex={open ? 0 : -1}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`panel-ornate relative z-10 flex h-full max-h-[min(90vh,900px)] w-full max-w-4xl flex-col overflow-hidden transition-all duration-300 motion-reduce:transition-none ${
          open ? "scale-100 opacity-100" : "scale-95 opacity-0"
        }`}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-accent/20 px-4 py-3">
          <div>
            <h2 className="display-text text-lg tracking-[0.08em] text-accent">{title}</h2>
            {breadcrumb ? <p className="mt-1 text-xs text-muted">{breadcrumb}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="btn-fantasy px-2 py-1 text-muted hover:text-accent" aria-label="Close">
            ✕
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-4">{children}</div>
      </div>
    </div>
  );
}
