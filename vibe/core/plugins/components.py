"""Fixed, inert package components with per-component diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from vibe.core.plugins.package import PluginPackage
from vibe.utils.io import read_safe


@dataclass(frozen=True)
class PluginPackageComponents:
    skills: Path | None = None
    mcp: dict[str, Any] | None = None
    diagnostics: tuple[str, ...] = ()


def load_package_components(package: PluginPackage) -> PluginPackageComponents:
    skills = None
    mcp = None
    diagnostics: list[str] = []
    if "skills" in package.manifest.capabilities:
        path = package.root / "skills"
        if path.is_dir() and not path.is_symlink():
            skills = path
        else:
            diagnostics.append("skills component is not a regular directory")
    if "mcp" in package.manifest.capabilities:
        path = package.root / "mcp.json"
        try:
            if not path.is_file() or path.is_symlink():
                raise ValueError("mcp component is not a regular file")
            payload = json.loads(read_safe(path, raise_on_error=True).text)
            if not isinstance(payload, dict):
                raise ValueError("mcp.json must contain an object")
            mcp = payload
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            diagnostics.append(str(exc))
    return PluginPackageComponents(
        skills=skills, mcp=mcp, diagnostics=tuple(diagnostics)
    )
