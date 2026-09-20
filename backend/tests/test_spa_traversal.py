import pytest
from fastapi.testclient import TestClient

import app.main as main


@pytest.fixture()
def dist(tmp_path, monkeypatch):
    if not any(getattr(r, "path", "") == "/{full_path:path}" for r in main.app.routes):
        pytest.skip("frontend/dist not built; SPA fallback route not registered")
    root = tmp_path / "dist"
    root.mkdir()
    (root / "index.html").write_text("<html>spa</html>")
    (root / "robots.txt").write_text("ok")
    (tmp_path / ".env").write_text("GROQ_API_KEY=leaked")
    monkeypatch.setattr(main, "_FRONTEND", root.resolve())
    return root


@pytest.mark.parametrize(
    "path",
    [
        "/..%2F.env",
        "/%2e%2e/.env",
        "/..%5C.env",
        "/x/..%2F..%2F.env",
    ],
)
def test_spa_fallback_blocks_path_traversal(dist, path):
    r = TestClient(main.app).get(path)
    assert "leaked" not in r.text
    assert "spa" in r.text


def test_spa_fallback_still_serves_dist_files(dist):
    assert TestClient(main.app).get("/robots.txt").text == "ok"
