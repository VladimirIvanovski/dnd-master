import type { ReactNode } from "react";

type Props = {
  header: ReactNode;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  footer: ReactNode;
};

export function GameLayout({ header, left, center, right, footer }: Props) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      {header}
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[240px_minmax(0,1fr)_260px]">
        <aside className="panel min-h-0 overflow-y-auto border-b border-border p-3 lg:border-b-0 lg:border-r">
          {left}
        </aside>
        <main className="relative flex min-h-0 flex-col overflow-hidden border-b border-border lg:border-b-0">
          {center}
        </main>
        <aside className="panel min-h-0 overflow-y-auto p-3 lg:border-l lg:border-border">
          {right}
        </aside>
      </div>
      <div className="panel border-t border-border p-3">{footer}</div>
    </div>
  );
}
