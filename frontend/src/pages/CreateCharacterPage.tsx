import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { characterApi } from "../api";
import { ErrorState } from "../components/common/ErrorState";

const ABILITIES = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
] as const;

const fieldClass =
  "mt-1 w-full rounded border border-border bg-ink px-3 py-2 outline-none focus:ring-2 focus:ring-accent/40";

export function CreateCharacterPage() {
  const [params] = useSearchParams();
  const campaignId = params.get("campaignId") ?? "";
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [race, setRace] = useState("Human");
  const [className, setClassName] = useState("Fighter");
  const [stats, setStats] = useState<Record<(typeof ABILITIES)[number], number>>({
    strength: 14,
    dexterity: 12,
    constitution: 14,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => Boolean(campaignId && name.trim()), [campaignId, name]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      const character = await characterApi.create({
        campaign_id: campaignId,
        name,
        race,
        class_name: className,
        ...stats,
      });
      localStorage.setItem(
        "dnd-session",
        JSON.stringify({ campaignId, characterId: character.id }),
      );
      navigate(`/game/${campaignId}/${character.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create character");
    } finally {
      setBusy(false);
    }
  }

  if (!campaignId) {
    return (
      <div className="mx-auto max-w-xl px-6 py-12">
        <ErrorState
          title="Campaign required"
          message="Create or select a campaign before forging a character."
        />
        <Link to="/campaigns/new" className="mt-4 inline-block text-accent">
          Create campaign
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl px-6 py-12">
      <Link to="/" className="text-sm text-muted hover:text-accent">
        ← Home
      </Link>
      <h1 className="display-text mt-4 text-3xl text-accent">Create Character</h1>
      <p className="mt-2 text-sm text-muted">Your avatar in a world that will not forget.</p>

      <form onSubmit={onSubmit} className="panel mt-6 space-y-4 rounded-xl p-5">
        <Field label="Name">
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={fieldClass}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Race">
            <input value={race} onChange={(e) => setRace(e.target.value)} className={fieldClass} />
          </Field>
          <Field label="Class">
            <input
              value={className}
              onChange={(e) => setClassName(e.target.value)}
              className={fieldClass}
            />
          </Field>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {ABILITIES.map((ability) => (
            <Field key={ability} label={ability.slice(0, 3).toUpperCase()}>
              <input
                type="number"
                min={3}
                max={20}
                value={stats[ability]}
                onChange={(e) =>
                  setStats((s) => ({ ...s, [ability]: Number(e.target.value) }))
                }
                className={fieldClass}
              />
            </Field>
          ))}
        </div>
        {error ? <ErrorState message={error} /> : null}
        <button
          type="submit"
          disabled={busy || !canSubmit}
          className="display-text rounded-lg border border-accent/50 bg-accent/15 px-4 py-2 text-accent hover:bg-accent/25 disabled:opacity-50"
        >
          {busy ? "Creating…" : "Enter the World"}
        </button>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="text-muted">{label}</span>
      {children}
    </label>
  );
}
