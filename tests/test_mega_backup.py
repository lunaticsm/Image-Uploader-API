import importlib
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


def _prepare_client_with_mega(tmp_path, monkeypatch, *, enable_mega="false"):
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ENABLE_CLEANER", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "5")
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024))
    monkeypatch.setenv("CACHE_MAX_AGE_SECONDS", "120")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin")
    monkeypatch.setenv("ADMIN_LOCK_STEP_SECONDS", "60")
    monkeypatch.setenv("MEGA_BACKUP_ENABLED", enable_mega)
    monkeypatch.setenv("MEGA_EMAIL", "test@example.com")
    monkeypatch.setenv("MEGA_PASSWORD", "dummy-password")
    monkeypatch.setenv("MEGA_FOLDER_NAME", "")

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
        try:
            module = importlib.import_module(module_name)
            importlib.reload(module)
        except Exception as e:
            print(f"Could not reload module {module_name}: {e}")

    main = sys.modules["app.main"]

    test_client = TestClient(main.app)
    test_client.upload_dir = tmp_path  # type: ignore[attr-defined]
    return test_client


@pytest.fixture
def client_with_backup_disabled(tmp_path, monkeypatch):
    test_client = _prepare_client_with_mega(tmp_path, monkeypatch, enable_mega="false")
    with test_client as c:
        yield c


def test_regular_upload_with_backup_disabled(client_with_backup_disabled):
    """Test that regular upload works when remote backup is disabled"""
    client = client_with_backup_disabled

    response = client.post("/upload", files={"file": ("test.txt", b"Test content", "text/plain")})

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "url" in data
    assert "size" in data
    assert "type" in data
    assert data["size"] == 12  # Length of "Test content"


def test_file_model_has_backup_fields():
    """Test that the File model has the expected backup fields"""
    from app.models import File
    
    # Create a file instance and check it has the expected fields
    file_instance = File(
        id="test123",
        original_name="test.txt",
        stored_name="test123.txt",
        content_type="text/plain",
        size_bytes=12
    )
    
    # Check that the backup-related fields exist and have correct defaults
    assert hasattr(file_instance, 'backed_up')
    assert file_instance.backed_up == False
    assert hasattr(file_instance, 'backup_id')
    assert file_instance.backup_id is None
    assert hasattr(file_instance, 'backup_time')
    assert file_instance.backup_time is None
