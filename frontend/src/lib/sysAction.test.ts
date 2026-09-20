import { describe, expect, it } from "vitest";
import { playerActionLabel } from "./sysAction";

describe("playerActionLabel", () => {
  it("keeps free text", () => {
    expect(playerActionLabel("Look around")).toBe("Look around");
  });

  it("labels combat and talk commands", () => {
    expect(playerActionLabel("sys:move:0:1")).toBe("Move.");
    expect(playerActionLabel("sys:strike:abc")).toBe("Strike.");
    expect(playerActionLabel("sys:advance")).toBe("End turn.");
    expect(playerActionLabel("sys:ask:1:well")).toBe("Ask about that.");
    expect(playerActionLabel("sys:save:camp")).toBe("Save checkpoint.");
  });
});
