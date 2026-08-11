import { useState } from "react";

type Props = {
  disabled?: boolean;
  placeholder?: string;
  onSubmit: (action: string) => void;
};

export function ActionInput({
  disabled,
  placeholder = "What do you do?",
  onSubmit,
}: Props) {
  const [value, setValue] = useState("");

  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!value.trim() || disabled) return;
        onSubmit(value);
        setValue("");
      }}
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="w-full rounded-lg border border-border bg-ink px-3 py-2 text-sm outline-none ring-accent/40 placeholder:text-muted focus:ring-2 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="display-text rounded-lg border border-accent/40 bg-accent/15 px-4 py-2 text-sm text-accent hover:bg-accent/25 disabled:opacity-40"
      >
        Act
      </button>
    </form>
  );
}
