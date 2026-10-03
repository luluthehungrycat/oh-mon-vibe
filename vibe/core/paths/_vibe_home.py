from __future__ import annotations

import os
import stat

from vibe import VIBE_ROOT
from vibe.observability.logging import logger
from vibe.utils.paths import GlobalPath, get_omv_home
from vibe.utils.platform import is_windows

OMV_HOME = GlobalPath(get_omv_home)
VIBE_HOME = OMV_HOME
GLOBAL_ENV_FILE = GlobalPath(lambda: OMV_HOME.path / ".env")
SESSION_LOG_DIR = GlobalPath(lambda: VIBE_HOME.path / "logs" / "session")
WORKTREES_DIR = GlobalPath(lambda: VIBE_HOME.path / "worktrees")
TRUSTED_FOLDERS_FILE = GlobalPath(lambda: VIBE_HOME.path / "trusted_folders.toml")
LOG_DIR = GlobalPath(lambda: VIBE_HOME.path / "logs")
LOG_FILE = GlobalPath(lambda: OMV_HOME.path / "logs" / "omv.log")
CACHE_FILE = GlobalPath(lambda: VIBE_HOME.path / "cache.toml")
PROJECTS_FILE = GlobalPath(lambda: VIBE_HOME.path / "projects.toml")
CONNECTOR_BOOTSTRAP_CACHE_FILE = GlobalPath(
    lambda: VIBE_HOME.path / "connector_bootstrap_cache.json"
)
EXPERIMENT_EVAL_CACHE_FILE = GlobalPath(
    lambda: VIBE_HOME.path / "experiment_eval_cache.json"
)
WHOAMI_CACHE_FILE = GlobalPath(lambda: VIBE_HOME.path / "whoami_cache.json")
_GROUP_OTHER = 0o077


def restrict_vibe_home_permissions() -> None:
    if is_windows():
        return
    home = VIBE_HOME.path
    try:
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        mode = stat.S_IMODE(os.lstat(home).st_mode)
        if mode & _GROUP_OTHER:
            os.chmod(home, mode & ~_GROUP_OTHER)
    except OSError as e:
        logger.debug("Could not restrict Vibe home permissions: %s", e)


def bootstrap_vibe_home() -> None:
    restrict_vibe_home_permissions()
    history_file = HISTORY_FILE.path
    if history_file.exists():
        return
    try:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.touch(mode=0o600, exist_ok=True)
        history_file.write_text("Hello Vibe!\n", "utf-8")
    except OSError as e:
        logger.error("Could not create Vibe home history file: %s", e)


HISTORY_FILE = GlobalPath(lambda: OMV_HOME.path / "omv_history")
PLANS_DIR = GlobalPath(lambda: VIBE_HOME.path / "plans")

DEFAULT_TOOL_DIR = GlobalPath(lambda: VIBE_ROOT / "core" / "tools" / "builtins")
