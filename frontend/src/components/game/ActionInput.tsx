import { useEffect, useRef, useState } from "react";

type Props = {
  disabled?: boolean;
  suggestions?: string[];
  placeholder?: string;
  onSubmit: (action: string) => void;
};

const ROMAN = ["I", "II", "III"] as const;

export function ActionInput({
  disabled,
  suggestions = [],
  placeholder = "What do you attempt…",
  onSubmit,
}: Props) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const [customOpen, setCustomOpen] = useState(suggestions.length === 0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (suggestions.length > 0 && !disabled) {
      setCustomOpen(false);
      setValue("");
    }
  }, [suggestions, disabled]);

  const submit = (action: string) => {
    const text = action.trim();
    if (!text || disabled) return;
    onSubmit(text);
    setValue("");
  };

  const openCustom = () => {
    setCustomOpen(true);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const showChoices = suggestions.length > 0;
  const choiceCount = Math.min(suggestions.length, 3) + (showChoices ? 1 : 0);
  const twoCol = choiceCount >= 4;

  return (
    <div className={`action-bar relative mx-auto w-full max-w-[52rem] ${disabled ? "is-busy" : ""}`}>
      <p className="mb-3 text-center text-[0.78rem] uppercase tracking-[0.22em] text-muted">
        What do you do?
      </p>

      {showChoices ? (
        <div
          className={`mb-3 grid gap-2.5 ${twoCol ? "sm:grid-cols-2" : ""}`}
          role="group"
          aria-label="Suggested actions"
        >
          {suggestions.slice(0, 3).map((opt, i) => (
            <button
              key={`${i}-${opt}`}
              type="button"
              disabled={disabled}
              onClick={() => submit(opt)}
              className="action-choice group text-left"
            >
              <span className="action-choice-num" aria-hidden>
                {ROMAN[i] ?? String(i + 1)}
              </span>
              <span className="min-w-0 flex-1 text-[1.05rem] leading-snug text-parchment/92 group-hover:text-parchment md:text-[1.12rem]">
                {opt}
              </span>
            </button>
          ))}
          <button
            type="button"
            disabled={disabled}
            onClick={openCustom}
            className={`action-choice action-choice-custom ${customOpen ? "is-active" : ""} ${
              twoCol ? "sm:col-span-2" : ""
            }`}
            aria-expanded={customOpen}
          >
            <span className="action-choice-num" aria-hidden>
              IV
            </span>
            <span className="text-[1.05rem] leading-snug text-parchment/80 md:text-[1.12rem]">
              Something else… <span className="text-muted">your own words</span>
            </span>
          </button>
        </div>
      ) : null}

      {(customOpen || !showChoices) && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(value);
          }}
        >
          <div
            className={`action-console flex items-stretch overflow-hidden ${
              focused ? "is-focused" : ""
            }`}
          >
            <input
              ref={inputRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              disabled={disabled}
              placeholder={disabled ? "Resolving…" : placeholder}
              aria-label="Custom action"
              className="story-text min-w-0 flex-1 border-0 bg-transparent px-4 py-3.5 text-[1.12rem] text-parchment outline-none placeholder:text-muted/70 disabled:opacity-55 md:text-[1.18rem]"
            />
            <button
              type="submit"
              disabled={disabled || !value.trim()}
              className="display-text shrink-0 border-l border-border/50 bg-[#2a2418] px-5 text-[0.78rem] tracking-[0.18em] text-accent transition hover:bg-[#3a3020] hover:text-[#e8d4a0] disabled:opacity-35"
            >
              {disabled ? "…" : "ACT"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
