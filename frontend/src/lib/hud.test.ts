import { describe, expect, it } from "vitest";
import { formatGameTime, weatherIcon, xpProgress } from "./hud";

describe("hud", () => {
  it("clamps xp progress", () => {
    const p = xpProgress(1, 0);
    expect(p.pct).toBeGreaterThanOrEqual(0);
    expect(p.pct).toBeLessThanOrEqual(100);
    expect(p.label).toContain("/");
  });

  it("guards timestamp-like times", () => {
    expect(formatGameTime("12:00:00+00")).toBe("Day 1, Morning");
    expect(formatGameTime("Day 2, Dusk")).toBe("Day 2, Dusk");
  });

  it("picks a weather icon", () => {
    expect(weatherIcon("Storm")).toBe("⛈");
    expect(weatherIcon("Clear")).toBe("☀");
  });
});
