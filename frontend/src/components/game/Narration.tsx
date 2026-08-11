type Props = {
  text: string;
  streaming?: boolean;
};

export function Narration({ text, streaming = false }: Props) {
  return (
    <div className={`story-text text-base leading-relaxed text-text/95 ${streaming ? "opacity-90" : ""}`}>
      {text}
      {streaming ? <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-accent align-middle" /> : null}
    </div>
  );
}
