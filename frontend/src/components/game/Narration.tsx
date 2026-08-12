import { useEffect } from "react";
import { useRevealText } from "../../hooks/useRevealText";
import { StoryMarkup } from "./StoryMarkup";

type Props = {
  text: string;
  streaming?: boolean;
  reveal?: boolean;
  onRevealDone?: () => void;
  onSkipReady?: (skip: () => void) => void;
};

export function Narration({
  text,
  streaming = false,
  reveal = false,
  onRevealDone,
  onSkipReady,
}: Props) {
  const active = reveal && !streaming;
  const { shown, done, skip } = useRevealText(text, {
    active,
    msPerChunk: 28,
    wordsPerChunk: 1,
    onDone: onRevealDone,
  });

  useEffect(() => {
    onSkipReady?.(skip);
  }, [onSkipReady, skip]);

  const display = streaming || !active ? text : shown;
  const useDrop = !streaming && (!active || done) && text.trim().length > 90;

  return (
    <div
      className={`story-text text-[1.14rem] leading-[1.85] text-parchment/92 md:text-[1.22rem] md:leading-[1.9] ${
        streaming || (active && !done) ? "opacity-95" : ""
      }`}
    >
      <StoryMarkup text={display} dropCap={useDrop} />
      {(streaming || (active && !done)) && display ? (
        <span className="story-reveal-caret" aria-hidden />
      ) : null}
    </div>
  );
}
