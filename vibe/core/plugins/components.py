"""Fixed, inert package components with per-component diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from vibe.core.config import MCPServer
from vibe.core.plugins.package import PluginPackage
from vibe.utils.io import read_safe

_MCP_SERVERS = TypeAdapter(list[MCPServer])


@dataclass(frozen=True)
class PluginPackageComponents:
    skills: Path | None = None
    mcp: dict[str, Any] | None = None
    mcp_servers: tuple[MCPServer, ...] = ()
    diagnostics: tuple[str, ...] = ()


def load_package_components(package: PluginPackage) -> PluginPackageComponents:
    skills = None
    mcp = None
    mcp_servers: tuple[MCPServer, ...] = ()
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
            raw_servers = payload.get("servers")
            if not isinstance(raw_servers, list):
                raise ValueError("mcp.json must contain a servers list")
            mcp_servers = tuple(_MCP_SERVERS.validate_python(raw_servers))
            mcp = payload
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            diagnostics.append(str(exc))
    return PluginPackageComponents(
        skills=skills, mcp=mcp, mcp_servers=mcp_servers, diagnostics=tuple(diagnostics)
    )
