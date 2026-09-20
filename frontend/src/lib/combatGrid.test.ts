import { describe, expect, it } from "vitest";
import { cellIntent, combatFlagLine, isYourTurn } from "./combatGrid";

const combat = {
  whose_turn: "Hero",
  can_move: true,
  can_strike: true,
  combatants: [
    { id: "h", name: "Hero", combatant_type: "player", x: 3, y: 1 },
    { id: "w", name: "Wolf", combatant_type: "enemy", x: 3, y: 2 },
  ],
};

describe("combat grid", () => {
  it("knows the player turn and flags", () => {
    expect(isYourTurn(combat)).toBe(true);
    expect(isYourTurn({ ...combat, whose_turn: "Wolf" })).toBe(false);
    expect(combatFlagLine({ round_number: 2, whose_turn: "Hero", can_move: false })).toContain(
      "moved",
    );
  });

  it("maps clicks to strike or step", () => {
    expect(cellIntent(combat, 3, 2)).toBe("strike");
    expect(cellIntent(combat, 3, 0)).toBe("move");
    expect(cellIntent({ ...combat, can_move: false }, 3, 0)).toBe(null);
    expect(cellIntent({ ...combat, whose_turn: "Wolf" }, 3, 0)).toBe(null);
  });
});
