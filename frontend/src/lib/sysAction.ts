export function playerActionLabel(text: string): string {
  if (!text.startsWith("sys:")) return text;
  const kind = text.slice(4).split(":")[0];
  if (kind === "ask") return "Ask about that.";
  if (kind === "hear") return "Listen for a rumor.";
  if (kind === "move") return "Move.";
  if (kind === "strike") return "Strike.";
  if (kind === "advance") return "End turn.";
  if (kind === "save") return "Save checkpoint.";
  if (kind === "load") return "Load checkpoint.";
  return "Act.";
}
