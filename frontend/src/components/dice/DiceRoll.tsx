import type { DiceResult } from "../../types/game";

type Props = {
  result: DiceResult;
};

export function DiceRoll({ result }: Props) {
  const outcome =
    result.success === true ? "Success" : result.success === false ? "Failure" : null;

  return (
    <div className="glow-accent mx-auto w-full max-w-xs animate-[dice-pop_0.55s_ease-out] rounded-lg border border-accent/30 bg-panel-2 px-4 py-3 text-center">
      <p className="text-xs uppercase tracking-[0.2em] text-muted">
        {result.purpose || "Dice Roll"}
      </p>
      <div className="display-text mt-2 space-y-1 text-lg">
        <div className="animate-[dice-spin_0.45s_ease-out]">{result.notation}</div>
        <div className="text-sm text-muted">rolls: {result.rolls.join(", ") || "—"}</div>
        <div className="border-t border-border pt-1 text-accent">= {result.total}</div>
      </div>
      {outcome ? (
        <p className={`mt-2 text-sm ${result.success ? "text-success" : "text-danger"}`}>
          {outcome}
        </p>
      ) : null}
    </div>
  );
}
