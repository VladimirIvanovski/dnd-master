import { useEffect } from "react";
import { useRevealText } from "../../hooks/useRevealText";
import { DustRevealText, renderInline } from "./StoryMarkup";

type Props = {
  speaker: string;
  text: string;
  reveal?: boolean;
  onRevealDone?: () => void;
  onSkipReady?: (skip: () => void) => void;
};

export function Dialogue({ speaker, text, reveal = false, onRevealDone, onSkipReady }: Props) {
  const { shown, done, skip } = useRevealText(text, {
    active: reveal,
    msPerChunk: 25,
    charsPerChunk: 1,
    onDone: onRevealDone,
  });

  useEffect(() => {
    onSkipReady?.(skip);
  }, [onSkipReady, skip]);

  const display = reveal ? shown : text;
  const dusting = reveal && !done;

  return (
    <div className="dialogue-line mx-auto max-w-3xl">
      <p className="display-text mb-1.5 text-[0.8rem] tracking-[0.12em] text-accent/90">{speaker}</p>
      <p className="story-text border-l border-bronze/50 pl-3.5 text-[1.08rem] leading-[1.75] italic text-parchment/85 md:text-[1.12rem]">
        “
        {dusting ? <DustRevealText text={display} /> : renderInline(display)}
        ”
        {dusting && display ? <span className="story-reveal-caret" aria-hidden /> : null}
      </p>
    </div>
  );
}
