import type { DiceResult } from "../../types/game";

type Props = {
  result: DiceResult;
  compact?: boolean;
};

/** Story-log outcome with roll formula + Success / Failure seal. */
export function DiceRoll({ result }: Props) {
  const ok = result.success === true;
  const fail = result.success === false;
  const natural = result.natural ?? result.rolls[0];
  const mod = result.modifier ?? 0;
  const modPart = mod === 0 ? "" : ` ${mod >= 0 ? "+" : "−"} ${Math.abs(mod)}`;
  const formula =
    natural != null ? `${natural}${modPart} = ${result.total}` : `${result.total}`;
  const vsDc = result.dc != null ? ` vs DC ${result.dc}` : "";
  const label = (result.skill || result.purpose || "Check").trim();

  return (
    <div
      className={`check-seal mx-auto max-w-md ${
        ok ? "is-success" : fail ? "is-failure" : ""
      }`}
    >
      <p className="check-seal-label">{label}</p>
      <p className="check-seal-formula">
        {formula}
        {vsDc}
      </p>
      <p className="check-seal-outcome">
        {ok ? "Success" : fail ? "Failure" : "Rolled"}
      </p>
      {result.critical === "natural_20" ? (
        <p className="check-seal-crit">Natural twenty</p>
      ) : null}
      {result.critical === "natural_1" ? (
        <p className="check-seal-crit">Natural one</p>
      ) : null}
    </div>
  );
}
