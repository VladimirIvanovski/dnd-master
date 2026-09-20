import { useEffect } from "react";
import { useRevealText } from "../../hooks/useRevealText";
import { DustRevealText, StoryMarkup } from "./StoryMarkup";

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
    msPerChunk: 25,
    charsPerChunk: 1,
    onDone: onRevealDone,
  });

  useEffect(() => {
    onSkipReady?.(skip);
  }, [onSkipReady, skip]);

  const display = streaming || !active ? text : shown;
  const useDrop = !streaming && (!active || done) && text.trim().length > 90;
  const dusting = active && !done;

  return (
    <div
      className={`story-text text-[1.14rem] leading-[1.85] text-parchment/92 md:text-[1.22rem] md:leading-[1.9] ${
        streaming || dusting ? "opacity-95" : ""
      }`}
    >
      {dusting ? (
        <p className="story-para">
          <DustRevealText text={display} />
        </p>
      ) : (
        <StoryMarkup text={display} dropCap={useDrop} />
      )}
      {(streaming || dusting) && display ? (
        <span className="story-reveal-caret" aria-hidden />
      ) : null}
    </div>
  );
}
