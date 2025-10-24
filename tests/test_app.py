import importlib
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ENABLE_CLEANER", "false")

    # Reload modules so configuration changes take effect cleanly.
    config = importlib.import_module("app.config")
    importlib.reload(config)
    storage = importlib.import_module("app.storage")
    importlib.reload(storage)
    cleaner = importlib.import_module("app.cleaner")
    importlib.reload(cleaner)
    main = importlib.import_module("app.main")
    importlib.reload(main)

    with TestClient(main.app) as test_client:
        test_client.upload_dir = tmp_path  # type: ignore[attr-defined]
        yield test_client
def test_upload_list_and_serve(client):
    response = client.post("/upload", files={"file": ("hello.txt", b"hi", "text/plain")})
    assert response.status_code == 200
    file_id = response.json()["id"]
    stored_url = response.json()["url"]

    list_response = client.get("/list")
    assert list_response.status_code == 200
    assert any(item["id"] == file_id for item in list_response.json())

    serve_response = client.get(stored_url)
    assert serve_response.status_code == 200
    assert serve_response.content == b"hi"


def test_directory_traversal_blocked(client):
    outside_file = client.upload_dir.parent / "top_secret.txt"  # type: ignore[attr-defined]
    outside_file.write_text("nope")

    response = client.get("/..%2f..%2f" + outside_file.name)
    assert response.status_code == 404


def test_homepage_and_api_docs(client):
    home_response = client.get("/", headers={"accept": "text/html"})
    assert home_response.status_code == 200
    assert "AlterBase CDN" in home_response.text

    api_response = client.get("/api-info", headers={"accept": "text/html"})
    assert api_response.status_code == 200
    assert "AlterBase CDN API" in api_response.text
