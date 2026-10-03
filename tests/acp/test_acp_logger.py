from __future__ import annotations

import logging
import os
from pathlib import Path
import stat

import pytest

from vibe.acp import acp_logger


def _windows_dacl_sddl(path: Path) -> str:
    import ctypes
    from ctypes import wintypes

    win_dll = ctypes.__dict__["WinDLL"]
    win_error = ctypes.__dict__["WinError"]
    get_last_error = ctypes.__dict__["get_last_error"]
    advapi32 = win_dll("advapi32", use_last_error=True)
    kernel32 = win_dll("kernel32", use_last_error=True)
    advapi32.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = (
        wintypes.BOOL
    )
    kernel32.LocalFree.argtypes = [wintypes.HANDLE]
    kernel32.LocalFree.restype = wintypes.HANDLE
    descriptor = ctypes.c_void_p()
    sddl = wintypes.LPWSTR()
    result = advapi32.GetNamedSecurityInfoW(
        str(path), 1, 0x00000004, None, None, None, None, ctypes.byref(descriptor)
    )
    if result:
        raise win_error(result)
    try:
        size = wintypes.DWORD()
        security_information = 0x00000004 | 0x80000000
        if not advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            descriptor, 1, security_information, ctypes.byref(sddl), ctypes.byref(size)
        ):
            raise win_error(get_last_error())
        if sddl.value is None:
            raise OSError("Windows returned an empty security descriptor")
        return sddl.value
    finally:
        if sddl:
            kernel32.LocalFree(sddl)
        if descriptor:
            kernel32.LocalFree(descriptor)


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_acp_logger_creates_owner_only_transcripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ACP transcripts hold full session messages, so they land owner-only."""
    log_dir = tmp_path / "acp"
    log_dir.mkdir()
    log_dir.chmod(0o755)
    transcript = log_dir / "messages.jsonl"
    transcript.write_text("existing\n", encoding="utf-8")
    transcript.chmod(0o644)
    (log_dir / "messages.jsonl.1").write_text("older\n", encoding="utf-8")
    (log_dir / "messages.jsonl.1").chmod(0o644)
    monkeypatch.setattr(acp_logger, "ACP_LOG_DIR", log_dir)
    monkeypatch.setattr(acp_logger, "ACP_LOG_FILE", transcript)
    monkeypatch.setattr(acp_logger, "_logger", None)
    monkeypatch.setattr(acp_logger, "MAX_LOG_SIZE_BYTES", 64)

    try:
        logger = acp_logger._get_logger()
        for index in range(10):
            logger.info({"msg": f"rotation-{index}"})
        logger.info({"msg": "hello"})

        assert stat.S_IMODE(log_dir.stat().st_mode) & 0o077 == 0
        transcripts = list(log_dir.glob("messages.jsonl*"))
        assert len(transcripts) > 1
        assert all(
            stat.S_IMODE(path.stat().st_mode) & 0o077 == 0 for path in transcripts
        )
        assert "hello" in transcript.read_text(encoding="utf-8")
    finally:
        logging.getLogger("acp_messages").handlers.clear()


@pytest.mark.skipif(os.name != "nt", reason="Windows DACL handling")
def test_acp_logger_secures_windows_transcripts_and_rotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_dir = tmp_path / "acp"
    log_dir.mkdir()
    transcript = log_dir / "messages.jsonl"
    transcript.write_text("existing\n", encoding="utf-8")
    (log_dir / "messages.jsonl.1").write_text("older\n", encoding="utf-8")
    monkeypatch.setattr(acp_logger, "ACP_LOG_DIR", log_dir)
    monkeypatch.setattr(acp_logger, "ACP_LOG_FILE", transcript)
    monkeypatch.setattr(acp_logger, "_logger", None)
    monkeypatch.setattr(acp_logger, "MAX_LOG_SIZE_BYTES", 64)

    try:
        logger = acp_logger._get_logger()
        for index in range(10):
            logger.info({"msg": f"rotation-{index}"})
        logger.info({"msg": "hello"})

        transcripts = list(log_dir.glob("messages.jsonl*"))
        assert len(transcripts) > 1
        assert "hello" in transcript.read_text(encoding="utf-8")
        sid = acp_logger._windows_current_user_sid()
        for path in [log_dir, *transcripts]:
            dacl = _windows_dacl_sddl(path)
            assert dacl.startswith("D:P(")
            assert dacl.count("(") == 1
            assert f";;;{sid})" in dacl
    finally:
        logging.getLogger("acp_messages").handlers.clear()
