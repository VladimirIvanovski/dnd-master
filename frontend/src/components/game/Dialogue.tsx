type Props = {
  speaker: string;
  text: string;
};

export function Dialogue({ speaker, text }: Props) {
  return (
    <div className="rounded border-l-2 border-accent/60 bg-panel-2/80 px-3 py-2">
      <p className="display-text text-sm text-accent">{speaker}</p>
      <p className="story-text mt-1 text-[0.95rem] italic text-text/90">“{text}”</p>
    </div>
  );
}
