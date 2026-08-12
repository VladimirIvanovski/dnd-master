import { useCallback, useEffect, useRef } from "react";

type Props = {
  side: "left" | "right";
  onResize: (deltaX: number) => void;
};

/** Drag handle between dock and story. */
export function DockResizeHandle({ side, onResize }: Props) {
  const dragging = useRef(false);
  const lastX = useRef(0);

  const onPointerMove = useCallback(
    (e: PointerEvent) => {
      if (!dragging.current) return;
      const dx = e.clientX - lastX.current;
      lastX.current = e.clientX;
      onResize(side === "left" ? dx : -dx);
    },
    [onResize, side],
  );

  const stop = useCallback(() => {
    dragging.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stop);
    window.addEventListener("pointercancel", stop);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stop);
      window.removeEventListener("pointercancel", stop);
    };
  }, [onPointerMove, stop]);

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={`Resize ${side} panel`}
      tabIndex={0}
      className="group relative z-10 hidden w-1.5 shrink-0 cursor-col-resize bg-accent/20 hover:bg-accent/50 lg:block"
      onPointerDown={(e) => {
        dragging.current = true;
        lastX.current = e.clientX;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") onResize(side === "left" ? -16 : 16);
        if (e.key === "ArrowRight") onResize(side === "left" ? 16 : -16);
      }}
    >
      <span className="pointer-events-none absolute inset-y-0 -left-1 -right-1" />
    </div>
  );
}
