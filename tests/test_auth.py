import sys
import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
import auth  # noqa: E402
import main  # noqa: E402

PW = "correct-horse-1"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, "DB_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(auth, "_engine", None)
    yield TestClient(main.app)
    if auth._engine is not None:
        auth._engine.dispose()


def signup(client, name="ayesha", pw=PW):
    return client.post("/auth/register", json={"username": name, "password": pw})


def headers(client, name="ayesha"):
    signup(client, name)
    r = client.post("/auth/login", json={"username": name, "password": PW})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_register_ok(client):
    r = signup(client, "Ayesha")
    assert r.status_code == 201
    assert r.json() == {"username": "ayesha"}


def test_duplicate_username_409(client):
    signup(client, "ayesha")
    assert signup(client, "AYESHA").status_code == 409


def test_short_password_422(client):
    assert signup(client, "ayesha", "short").status_code == 422


def test_wrong_password_401(client):
    signup(client)
    r = client.post("/auth/login", json={"username": "ayesha", "password": "nope-nope-1"})
    assert r.status_code == 401


def test_unknown_user_401(client):
    r = client.post("/auth/login", json={"username": "ghost", "password": PW})
    assert r.status_code == 401


def test_bookmarks_need_login(client):
    assert client.get("/bookmarks").status_code in (401, 403)


def test_garbage_token_401(client):
    r = client.get("/bookmarks", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401


def test_expired_token_401(client):
    old = jwt.encode({"sub": "1", "exp": int(time.time()) - 10}, auth.SECRET, algorithm="HS256")
    r = client.get("/bookmarks", headers={"Authorization": "Bearer " + old})
    assert r.status_code == 401


def test_add_and_list_bookmark(client):
    h = headers(client)
    body = {"country_code": "pak", "region": "Punjab"}
    assert client.post("/bookmarks", json=body, headers=h).status_code == 201
    client.post("/bookmarks", json=body, headers=h)
    r = client.get("/bookmarks", headers=h)
    assert r.json() == [{"country_code": "PAK", "region": "Punjab"}]


def test_users_are_isolated(client):
    a = headers(client, "alice")
    b = headers(client, "bobby")
    client.post("/bookmarks", json={"country_code": "PAK", "region": "Sindh"}, headers=a)
    assert client.get("/bookmarks", headers=b).json() == []


def test_delete_bookmark(client):
    h = headers(client)
    client.post("/bookmarks", json={"country_code": "PAK", "region": "Punjab"}, headers=h)
    assert client.delete("/bookmarks/PAK/Punjab", headers=h).status_code == 200
    assert client.get("/bookmarks", headers=h).json() == []


def test_delete_missing_404(client):
    h = headers(client)
    assert client.delete("/bookmarks/PAK/Nowhere", headers=h).status_code == 404


def test_password_is_hashed(client):
    signup(client)
    with auth.db().connect() as conn:
        stored = conn.execute(text("SELECT pw_hash FROM users")).scalar()
    assert PW not in stored
    assert ":" in stored
