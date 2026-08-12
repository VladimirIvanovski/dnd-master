import { lazy, Suspense, useState } from "react";
import type { DiceResult } from "../../types/game";
import { useUiStore } from "../../stores/uiStore";
import {
  playDiceCrit,
  playDiceLand,
  playTableBounce,
  unlockDiceAudio,
} from "../../lib/diceSounds";

const Dice3D = lazy(() =>
  import("../dice/Dice3D").then((m) => ({ default: m.Dice3D })),
);

/**
 * Tabletop 3D D20 toss — reveals server-predetermined result.
 * Never triggers another gameplay / LLM request.
 */
export function DiceFocus() {
  const dice = useUiStore((s) => s.diceOverlay);
  const clear = useUiStore((s) => s.clearDiceOverlay);
  if (!dice) return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-50 flex items-end justify-center pb-20 sm:items-center sm:pb-0">
      <div className="pointer-events-auto w-[min(52rem,96vw)]">
        <DiceCheckCard result={dice} onDone={clear} />
      </div>
    </div>
  );
}

type CardProps = {
  result: DiceResult;
  onDone?: () => void;
};

export function DiceCheckCard({ result, onDone }: CardProps) {
  const [phase, setPhase] = useState<"idle" | "rolling" | "done">("idle");

  const natural = Math.max(1, Math.min(20, result.natural ?? result.rolls[0] ?? result.total));
  const mod = result.modifier ?? 0;
  const label = (result.skill || result.purpose || "Check").toUpperCase();
  const outcome =
    result.success === true ? "SUCCESS" : result.success === false ? "FAILURE" : "ROLLED";
  const crit =
    result.critical === "natural_20"
      ? "NATURAL 20"
      : result.critical === "natural_1"
        ? "NATURAL 1"
        : null;

  const roll = () => {
    if (phase !== "idle") return;
    unlockDiceAudio();
    setPhase("rolling");
  };

  const onSettled = () => {
    playDiceLand();
    if (result.critical === "natural_20") playDiceCrit(true);
    if (result.critical === "natural_1") playDiceCrit(false);
    setPhase("done");
    window.setTimeout(() => onDone?.(), 2800);
  };

  return (
    <div className="overflow-hidden border border-amber-900/50 bg-[#0c0a0e]/92 shadow-[0_20px_60px_rgba(0,0,0,0.65)] backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-amber-900/40 px-4 py-2">
        <div>
          <p className="text-[0.65rem] uppercase tracking-[0.22em] text-amber-200/80">
            {label} CHECK
          </p>
          {result.dc != null ? (
            <p className="text-[0.65rem] text-muted">DC {result.dc}</p>
          ) : null}
        </div>
        {phase === "idle" ? (
          <p className="text-xs text-amber-100/80">Click the table to toss the die</p>
        ) : null}
        {phase === "done" ? (
          <div className="text-right animate-[fade-in_0.35s_ease-out]">
            <p className="text-sm text-parchment">
              <span className="text-violet-200">{natural}</span>
              {mod !== 0 ? (
                <span className="text-muted">
                  {" "}
                  {mod >= 0 ? "+" : ""}
                  {mod}
                  {result.skill ? ` ${result.skill}` : ""}
                </span>
              ) : null}
              <span className="display-text ml-2 text-accent">= {result.total}</span>
            </p>
            <p className="flex justify-end gap-2 text-xs tracking-[0.18em]">
              {crit ? (
                <span className={result.critical === "natural_20" ? "text-accent" : "text-danger"}>
                  {crit}
                </span>
              ) : null}
              <span
                className={
                  result.success === true
                    ? "text-success"
                    : result.success === false
                      ? "text-danger"
                      : "text-accent"
                }
              >
                {outcome}
              </span>
            </p>
          </div>
        ) : null}
      </div>

      <button
        type="button"
        onClick={roll}
        disabled={phase !== "idle"}
        className="block w-full outline-none focus-visible:ring-2 focus-visible:ring-violet-400 disabled:cursor-default"
        aria-label={phase === "idle" ? "Toss the D20 on the table" : "Dice result"}
      >
        <Suspense
          fallback={
            <div className="flex h-[min(52vh,28rem)] items-center justify-center bg-[#1a120c] text-amber-200/70">
              Preparing the table…
            </div>
          }
        >
          <Dice3D
            target={natural}
            rolling={phase === "rolling"}
            onSettled={phase === "rolling" ? onSettled : undefined}
            onBounce={(i) => playTableBounce(i)}
            className="h-[min(52vh,28rem)] w-full bg-gradient-to-b from-[#1a1410] to-[#0a0806]"
          />
        </Suspense>
      </button>
    </div>
  );
}
