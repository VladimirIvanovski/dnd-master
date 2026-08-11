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
  const main = quests.filter((q) => q.status === "active");
  const completed = quests.filter((q) => q.status === "completed");

  return (
    <section>
      <p className="mb-2 text-xs uppercase tracking-[0.18em] text-muted">{title}</p>
      {quests.length === 0 ? (
        <p className="text-sm text-muted">{emptyText}</p>
      ) : (
        <div className="space-y-3">
          {main.map((q) => (
            <QuestCard key={q.id} quest={q} />
          ))}
          {completed.length > 0 ? (
            <div>
              <p className="mb-1 text-xs text-muted">Completed</p>
              {completed.map((q) => (
                <QuestCard key={q.id} quest={q} dim />
              ))}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

function QuestCard({ quest, dim }: { quest: QuestLike; dim?: boolean }) {
  return (
    <div className={`rounded border border-border bg-panel-2 p-2 ${dim ? "opacity-60" : ""}`}>
      <p className="text-sm font-medium text-accent">{quest.title}</p>
      {quest.description ? <p className="mt-1 text-xs text-muted">{quest.description}</p> : null}
      <ul className="mt-2 space-y-1 text-xs text-muted">
        {quest.objectives.map((obj, i) => {
          const text = typeof obj === "string" ? obj : obj.description;
          const done = typeof obj === "string" ? false : Boolean(obj.is_completed);
          return (
            <li key={`${quest.id}-${i}`} className={done ? "line-through" : ""}>
              {done ? "✓" : "•"} {text}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
