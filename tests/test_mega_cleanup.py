import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.db import get_session
from app.models import File as FileModel


def _prepare_client_for_cleanup_test(tmp_path, monkeypatch, *, enable_backup="true"):
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ENABLE_CLEANER", "false")  # Disable automatic cleaner for manual testing
    monkeypatch.setenv("DELETE_AFTER_HOURS", "0")  # Set to 0 for immediate deletion in tests
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "5")
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024))
    monkeypatch.setenv("CACHE_MAX_AGE_SECONDS", "120")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin")
    monkeypatch.setenv("ADMIN_LOCK_STEP_SECONDS", "60")
    monkeypatch.setenv("MEGA_BACKUP_ENABLED", enable_backup)
    monkeypatch.setenv("MEGA_EMAIL", "test@example.com")
    monkeypatch.setenv("MEGA_PASSWORD", "dummy-password")
    monkeypatch.setenv("MEGA_FOLDER_NAME", "")

    class _StubMegaBackup:
        def __init__(self, *args, **kwargs):
            pass

        def upload_file(self, *args, **kwargs):
            return ("stub-handle", "https://mega.nz/file/stub")

        def delete_file(self, *args, **kwargs):
            return None

    monkeypatch.setattr("app.services.mega_backup.MegaBackup", _StubMegaBackup, raising=False)

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
def client_with_backup_enabled(tmp_path, monkeypatch):
    test_client = _prepare_client_for_cleanup_test(tmp_path, monkeypatch, enable_backup="true")
    with test_client as c:
        yield c


def test_cleanup_respects_backup_status(client_with_backup_enabled):
    """Cleanup should only remove files that are marked as backed up when remote backup is enabled."""
    client = client_with_backup_enabled
    
    # Create an expired file in the database (set creation time to be in the past)
    from datetime import datetime, timedelta
    from app.models import File as FileModel
    from app.db import get_session
    import os
    
    # Upload a test file 
    response = client.post("/upload", files={"file": ("test.txt", b"Test content", "text/plain")})
    assert response.status_code == 200
    
    # Get the file ID from the response
    response_data = response.json()
    file_id = response_data['id']
    stored_name = response_data['url'].lstrip('/')
    
    # Get the session and verify the file exists in the database
    session_gen = get_session()
    session = next(session_gen)
    try:
        file_record = session.get(FileModel, file_id)
        assert file_record is not None
        assert file_record.original_name == "test.txt"
        # Initially, backed_up should be False
        assert file_record.backed_up == False
        assert file_record.backup_id is None
    finally:
        session.close()
        try:
            next(session_gen)
        except StopIteration:
            pass  # Generator exhausted, which is expected

    # Simulate the backup process by setting backed_up to True and backup_id
    session_gen = get_session()
    session = next(session_gen)
    try:
        file_record = session.get(FileModel, file_id)
        if file_record:
            file_record.backed_up = True
            file_record.backup_id = "test_mega_file_id"
            session.add(file_record)
            session.commit()
    finally:
        session.close()
        try:
            next(session_gen)
        except StopIteration:
            pass  # Generator exhausted, which is expected
    
    # Now run the cleanup process directly
    from app.storage import delete_expired_files
    from app.db import engine
    deleted_count = delete_expired_files(engine)

    # Check that the file was deleted since it was backed up
    session_gen = get_session()
    session = next(session_gen)
    try:
        file_record = session.get(FileModel, file_id)
        # The record should be deleted now since it was backed up
        assert file_record is None
    finally:
        session.close()
        try:
            next(session_gen)
        except StopIteration:
            pass  # Generator exhausted, which is expected
        
    # Verify the file was also removed from disk
    file_path = client.upload_dir / stored_name  # type: ignore[attr-defined]
    assert not file_path.exists(), f"File {file_path} still exists after cleanup"


def test_cleanup_does_not_remove_unbacked_file_with_backup_enabled(client_with_backup_enabled):
    """Cleanup should not remove files that haven't been backed up even when remote backup is enabled."""
    client = client_with_backup_enabled
    
    # Upload a test file 
    response = client.post("/upload", files={"file": ("test2.txt", b"Test content 2", "text/plain")})
    assert response.status_code == 200
    
    # Get the file ID from the response
    response_data = response.json()
    file_id = response_data['id']
    stored_name = response_data['url'].lstrip('/')
    
    # Verify the file exists in the database and backed_up is False
    session_gen = get_session()
    session = next(session_gen)
    try:
        file_record = session.get(FileModel, file_id)
        assert file_record is not None
        assert file_record.original_name == "test2.txt"
        assert file_record.backed_up == False  # Should still be False
        assert file_record.backup_id is None
    finally:
        session.close()
        try:
            next(session_gen)
        except StopIteration:
            pass  # Generator exhausted, which is expected
        
    # Run the cleanup process directly - this should NOT delete the file since it's not backed up
    from app.storage import delete_expired_files
    from app.db import engine
    deleted_count = delete_expired_files(engine)
    
    # Since the file wasn't backed up, it should not be deleted
    assert deleted_count == 0
    
    # Check that the file is still in the database
    session_gen = get_session()
    session = next(session_gen)
    try:
        file_record = session.get(FileModel, file_id)
        assert file_record is not None
        assert file_record.original_name == "test2.txt"
    finally:
        session.close()
        try:
            next(session_gen)
        except StopIteration:
            pass  # Generator exhausted, which is expected
        
    # Check the file should still exist on disk
    file_path = client.upload_dir / stored_name  # type: ignore[attr-defined]
    assert file_path.exists(), f"File {file_path} was deleted despite not being backed up"
