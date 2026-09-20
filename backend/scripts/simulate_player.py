"""Run: python -m scripts.simulate_player  (from backend, with DATABASE_URL)."""

from app.database.session import SessionLocal
from app.game.simulation import simulate_session


def main() -> None:
    db = SessionLocal()
    try:
        from tests.test_game_core import _seed

        _, campaign, _, character = _seed(db)
        report = simulate_session(db, campaign.id, character.id)
        print("applied", len(report.applied), "rejected", len(report.rejected))
        if report.errors:
            print("ERRORS", report.errors)
            raise SystemExit(1)
        print("ok")
    finally:
        db.close()


if __name__ == "__main__":
    main()
