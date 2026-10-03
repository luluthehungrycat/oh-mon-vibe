from __future__ import annotations

from datetime import UTC, datetime
from io import TextIOWrapper
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import stat
from typing import TYPE_CHECKING, Any, cast

from cachetools import TTLCache

from vibe.utils.paths import get_omv_home

if TYPE_CHECKING:
    from acp.connection import StreamEvent

ACP_LOG_DIR = get_omv_home() / "logs" / "acp"
ACP_LOG_FILE = ACP_LOG_DIR / "messages.jsonl"
MAX_LOG_SIZE_BYTES = 1_000_000
BACKUP_COUNT = 3
_ERROR_INSUFFICIENT_BUFFER = 122

ACP_LOGGING_ENABLED_KEY = "VIBE_ACP_LOGGING_ENABLED"

_session_cache: TTLCache[int | str, str] = TTLCache(maxsize=1000, ttl=3600)
_current_session: str | None = None
_logger: logging.Logger | None = None


def is_acp_logging_enabled() -> bool:
    return os.getenv(ACP_LOGGING_ENABLED_KEY, "").lower() in {"1", "true", "yes"}


def _windows_current_user_sid() -> str:
    import ctypes
    from ctypes import wintypes

    class _SidAndAttributes(ctypes.Structure):
        _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]

    class _TokenUser(ctypes.Structure):
        _fields_ = [("user", _SidAndAttributes)]

    win_dll = ctypes.__dict__["WinDLL"]
    win_error = ctypes.__dict__["WinError"]
    get_last_error = ctypes.__dict__["get_last_error"]
    kernel32 = win_dll("kernel32", use_last_error=True)
    advapi32 = win_dll("advapi32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.LocalFree.argtypes = [wintypes.HANDLE]
    kernel32.LocalFree.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    advapi32.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    ]
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
    ):
        raise win_error(get_last_error())

    sid_text = wintypes.LPWSTR()
    try:
        required = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
        if get_last_error() != _ERROR_INSUFFICIENT_BUFFER:
            raise win_error(get_last_error())
        token_buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token, 1, token_buffer, required, ctypes.byref(required)
        ):
            raise win_error(get_last_error())
        user = ctypes.cast(token_buffer, ctypes.POINTER(_TokenUser)).contents
        if not advapi32.ConvertSidToStringSidW(user.user.sid, ctypes.byref(sid_text)):
            raise win_error(get_last_error())
        if sid_text.value is None:
            raise OSError("Windows returned an empty current-user SID")
        return sid_text.value
    finally:
        if sid_text:
            kernel32.LocalFree(sid_text)
        kernel32.CloseHandle(token)


def _set_windows_owner_only(path: Path, *, directory: bool = False) -> None:
    """Replace a Windows DACL with a protected, current-user-only ACL."""
    import ctypes
    from ctypes import wintypes

    win_dll = ctypes.__dict__["WinDLL"]
    win_error = ctypes.__dict__["WinError"]
    get_last_error = ctypes.__dict__["get_last_error"]
    kernel32 = win_dll("kernel32", use_last_error=True)
    advapi32 = win_dll("advapi32", use_last_error=True)
    kernel32.LocalFree.argtypes = [wintypes.HANDLE]
    kernel32.LocalFree.restype = wintypes.HANDLE
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = (
        wintypes.BOOL
    )
    advapi32.GetSecurityDescriptorDacl.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.BOOL),
    ]
    advapi32.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    advapi32.SetNamedSecurityInfoW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    advapi32.SetNamedSecurityInfoW.restype = wintypes.DWORD
    sid = _windows_current_user_sid()
    inheritance = "OICI" if directory else ""
    sddl = f"D:P(A;{inheritance};FA;;;{sid})"
    descriptor = ctypes.c_void_p()
    descriptor_size = wintypes.DWORD()
    if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), ctypes.byref(descriptor_size)
    ):
        raise win_error(get_last_error())
    try:
        present = wintypes.BOOL()
        defaulted = wintypes.BOOL()
        dacl = ctypes.c_void_p()
        if not advapi32.GetSecurityDescriptorDacl(
            descriptor,
            ctypes.byref(present),
            ctypes.byref(dacl),
            ctypes.byref(defaulted),
        ):
            raise win_error(get_last_error())
        if not present.value or not dacl:
            raise PermissionError(f"Windows owner-only DACL was not created: {path}")
        result = advapi32.SetNamedSecurityInfoW(
            str(path), 1, 0x00000004 | 0x80000000, None, None, dacl, None
        )
        if result:
            raise win_error(result)
    finally:
        if descriptor:
            kernel32.LocalFree(descriptor)


def _secure_log_directory() -> None:
    ACP_LOG_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
    if os.name == "nt":
        _set_windows_owner_only(ACP_LOG_DIR, directory=True)
        return
    directory_fd = os.open(
        ACP_LOG_DIR,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fchmod(directory_fd, 0o700)
    finally:
        os.close(directory_fd)


def _secure_existing_transcripts() -> None:
    for path in ACP_LOG_DIR.glob(f"{ACP_LOG_FILE.name}*"):
        path_stat = path.lstat()
        if not stat.S_ISREG(path_stat.st_mode):
            raise PermissionError(f"ACP transcript is not a regular file: {path}")
        if os.name == "nt":
            _set_windows_owner_only(path)
        else:
            os.chmod(path, 0o600, follow_symlinks=False)


class _OwnerOnlyRotatingFileHandler(RotatingFileHandler):
    def _open(self) -> TextIOWrapper[Any]:
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.baseFilename, flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise PermissionError(
                    f"ACP transcript is not a regular file: {self.baseFilename}"
                )
            if os.name == "nt":
                _set_windows_owner_only(Path(self.baseFilename))
            else:
                os.fchmod(descriptor, 0o600)
            return cast(
                TextIOWrapper,
                os.fdopen(
                    descriptor, self.mode, encoding=self.encoding, errors=self.errors
                ),
            )
        except Exception:
            os.close(descriptor)
            raise

    def doRollover(self) -> None:
        _secure_existing_transcripts()
        super().doRollover()
        _secure_existing_transcripts()


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(record.msg, separators=(",", ":"))


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    _secure_log_directory()
    _secure_existing_transcripts()

    logger = logging.getLogger("acp_messages")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = _OwnerOnlyRotatingFileHandler(
        ACP_LOG_FILE,
        maxBytes=MAX_LOG_SIZE_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(JsonLineFormatter())
    logger.addHandler(handler)

    _logger = logger
    return _logger


def _extract_session_id(message: dict) -> str | None:
    json_str = json.dumps(message)
    match = re.search(r'"(?:session_id|sessionId)":\s*"([^"]+)"', json_str)
    return match.group(1) if match else None


def acp_message_observer(event: StreamEvent) -> None:
    if not is_acp_logging_enabled():
        return

    try:
        global _current_session

        message = event.message
        msg_id = message.get("id", "")

        if msg_id in _session_cache:
            session_id = _session_cache[msg_id]
        else:
            session_id = _extract_session_id(message) or _current_session

        if session_id is not None:
            _current_session = session_id
            if msg_id:
                _session_cache[msg_id] = session_id

        log_entry: dict = {
            "ts": datetime.now(UTC).isoformat(),
            "dir": "in" if event.direction.value == "incoming" else "out",
            "msg": message,
            **({"session": session_id} if session_id else {}),
        }

        _get_logger().info(log_entry)
    except Exception:
        pass
