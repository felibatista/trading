from __future__ import annotations

import os

from fastapi.testclient import TestClient

from api.app import create_app


def test_api_still_works_without_web_dist(monkeypatch):
    # Sin build del SPA, /api sigue respondiendo y no se monta estático.
    monkeypatch.setenv("AMERICO_RUN_FLEET", "0")
    monkeypatch.setenv("AMERICO_WEB_DIST", "no_existe_dir")
    client = TestClient(create_app())
    assert client.get("/api/health").json() == {"status": "ok"}


def test_spa_fallback_when_dist_exists(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>app</title>", encoding="utf-8")
    monkeypatch.setenv("AMERICO_RUN_FLEET", "0")
    monkeypatch.setenv("AMERICO_WEB_DIST", str(dist))
    client = TestClient(create_app())
    # ruta de cliente -> index.html
    r = client.get("/cualquier/ruta")
    assert r.status_code == 200 and "<title>app</title>" in r.text
    # /api sigue teniendo prioridad
    assert client.get("/api/health").json() == {"status": "ok"}
