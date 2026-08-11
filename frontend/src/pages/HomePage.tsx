import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { campaignApi, characterApi } from "../api";
import type { Campaign, Character } from "../types/game";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import {
  randomCampaignDescription,
  randomCampaignName,
  randomCharacter,
} from "../lib/quickStart";

type Session = { campaignId: string; characterId: string };

function readSession(): Session | null {
  try {
    const raw = localStorage.getItem("dnd-session");
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Session;
    if (parsed.campaignId && parsed.characterId) return parsed;
  } catch {
    /* ignore */
  }
  return null;
}

export function HomePage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [charsByCampaign, setCharsByCampaign] = useState<Record<string, Character[]>>({});
  const [loading, setLoading] = useState(true);
  const [quickStarting, setQuickStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const last = readSession();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await campaignApi.list();
      setCampaigns(list);
      const map: Record<string, Character[]> = {};
      await Promise.all(
        list.map(async (c) => {
          map[c.id] = await characterApi.list(c.id);
        }),
      );
      setCharsByCampaign(map);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  async function quickStart() {
    setQuickStarting(true);
    setError(null);
    try {
      const campaignName = randomCampaignName();
      const campaign = await campaignApi.create({
        name: campaignName,
        description: randomCampaignDescription(campaignName),
      });
      const hero = randomCharacter();
      const character = await characterApi.create({
        campaign_id: campaign.id,
        name: hero.name,
        race: hero.race,
        class_name: hero.class_name,
      });
      localStorage.setItem(
        "dnd-session",
        JSON.stringify({ campaignId: campaign.id, characterId: character.id }),
      );
      navigate(`/game/${campaign.id}/${character.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quick start failed");
      setQuickStarting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col justify-center px-6 py-12">
      <p className="text-xs uppercase tracking-[0.35em] text-muted">Tabletop Reality Engine</p>
      <h1 className="display-text mt-3 text-5xl text-accent md:text-6xl">D&D Master</h1>
      <p className="story-text mt-4 max-w-2xl text-lg text-muted">
        A persistent campaign world. The engine keeps the rules. The dungeon master narrates the
        consequences.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={quickStarting}
          onClick={() => void quickStart()}
          className="display-text rounded-lg border border-accent/50 bg-accent/20 px-5 py-2.5 text-accent hover:bg-accent/30 disabled:opacity-50"
        >
          {quickStarting ? "Forging your tale…" : "Quick Start"}
        </button>
        <Link
          to="/campaigns/new"
          className="display-text rounded-lg border border-border px-5 py-2.5 text-text hover:bg-panel-2"
        >
          New Campaign
        </Link>
        {last ? (
          <button
            type="button"
            disabled={quickStarting}
            onClick={() => navigate(`/game/${last.campaignId}/${last.characterId}`)}
            className="display-text rounded-lg border border-border px-5 py-2.5 text-text hover:bg-panel-2 disabled:opacity-50"
          >
            Resume Last Session
          </button>
        ) : null}
      </div>
      {quickStarting ? (
        <p className="mt-3 text-sm text-muted">
          Random campaign, character, and opening scene — this can take a few seconds.
        </p>
      ) : null}

      <section className="panel mt-10 rounded-xl p-5">
        <h2 className="display-text text-lg text-accent">Your Campaigns</h2>
        {loading ? <LoadingState className="mt-4" /> : null}
        {error ? (
          <div className="mt-4">
            <ErrorState message={error} onRetry={() => void load()} />
          </div>
        ) : null}
        {!loading && !error && campaigns.length === 0 ? (
          <p className="mt-3 text-sm text-muted">No campaigns yet. Forge one to begin.</p>
        ) : null}
        <ul className="mt-4 space-y-3">
          {campaigns.map((c) => {
            const chars = charsByCampaign[c.id] ?? [];
            return (
              <li key={c.id} className="rounded border border-border bg-panel-2 px-3 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{c.name}</p>
                    <p className="text-xs text-muted">
                      {c.current_time} · {c.weather}
                    </p>
                  </div>
                  <Link
                    to={`/characters/new?campaignId=${c.id}`}
                    className="text-sm text-accent hover:underline"
                  >
                    New character
                  </Link>
                </div>
                {chars.length === 0 ? (
                  <p className="mt-2 text-xs text-muted">No characters yet.</p>
                ) : (
                  <ul className="mt-2 space-y-1">
                    {chars.map((ch) => (
                      <li key={ch.id} className="flex items-center justify-between text-sm">
                        <span>
                          {ch.name}{" "}
                          <span className="text-muted">
                            · L{ch.level} {ch.class_name}
                          </span>
                        </span>
                        <button
                          type="button"
                          className="text-accent hover:underline"
                          onClick={() => navigate(`/game/${c.id}/${ch.id}`)}
                        >
                          Continue
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
