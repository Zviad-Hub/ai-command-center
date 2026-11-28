"""Controlled local workspace operations for the Technical Department.

This module is deliberately not exposed to model prompts as an autonomous tool.
A human-operated controller must call these functions and supply the approval
token for writes. Reads and tests are limited to an explicitly configured
workspace; writes require an expected content hash and create an external backup.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class WorkbenchError(RuntimeError):
    """A safe, user-displayable workbench validation or execution error."""


TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".csv"}
WRITE_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"}
MAX_READ_BYTES = 256_000
MAX_WRITE_BYTES = 512_000
MAX_LIST_FILES = 500
MAX_TEST_OUTPUT = 20_000
DEFAULT_TEST_TIMEOUT = 180
SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", "secrets.json",
    "credentials.json", "service-account.json", "id_rsa", "id_ed25519",
}
DENIED_PARTS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode"}
MODULE_RE = re.compile(r"^tests\.test_[A-Za-z0-9_]+$")


def _workspace_root(root: str | os.PathLike | None = None) -> Path:
    configured = root if root is not None else os.getenv("AI_COMMAND_CENTER_WORKSPACE", "")
    if not str(configured or "").strip():
        raise WorkbenchError("Workspace is not configured. Set AI_COMMAND_CENTER_WORKSPACE to the project directory.")
    candidate = Path(os.path.expandvars(os.path.expanduser(str(configured)))).resolve(strict=True)
    if not candidate.is_dir():
        raise WorkbenchError("Configured workspace is not a directory.")
    return candidate


def _safe_path(root: Path, relative_path: str, *, for_write: bool = False) -> Path:
    raw = str(relative_path or "").strip()
    if not raw or "\x00" in raw:
        raise WorkbenchError("A relative workspace path is required.")
    candidate = Path(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise WorkbenchError("Absolute paths and path traversal are not allowed.")
    if any(part.casefold() in DENIED_PARTS or part.startswith(".") for part in candidate.parts):
        raise WorkbenchError("Access to hidden, environment, or dependency directories is blocked.")
    if candidate.name.casefold() in SENSITIVE_NAMES or candidate.name.casefold().startswith(".env"):
        raise WorkbenchError("Sensitive configuration and credential files are blocked.")
    if candidate.suffix.casefold() not in (WRITE_SUFFIXES if for_write else TEXT_SUFFIXES):
        raise WorkbenchError("This file type is not allowed by the workbench.")
    target = root.joinpath(candidate)
    # Reject symlinks in every existing path component, including the leaf.
    current = root
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise WorkbenchError("Symlink access is blocked.")
    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise WorkbenchError("The requested path escapes the configured workspace.")
    return target


def list_files(root: str | os.PathLike | None = None, *, limit: int = 100) -> dict:
    """List safe text/source files without reading their contents."""
    workspace = _workspace_root(root)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_LIST_FILES:
        raise WorkbenchError(f"limit must be between 1 and {MAX_LIST_FILES}.")
    found = []
    for directory, dirs, files in os.walk(workspace, followlinks=False):
        dirs[:] = sorted(
            name for name in dirs
            if name.casefold() not in DENIED_PARTS and not name.startswith(".")
            and not (Path(directory) / name).is_symlink()
        )
        for name in sorted(files):
            relative = (Path(directory) / name).relative_to(workspace).as_posix()
            try:
                path = _safe_path(workspace, relative)
            except WorkbenchError:
                continue
            if path.suffix.casefold() in TEXT_SUFFIXES and path.is_file():
                found.append(relative)
                if len(found) >= limit:
                    return {"workspace": str(workspace), "files": found, "truncated": True}
    return {"workspace": str(workspace), "files": found, "truncated": False}


def read_file(relative_path: str, root: str | os.PathLike | None = None) -> dict:
    """Read one bounded UTF-8 source/document file from the configured workspace."""
    workspace = _workspace_root(root)
    path = _safe_path(workspace, relative_path)
    try:
        size = path.stat().st_size
        if not path.is_file() or size > MAX_READ_BYTES:
            raise WorkbenchError(f"File is missing, not regular, or exceeds {MAX_READ_BYTES} bytes.")
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise WorkbenchError("Only UTF-8 text files can be inspected.") from error
    except OSError as error:
        raise WorkbenchError("The requested workspace file could not be read.") from error
    return {
        "path": Path(relative_path).as_posix(),
        "content": content,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "size_bytes": size,
    }


def _backup_directory(workspace: Path) -> Path:
    digest = hashlib.sha256(str(workspace).encode("utf-8")).hexdigest()[:16]
    base = Path(tempfile.gettempdir()) / "ai-command-center-workbench-backups" / digest
    base.mkdir(parents=True, exist_ok=True)
    return base


def _record_audit(backup_dir: Path, event: dict) -> None:
    audit_path = backup_dir / "audit.jsonl"
    with audit_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def write_file(
    relative_path: str,
    content: str,
    *,
    expected_sha256: str,
    approval_token: str,
    root: str | os.PathLike | None = None,
) -> dict:
    """Replace an existing source file after explicit approval and optimistic locking."""
    workspace = _workspace_root(root)
    path = _safe_path(workspace, relative_path, for_write=True)
    configured_token = os.getenv("AI_TECHNICAL_APPROVAL_TOKEN", "")
    if not configured_token or not approval_token or not hmac.compare_digest(
        str(approval_token), configured_token
    ):
        raise WorkbenchError("A valid CEO approval token is required for file changes.")
    if not isinstance(content, str):
        raise WorkbenchError("File content must be UTF-8 text.")
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_WRITE_BYTES:
        raise WorkbenchError(f"New content exceeds {MAX_WRITE_BYTES} bytes.")
    if not path.is_file() or path.is_symlink():
        raise WorkbenchError("Only existing regular files can be updated.")
    current = path.read_bytes()
    current_hash = hashlib.sha256(current).hexdigest()
    if not isinstance(expected_sha256, str) or not hmac.compare_digest(current_hash, expected_sha256):
        raise WorkbenchError("The file changed since it was reviewed; fetch it again before retrying.")
    backup_dir = _backup_directory(workspace)
    backup_name = Path(relative_path).as_posix().replace("/", "__")
    backup_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"{backup_stamp}__{backup_name}.bak"
    shutil.copy2(path, backup_path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=str(path.parent), prefix=f".{path.name}.",
            suffix=".tmp", delete=False
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_path, path.stat().st_mode)
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as error:
        raise WorkbenchError("The approved file update failed; the original backup was preserved.") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    new_hash = hashlib.sha256(encoded).hexdigest()
    try:
        _record_audit(backup_dir, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "file_update",
            "path": Path(relative_path).as_posix(),
            "before_sha256": current_hash,
            "after_sha256": new_hash,
            "backup": backup_path.name,
        })
        audit_recorded = True
    except OSError:
        audit_recorded = False
    return {
        "status": "UPDATED",
        "path": Path(relative_path).as_posix(),
        "before_sha256": current_hash,
        "after_sha256": new_hash,
        "backup_created": True,
        "audit_recorded": audit_recorded,
        "execution_authorized": True,
    }


def run_tests(
    *,
    test_module: str | None = None,
    timeout: int = DEFAULT_TEST_TIMEOUT,
    root: str | os.PathLike | None = None,
) -> dict:
    """Run only the full unittest suite or one tests.* module; never invoke a shell."""
    workspace = _workspace_root(root)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 600:
        raise WorkbenchError("Test timeout must be between 1 and 600 seconds.")
    if test_module is None:
        args = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
        target = "tests (full unittest discovery)"
    else:
        if not isinstance(test_module, str) or not MODULE_RE.fullmatch(test_module):
            raise WorkbenchError("Only a tests.test_<name> unittest module can be selected.")
        filename = test_module.rsplit(".", 1)[1] + ".py"
        args = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", filename, "-v"]
        target = test_module
    if not (workspace / "tests").is_dir():
        raise WorkbenchError("The configured workspace has no tests directory.")
    # Do not pass provider credentials, API tokens, or the approval token to test processes.
    safe_env = {}
    for name in ("PATH", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "TMP", "TEMP", "TMPDIR"):
        if name in os.environ:
            safe_env[name] = os.environ[name]
    safe_env["PYTHONIOENCODING"] = "utf-8"
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            args, cwd=str(workspace), env=safe_env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, shell=False, close_fds=True, check=False,
        )
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "target": target,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-MAX_TEST_OUTPUT:],
            "stderr": completed.stderr[-MAX_TEST_OUTPUT:],
            "tests_executed": True,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode("utf-8", "replace") if isinstance(error.stdout, bytes) else str(error.stdout or "")
        stderr = error.stderr.decode("utf-8", "replace") if isinstance(error.stderr, bytes) else str(error.stderr or "")
        return {
            "status": "TIMEOUT",
            "target": target,
            "returncode": None,
            "stdout": stdout[-MAX_TEST_OUTPUT:],
            "stderr": stderr[-MAX_TEST_OUTPUT:],
            "tests_executed": True,
            "timed_out": True,
        }
    except OSError as error:
        raise WorkbenchError("The approved unittest process could not be started.") from error
