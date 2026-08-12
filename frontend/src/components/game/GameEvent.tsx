type Props = {
  text: string;
};

export function GameEvent({ text }: Props) {
  return (
    <p className="mx-auto max-w-xl text-center text-[0.7rem] uppercase tracking-[0.16em] text-muted/80">
      {text}
    </p>
  );
}
