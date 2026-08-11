import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { campaignApi } from "../api";
import { ErrorState } from "../components/common/ErrorState";


export function CreateCampaignPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const campaign = await campaignApi.create({ name, description });
      navigate(`/characters/new?campaignId=${campaign.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create campaign");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl px-6 py-12">
      <Link to="/" className="text-sm text-muted hover:text-accent">
        ← Home
      </Link>
      <h1 className="display-text mt-4 text-3xl text-accent">Create Campaign</h1>
      <p className="mt-2 text-sm text-muted">Name the world that will remember your choices.</p>

      <form onSubmit={onSubmit} className="panel mt-6 space-y-4 rounded-xl p-5">
        <label className="block text-sm">
          <span className="text-muted">Name</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-ink px-3 py-2 outline-none focus:ring-2 focus:ring-accent/40"
          />
        </label>
        <label className="block text-sm">
          <span className="text-muted">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="mt-1 w-full rounded border border-border bg-ink px-3 py-2 outline-none focus:ring-2 focus:ring-accent/40"
          />
        </label>
        {error ? <ErrorState message={error} /> : null}
        <button
          type="submit"
          disabled={busy}
          className="display-text rounded-lg border border-accent/50 bg-accent/15 px-4 py-2 text-accent hover:bg-accent/25 disabled:opacity-50"
        >
          {busy ? "Forging the world…" : "Create Campaign"}
        </button>
        {busy ? (
          <p className="text-xs text-muted">
            The dungeon master is setting the tone and opening scene…
          </p>
        ) : null}
      </form>
    </div>
  );
}
