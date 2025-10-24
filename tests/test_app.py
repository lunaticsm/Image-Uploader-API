import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _prepare_client(tmp_path, monkeypatch, *, rate_limit="5", max_size="1024", cache_age="120"):
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ENABLE_CLEANER", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", rate_limit)
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", max_size)
    monkeypatch.setenv("CACHE_MAX_AGE_SECONDS", cache_age)

    # Reload modules so configuration changes take effect cleanly.
    for module_name in ("app.config", "app.metrics", "app.rate_limit", "app.storage", "app.cleaner", "app.main"):
        module = importlib.import_module(module_name)
        importlib.reload(module)

    main = sys.modules["app.main"]

    test_client = TestClient(main.app)
    test_client.upload_dir = tmp_path  # type: ignore[attr-defined]
    return test_client


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_client = _prepare_client(tmp_path, monkeypatch)
    with test_client as c:
        yield c


def test_upload_list_serve_and_cache_headers(client):
    response = client.post("/upload", files={"file": ("hello.txt", b"hi", "text/plain")})
    assert response.status_code == 200
    stored_url = response.json()["url"]

    list_response = client.get("/list")
    assert list_response.status_code == 200
    assert any(item["id"] == response.json()["id"] for item in list_response.json())

    serve_response = client.get(stored_url)
    assert serve_response.status_code == 200
    assert serve_response.content == b"hi"
    assert serve_response.headers["Cache-Control"] == "public, max-age=120"


def test_directory_traversal_blocked(client):
    outside_file = client.upload_dir.parent / "top_secret.txt"  # type: ignore[attr-defined]
    outside_file.write_text("nope")

    response = client.get("/..%2f..%2f" + outside_file.name)
    assert response.status_code == 404


def test_homepage_and_api_docs_show_metrics(client):
    home_response = client.get("/", headers={"accept": "text/html"})
    assert home_response.status_code == 200
    assert "AlterBase CDN" in home_response.text
    assert "Uploads" in home_response.text

    api_response = client.get("/api-info", headers={"accept": "text/html"})
    assert api_response.status_code == 200
    assert "AlterBase CDN API" in api_response.text
    assert "10.0 MB" in api_response.text


def test_rejects_files_over_limit(tmp_path, monkeypatch):
    with _prepare_client(tmp_path, monkeypatch, max_size="1024") as c:
        big_file = b"x" * 2048
        response = c.post("/upload", files={"file": ("too-big.bin", big_file, "application/octet-stream")})
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]


def test_rate_limit_exceeded(tmp_path, monkeypatch):
    with _prepare_client(tmp_path, monkeypatch, rate_limit="2") as c:
        # First two requests succeed.
        assert c.get("/list").status_code == 200
        assert c.get("/list").status_code == 200
        # Third within window should be blocked.
        limited = c.get("/list")
        assert limited.status_code == 429
        assert "Rate limit exceeded" in limited.json()["detail"]
