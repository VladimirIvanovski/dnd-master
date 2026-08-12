import { useState } from "react";
import { useUiStore } from "../../stores/uiStore";

type QuestLike = {
  id: string;
  title: string;
  status: string;
  description?: string;
  objectives: Array<string | { description: string; is_completed?: boolean }>;
};

type Props = {
  title?: string;
  quests: QuestLike[];
  emptyText?: string;
};

export function QuestPanel({ title = "Quests", quests, emptyText = "No quests yet." }: Props) {
  const tab = useUiStore((s) => s.panelPrefs.quests?.tab) || "active";
  const setPanelTab = useUiStore((s) => s.setPanelTab);
  const [expanded, setExpanded] = useState<string | null>(null);

  const active = quests.filter((q) => q.status === "active");
  const completed = quests.filter((q) => q.status === "completed");
  const failed = quests.filter((q) => q.status === "failed");
  const list = tab === "completed" ? completed : tab === "failed" ? failed : active;

  return (
    <section>
      <p className="label-caps mb-2">{title}</p>
      <div className="mb-3 flex flex-wrap gap-1">
        {(
          [
            ["active", "Active"],
            ["completed", "Completed"],
            ["failed", "Failed"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setPanelTab("quests", id)}
            className={`btn-fantasy px-2 py-1 text-[0.65rem] uppercase tracking-[0.12em] ${
              tab === id ? "is-active" : ""
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {list.length === 0 ? (
        <p className="text-sm text-muted">{emptyText}</p>
      ) : (
        <div className="space-y-2">
          {list.map((q) => {
            const open = expanded === q.id;
            const done = q.status === "completed";
            return (
              <div
                key={q.id}
                className={`border bg-panel-2/40 transition-[border-color,box-shadow] duration-200 ${
                  done
                    ? "border-success/40 shadow-[0_0_12px_rgba(90,143,74,0.12)]"
                    : "border-accent/20 hover:border-accent/40"
                }`}
              >
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-3 py-2 text-left"
                  onClick={() => setExpanded(open ? null : q.id)}
                  aria-expanded={open}
                >
                  <span className="text-sm font-medium text-accent">{q.title}</span>
                  <span className="text-xs text-muted">{open ? "−" : "+"}</span>
                </button>
                {open ? (
                  <div className="border-t border-border/50 px-3 py-2">
                    {q.description ? (
                      <p className="mb-2 text-xs text-muted">{q.description}</p>
                    ) : null}
                    <ul className="space-y-1 text-xs text-muted">
                      {q.objectives.map((obj, i) => {
                        const text = typeof obj === "string" ? obj : obj.description;
                        const done = typeof obj === "string" ? false : Boolean(obj.is_completed);
                        return (
                          <li key={`${q.id}-${i}`} className={done ? "line-through" : ""}>
                            {done ? "✓" : "•"} {text}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
