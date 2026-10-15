import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    # Fresh in-memory SQLite per test, so tests never touch a real database
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def shorten(client, url="https://example.com/some/long/path", **extra):
    return client.post("/shorten", json={"url": url, **extra})


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_shorten_returns_code_and_short_url(client):
    r = shorten(client)
    assert r.status_code == 201
    body = r.json()
    assert len(body["code"]) == 6
    assert body["short_url"].endswith("/" + body["code"])
    assert body["original_url"] == "https://example.com/some/long/path"


def test_invalid_url_rejected(client):
    assert shorten(client, url="not-a-url").status_code == 422


def test_redirect_to_original(client):
    code = shorten(client).json()["code"]
    r = client.get(f"/{code}", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "https://example.com/some/long/path"


def test_unknown_code_returns_404(client):
    assert client.get("/doesnotexist", follow_redirects=False).status_code == 404
    assert client.get("/stats/doesnotexist").status_code == 404


def test_custom_code(client):
    r = shorten(client, custom_code="my-link")
    assert r.status_code == 201 and r.json()["code"] == "my-link"
    assert client.get("/my-link", follow_redirects=False).status_code == 307


def test_duplicate_custom_code_conflict(client):
    shorten(client, custom_code="taken")
    r = shorten(client, url="https://other.com", custom_code="taken")
    assert r.status_code == 409


def test_reserved_custom_code_rejected(client):
    assert shorten(client, custom_code="stats").status_code == 409


def test_invalid_custom_code_format(client):
    assert shorten(client, custom_code="a b").status_code == 422
    assert shorten(client, custom_code="ab").status_code == 422


def test_generated_code_skips_reserved_routes(client, monkeypatch):
    chars = iter(["h", "e", "a", "l", "t", "h", "a", "b", "c", "1", "2", "3"])
    monkeypatch.setattr("app.crud.secrets.choice", lambda _alphabet: next(chars))

    r = shorten(client)
    assert r.status_code == 201
    assert r.json()["code"] == "abc123"


def test_click_stats_tracking(client):
    code = shorten(client).json()["code"]
    s0 = client.get(f"/stats/{code}").json()
    assert s0["total_clicks"] == 0 and s0["last_clicked_at"] is None

    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)

    s1 = client.get(f"/stats/{code}").json()
    assert s1["total_clicks"] == 3
    assert s1["last_clicked_at"] is not None
    assert s1["original_url"] == "https://example.com/some/long/path"
