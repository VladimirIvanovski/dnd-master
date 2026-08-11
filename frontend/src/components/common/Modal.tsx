import type { ReactNode } from "react";

type Props = {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
};

export function Modal({ open, title, children, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="panel glow-accent w-full max-w-lg rounded-xl p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="display-text text-lg text-accent">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-text"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
