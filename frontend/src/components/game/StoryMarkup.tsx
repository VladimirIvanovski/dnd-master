import type { ReactNode } from "react";

/** Render DM narration with paragraph breaks and sparse **bold**. */
export function StoryMarkup({
  text,
  dropCap = false,
  className = "",
}: {
  text: string;
  dropCap?: boolean;
  className?: string;
}) {
  const paragraphs = splitParagraphs(text);
  if (paragraphs.length === 0) return null;

  return (
    <div className={className}>
      {paragraphs.map((para, i) => (
        <p
          key={i}
          className={`story-para ${i === 0 && dropCap ? "drop-cap" : ""} ${
            i < paragraphs.length - 1 ? "mb-4" : ""
          }`}
        >
          {renderInline(para)}
        </p>
      ))}
    </div>
  );
}

export function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  // Complete **bold** pairs only — incomplete markers stay as plain text while typing
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    nodes.push(
      <strong key={key++} className="story-em">
        {m[1]}
      </strong>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function splitParagraphs(text: string): string[] {
  return text
    .replace(/\r\n/g, "\n")
    .split(/\n\s*\n/)
    .map((p) => p.replace(/\n/g, " ").trim())
    .filter(Boolean);
}
