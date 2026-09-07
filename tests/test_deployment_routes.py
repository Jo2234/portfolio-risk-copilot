"""Exercise the same entrypoint and public routes used by Vercel FastAPI."""

import importlib
import json
from pathlib import Path
import tomllib

from fastapi.testclient import TestClient
import pytest


ROOT = Path(__file__).resolve().parents[1]


def deployment_client():
    config = json.loads((ROOT / "vercel.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    module, attribute = project["tool"]["vercel"]["entrypoint"].split(":")
    app = getattr(importlib.import_module(module), attribute)
    return TestClient(app), config


def routed_path(path, config):
    # Apply the former edge rewrites to expose paths that the framework cannot serve.
    for rule in config.get("rewrites", []):
        if rule["source"] == path:
            return rule["destination"]
        if rule["source"].endswith("/:path*") and path.startswith(rule["source"][:-7] + "/"):
            return rule["destination"]
    return path


def test_deployment_homepage_is_available_outside_repository_cwd(tmp_path, monkeypatch):
    client, config = deployment_client()
    monkeypatch.chdir(tmp_path)
    response = client.get(routed_path("/", config))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Portfolio Risk Copilot</title>" in response.text
    assert "fetch('/analyze'" in response.text


@pytest.mark.parametrize("path", ["/health", "/api/health"])
def test_deployment_health_routes(path):
    client, config = deployment_client()
    response = client.get(routed_path(path, config))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/analyze", "/api/analyze"])
def test_deployment_analysis_routes_use_inline_data(path):
    client, config = deployment_client()
    response = client.post(routed_path(path, config), json={
        "holdings": [{"ticker": "AAA", "weight": 1.0}],
        "price_history": {"AAA": [100, 50, 55]},
    })
    assert response.status_code == 200
    assert response.json()["metrics"]["max_drawdown"] == -0.5
    assert response.json()["data_source"]["type"] == "inline"
