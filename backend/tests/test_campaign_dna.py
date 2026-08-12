"""Campaign DNA generation, merge, persistence, and DM context injection."""

from __future__ import annotations

import random

from app.ai.context_builder import ContextBuilder
from app.game.campaign_dna import (
    DNA_VERSION,
    SINGLE_CATEGORIES,
    build_campaign_dna,
    format_dna_for_prompt,
    generate_random_dna,
    merge_user_description_into_dna,
)
from app.schemas.common import CampaignCreate
from app.schemas.state import CharacterState, GameState
from app.services.campaign import CampaignService
from tests.conftest import make_user


def test_generate_random_dna_has_all_categories_and_version():
    dna = generate_random_dna(random.Random(42))
    assert dna["version"] == DNA_VERSION
    for key, options in SINGLE_CATEGORIES.items():
        assert dna[key] in options
    assert isinstance(dna["special_motifs"], list) and len(dna["special_motifs"]) == 3
    assert isinstance(dna["recurring_visual_themes"], list) and len(dna["recurring_visual_themes"]) == 3


def test_random_dna_is_deterministic_with_seed():
    a = generate_random_dna(random.Random(7))
    b = generate_random_dna(random.Random(7))
    assert a == b
    c = generate_random_dna(random.Random(8))
    assert a != c


def test_user_description_overrides_conflicting_dna():
    base = generate_random_dna(random.Random(1))
    merged = merge_user_description_into_dna(
        base,
        "A gritty survival tale on frozen ice kingdoms with rare magic and mercenaries.",
        rng=random.Random(1),
    )
    assert merged["core_theme"] == "survival"
    assert merged["tone"] == "gritty"
    assert merged["world_flavor"] == "frozen kingdoms"
    assert merged["magic_style"] == "rare and mysterious"
    assert merged["hero_style"] == "mercenaries"
    # Unspecified categories keep random picks
    assert merged["npc_style"] == base["npc_style"]
    assert merged["version"] == DNA_VERSION


def test_empty_description_keeps_random_dna():
    base = generate_random_dna(random.Random(3))
    merged = merge_user_description_into_dna(base, "", rng=random.Random(3))
    assert merged == {**base, "version": DNA_VERSION}


def test_format_dna_for_prompt_priority_and_user_desc():
    dna = build_campaign_dna("glory and tournaments", rng=random.Random(2))
    block = format_dna_for_prompt(dna, "glory and tournaments")
    assert "USER CAMPAIGN DESCRIPTION" in block
    assert "glory and tournaments" in block
    assert "Campaign DNA" in block
    assert "core_theme:" in block
    assert "NOT a rigid script" in block or "constraint" in block.lower()


def test_campaign_create_persists_dna_once(db):
    user = make_user(db, username="dna_user")
    svc = CampaignService(db)
    campaign = svc.create(
        CampaignCreate(name="Ice March", description="Survival on frozen kingdoms."),
        owner_id=user.id,
    )
    ws = campaign.world_state or {}
    assert ws.get("user_campaign_description") == "Survival on frozen kingdoms."
    dna = ws.get("campaign_dna")
    assert isinstance(dna, dict)
    assert dna.get("version") == DNA_VERSION
    assert dna.get("core_theme") == "survival"
    assert dna.get("world_flavor") == "frozen kingdoms"
    first = dict(dna)

    # ensure_brief must not regenerate DNA
    again = svc.ensure_brief(campaign.id)
    assert (again.world_state or {}).get("campaign_dna") == first


def test_ensure_brief_backfills_missing_dna(db):
    user = make_user(db, username="dna_backfill")
    svc = CampaignService(db)
    campaign = svc.create(
        CampaignCreate(name="Blank", description=""),
        owner_id=user.id,
    )
    ws = dict(campaign.world_state or {})
    ws.pop("campaign_dna", None)
    campaign.world_state = ws
    db.commit()
    db.refresh(campaign)

    campaign = svc.ensure_brief(campaign.id)
    dna = (campaign.world_state or {}).get("campaign_dna")
    assert isinstance(dna, dict)
    assert dna.get("version") == DNA_VERSION
    assert "core_theme" in dna


def test_context_builder_includes_campaign_dna():
    from uuid import UUID

    dna = build_campaign_dna("epic war with dragons", rng=random.Random(11))
    state = GameState(
        campaign_id=UUID("00000000-0000-0000-0000-000000000001"),
        campaign_name="Warpath",
        current_time="dawn",
        weather="clear",
        world_state={
            "tone": "epic",
            "themes": ["war"],
            "user_campaign_description": "epic war with dragons",
            "campaign_dna": dna,
            "opening_delivered": True,
        },
        character=CharacterState(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Asha",
            race="Human",
            class_name="Fighter",
            level=1,
            hp=10,
            max_hp=10,
            ac=14,
            xp=0,
            gold=0,
            abilities={"strength": 12},
        ),
    )
    _, user_prompt = ContextBuilder().build(
        state=state,
        player_action="Look around",
        recent_events=[],
        memories=[],
    )
    assert "Campaign DNA" in user_prompt
    assert "USER CAMPAIGN DESCRIPTION" in user_prompt
    assert "epic war with dragons" in user_prompt
    assert "core_theme:" in user_prompt
    flags_line = [ln for ln in user_prompt.splitlines() if ln.startswith("World flags:")][0]
    assert "campaign_dna" not in flags_line
    assert "user_campaign_description" not in flags_line
