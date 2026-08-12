/** Shared XP thresholds (mirrors backend engine). */
export const XP_THRESHOLDS = [0, 300, 900, 2700, 6500, 14000];

export function xpProgress(level: number, xp: number) {
  const lvl = Math.max(1, level);
  const currentFloor = XP_THRESHOLDS[Math.min(lvl, XP_THRESHOLDS.length - 1)] ?? 0;
  const next =
    XP_THRESHOLDS[Math.min(lvl + 1, XP_THRESHOLDS.length - 1)] ?? currentFloor + 300;
  const span = Math.max(1, next - currentFloor);
  const into = Math.max(0, xp - currentFloor);
  const pct = Math.max(0, Math.min(100, (into / span) * 100));
  return { currentFloor, next, into, pct, label: `${xp} / ${next}` };
}

export function formatGameTime(raw: string): string {
  if (!raw) return "Day 1, Morning";
  // Guard against accidental timestamp overwrite in DB.
  if (/^\d{1,2}:\d{2}/.test(raw) || raw.includes("+00") || raw.includes("T")) {
    return "Day 1, Morning";
  }
  return raw;
}

export function weatherIcon(weather?: string): string {
  const w = (weather || "").toLowerCase();
  if (w.includes("rain") || w.includes("storm")) return "⛈";
  if (w.includes("cloud") || w.includes("overcast")) return "☁";
  if (w.includes("snow") || w.includes("frost")) return "❄";
  if (w.includes("fog") || w.includes("mist")) return "〰";
  if (w.includes("night")) return "☾";
  return "☀";
}
