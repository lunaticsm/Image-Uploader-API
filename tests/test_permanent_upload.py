import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _prepare_client_with_api_key(tmp_path, monkeypatch, *, rate_limit="5", max_size=str(10 * 1024 * 1024), cache_age="120", lock_step="60", api_key="test-api-key"):
    project_root = Path(__file__).resolve().parents[2]  # Go up one more level
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
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin")
    monkeypatch.setenv("ADMIN_LOCK_STEP_SECONDS", lock_step)
    monkeypatch.setenv("API_KEY", api_key)  # Set the API key

    # Reload modules so configuration changes take effect cleanly.
    module_order = [
        "app.config",
        "app.core.metrics",
        "app.core.rate_limit",
        "app.db",
        "app.storage",
        "app.cleaner",
        "app.services.stats",
        "app.core.templates",
        "app.core.exceptions",
        "app.api.routes",
        "app.main",
    ]

    for module_name in module_order:
        module = importlib.import_module(module_name)
        importlib.reload(module)

    main = sys.modules["app.main"]

    test_client = TestClient(main.app)
    test_client.upload_dir = tmp_path  # type: ignore[attr-defined]
    return test_client


@pytest.fixture
def client_with_api_key(tmp_path, monkeypatch):
    test_client = _prepare_client_with_api_key(tmp_path, monkeypatch)
    with test_client as c:
        yield c


def test_permanent_upload_with_api_key(client_with_api_key):
    """Test that permanent upload works with valid API key"""
    client = client_with_api_key

    # Test the API key authentication
    response = client.post(
        "/upload-permanent",
        files={"file": ("test.txt", b"Test content for permanent upload", "text/plain")},
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "url" in data
    assert "size" in data
    assert "type" in data
    assert "permanent" in data
    assert data["permanent"] is True


def test_permanent_upload_without_api_key(client_with_api_key):
    """Test that permanent upload fails without API key"""
    client = client_with_api_key

    response = client.post("/upload-permanent", files={"file": ("test.txt", b"test", "text/plain")})
    
    assert response.status_code == 401
    data = response.json()
    assert "Invalid or missing API key" in data["detail"]


def test_permanent_upload_with_invalid_api_key(client_with_api_key):
    """Test that permanent upload fails with invalid API key"""
    client = client_with_api_key

    response = client.post(
        "/upload-permanent",
        files={"file": ("test.txt", b"test", "text/plain")},
        headers={"X-API-Key": "invalid-api-key"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "Invalid or missing API key" in data["detail"]


def test_permanent_upload_api_key_from_query_param(client_with_api_key):
    """Test that permanent upload works with API key from query parameter"""
    client = client_with_api_key

    response = client.post(
        "/upload-permanent?api_key=test-api-key",
        files={"file": ("test.txt", b"Test content for permanent upload", "text/plain")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "url" in data
    assert "size" in data
    assert "type" in data
    assert "permanent" in data
    assert data["permanent"] is True


def test_regular_upload_not_permanent(client_with_api_key):
    """Test that regular upload still works and doesn't create permanent files"""
    client = client_with_api_key

    response = client.post("/upload", files={"file": ("test.txt", b"Test content for regular upload", "text/plain")})
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "url" in data
    assert "size" in data
    assert "type" in data
    
    # Regular uploads should not have a permanent field in the response
    assert "permanent" not in data