import { describe, expect, it } from "vitest";
import { revealedAfterSkip, splitChunks } from "./reveal";

describe("reveal", () => {
  it("splits by words", () => {
    expect(splitChunks("The door sticks.", 1).join("")).toBe("The door sticks.");
    expect(splitChunks("The door sticks.", 1).length).toBeGreaterThan(1);
  });

  it("skip shows the full line", () => {
    expect(revealedAfterSkip("The door sticks.")).toBe("The door sticks.");
  });
});
