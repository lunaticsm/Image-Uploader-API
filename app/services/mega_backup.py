from __future__ import annotations

import asyncio
import logging
import time
import types
from typing import Any

logger = logging.getLogger("image_uploader")

# Global rate limiting to prevent too many operations in a short period
_last_operation_time = 0
_MIN_OPERATION_INTERVAL = 2  # Minimum 2 seconds between operations


def _enforce_rate_limit():
    """Enforce minimum interval between operations to prevent account blocks."""
    global _last_operation_time
    current_time = time.time()
    time_since_last = current_time - _last_operation_time

    if time_since_last < _MIN_OPERATION_INTERVAL:
        sleep_time = _MIN_OPERATION_INTERVAL - time_since_last
        time.sleep(sleep_time)

    _last_operation_time = time.time()

# mega.py expects asyncio.coroutine to exist; Python >=3.11 removed it.
if not hasattr(asyncio, "coroutine"):  # pragma: no cover - only runs on modern Python
    asyncio.coroutine = types.coroutine


class MegaBackup:
    """A thin wrapper around the mega.py client used to upload/delete backups."""

    def __init__(self, email: str, password: str, folder_name: str | None = None):
        if not email or not password:
            raise ValueError("MEGA_EMAIL and MEGA_PASSWORD must be set when MEGA backup is enabled")

        try:
            from mega import Mega  # Lazy import so the dependency is optional when backups are disabled
        except ImportError as exc:  # pragma: no cover - dependency missing
            raise RuntimeError(
                "mega.py is not installed. Install it via 'pip install mega.py' to enable MEGA backups."
            ) from exc

        self._mega = Mega()
        self._email = email
        self._password = password
        self._last_login_time = 0
        self._login()

        self._folder_name = folder_name.strip() if folder_name else None
        self._target_folder = None
        if self._folder_name:
            node = self._ensure_folder(self._folder_name)
            self._target_folder = node.get("h")

    def _login(self):
        """Login to MEGA and update the client."""
        try:
            self._client = self._mega.login(self._email, self._password)
            self._last_login_time = time.time()
        except Exception as exc:  # pragma: no cover - network/service failures
            raise RuntimeError("Failed to authenticate with MEGA. Check credentials.") from exc

    def _validate_session(self):
        """Validate the current session and re-login if needed."""
        # Check if we should refresh the session (if it's been more than 1 hour since last login)
        if time.time() - self._last_login_time > 3600:  # 1 hour
            logger.info("Refreshing MEGA session due to age")
            self._login()
            return

        # Test the connection by trying to get file list
        try:
            self._client.get_files()
        except Exception as e:
            # If it's an EBLOCKED error, we don't want to keep trying to re-authenticate as that might make it worse
            if "EBLOCKED" in str(e) or "User blocked" in str(e):
                logger.error("MEGA account is blocked, cannot re-authenticate: %s", e)
                raise RuntimeError(f"MEGA account blocked: {e}") from e
            else:
                logger.warning("MEGA session validation failed (%s), re-authenticating", e)
                self._login()

    def upload_file(self, file_path: str, file_name: str):
        """Upload a file to MEGA and return (item_handle, share_link)."""
        _enforce_rate_limit()
        self._validate_session()
        return self._upload_with_retry(file_path, file_name, refresh_on_failure=True)

    def _upload_with_retry(self, file_path: str, file_name: str, refresh_on_failure: bool):
        self._validate_session()
        destination = self._target_folder
        try:
            uploaded = self._client.upload(file_path, dest=destination, dest_filename=file_name)
        except Exception as exc:  # pragma: no cover - network/service failures
            # Check if it's a session-related error
            if "EBLOCKED" in str(exc) or "User blocked" in str(exc):
                logger.error("MEGA account blocked error detected: %s", exc)
                raise RuntimeError(f"Failed to upload '{file_name}' to MEGA: {exc}") from exc
            elif refresh_on_failure and self._folder_name:
                logger.warning("MEGA upload failed (%s). Refreshing folder handle and retrying once.", exc)
                # Try re-validating the session first
                self._login()  # Force re-login
                refreshed = self._ensure_folder(self._folder_name)
                self._target_folder = refreshed.get("h")
                return self._upload_with_retry(file_path, file_name, refresh_on_failure=False)
            raise RuntimeError(f"Failed to upload '{file_name}' to MEGA: {exc}") from exc

        file_handle = self._extract_handle(uploaded)
        share_link = None
        try:
            share_link = self._client.get_link(uploaded)
        except Exception:
            logger.warning("Could not create MEGA share link for %s", file_name)

        return file_handle, share_link

    def delete_file(self, file_handle: str):
        """Delete a file stored in MEGA by its handle."""
        if not file_handle:
            return

        _enforce_rate_limit()
        self._validate_session()
        try:
            files = self._client.get_files()
        except Exception as e:
            # If it's a blocked account error, log it specifically
            if "EBLOCKED" in str(e) or "User blocked" in str(e):
                logger.error("MEGA file listing fetch failed due to account block: %s", e)
            logger.warning("Unable to fetch MEGA file listing while deleting %s", file_handle)
            return

        node = files.get(file_handle)
        if not node:
            return

        try:
            self._client.delete(node)
        except Exception as e:
            # If it's a blocked account error, log it specifically
            if "EBLOCKED" in str(e) or "User blocked" in str(e):
                logger.error("MEGA file deletion failed due to account block: %s", e)
            logger.warning("Failed to delete MEGA file %s", file_handle)

    def _ensure_folder(self, folder_name: str):
        _enforce_rate_limit()
        self._validate_session()
        existing = self._find_folder(folder_name)
        if existing:
            logger.info("Using existing MEGA folder '%s' for backups", folder_name)
            return existing

        logger.info("Creating MEGA folder '%s' for backups", folder_name)
        try:
            created = self._client.create_folder(folder_name)
            node = self._folder_from_create_result(created)
            if node:
                return node
        except Exception as exc:  # pragma: no cover - network/service failures
            # Check if it's a blocked account error
            if "EBLOCKED" in str(exc) or "User blocked" in str(exc):
                logger.error("MEGA folder creation failed due to account block: %s", exc)
                raise RuntimeError(f"Unable to create MEGA folder '{folder_name}': {exc}") from exc
            # Another process may have created the folder in the meantime; log and re-check.
            logger.warning("MEGA folder creation raised %s; rechecking existence.", exc)
            self._login()  # Force re-login if there was an error
            existing = self._find_folder(folder_name)
            if existing:
                return existing
            raise RuntimeError(f"Unable to create MEGA folder '{folder_name}'") from exc

        # After creation, fetch the folder so we have a consistent node reference.
        created = self._find_folder(folder_name)
        if created:
            return created
        raise RuntimeError(f"MEGA folder '{folder_name}' was created but could not be retrieved afterwards.")

    def _find_folder(self, folder_name: str):
        """Look for a folder by name in the MEGA filesystem."""
        self._validate_session()
        try:
            files = self._client.get_files()
        except Exception as e:
            # If it's a blocked account error, log it specifically
            if "EBLOCKED" in str(e) or "User blocked" in str(e):
                logger.error("MEGA folder lookup failed due to account block: %s", e)
            return None

        for handle, node in files.items():
            if not self._is_folder(node):
                continue

            attributes = node.get("a") or {}
            node_name = attributes.get("n")
            if node_name == folder_name:
                # Attach the handle to the node so callers can use it directly.
                node_with_handle = dict(node)
                node_with_handle["h"] = handle
                return node_with_handle
        return None

    @staticmethod
    def _is_folder(node: Any) -> bool:
        if not isinstance(node, dict):
            return False
        # mega.py represents folders with type 1
        node_type = node.get("t")
        return node_type == 1

    @staticmethod
    def _extract_handle(upload_response: Any) -> str:
        """
        mega.py upload responses can be nested; attempt to pull the handle from the response.
        """
        if isinstance(upload_response, dict):
            if "h" in upload_response:
                return upload_response["h"]
            if "f" in upload_response and isinstance(upload_response["f"], list):
                for candidate in upload_response["f"]:
                    if isinstance(candidate, dict) and "h" in candidate:
                        return candidate["h"]
        if isinstance(upload_response, list) and upload_response:
            first = upload_response[0]
            if isinstance(first, dict) and "h" in first:
                return first["h"]

        raise RuntimeError("Could not determine MEGA file handle after upload")

    @staticmethod
    def _folder_from_create_result(create_response: Any):
        """Extract the folder node from mega.py create_folder response."""
        node = None
        if isinstance(create_response, dict):
            if "f" in create_response and isinstance(create_response["f"], list):
                for candidate in create_response["f"]:
                    if MegaBackup._is_folder(candidate):
                        node = candidate
                        break
            elif MegaBackup._is_folder(create_response):
                node = create_response
        elif isinstance(create_response, list):
            for candidate in create_response:
                if MegaBackup._is_folder(candidate):
                    node = candidate
                    break

        if node is None:
            return None

        # Ensure the node has a handle so delete operations can reference it later.
        if "h" not in node:
            try:
                handle = MegaBackup._extract_handle(create_response)
            except RuntimeError:
                handle = None
            if handle:
                node = dict(node)
                node["h"] = handle
        return node
