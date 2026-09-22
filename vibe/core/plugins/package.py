"""Manifest validation and inert discovery for OMV plugin packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import entry_points
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from vibe.core.plugins.components import PluginPackageComponents

from vibe.core.paths import OMV_HOME
from vibe.utils.io import read_safe

OMV_PLUGIN_SCHEMA = "omv.plugin.v1"
_PLUGIN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SEMVER = re.compile(r"^(?:0|[1-9][0-9]*)\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
_ENTRYPOINT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*$"
)
_PLUGIN_CAPABILITIES = frozenset({"analyzer", "tool", "hook", "skills", "mcp"})

PluginPackageKind = Literal["analyzer", "tool", "hook", "combined"]
PluginTrust = Literal["trusted_in_process", "isolated_process"]
PluginSandboxExpectation = Literal["optional", "required"]
PluginActivation = Literal["manual"]
PluginPackageDiagnosticEvent = Literal[
    "manifest_rejected",
    "duplicate",
    "disabled",
    "layout_rejected",
    "component_rejected",
    "legacy_entrypoint",
]


class PluginPackageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["omv.plugin.v1"] = Field(
        validation_alias="schema", serialization_alias="schema"
    )
    name: str
    version: str
    kind: PluginPackageKind
    capabilities: frozenset[str] = frozenset()
    entrypoint: str
    activation: PluginActivation
    trust: PluginTrust
    sandbox: PluginSandboxExpectation = "optional"
    lifecycle_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _PLUGIN_NAME.fullmatch(value):
            raise ValueError(
                "plugin name must be 1-64 ASCII letters, digits, '.', '_' or '-'"
            )
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not _SEMVER.fullmatch(value):
            raise ValueError("plugin version must use semantic versioning")
        return value

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint(cls, value: str) -> str:
        if not _ENTRYPOINT.fullmatch(value) or ".." in value:
            raise ValueError(
                "plugin entrypoint must use safe package-local module:attribute syntax"
            )
        return value

    @model_validator(mode="after")
    def validate_capabilities(self) -> PluginPackageManifest:
        unsupported = self.capabilities - _PLUGIN_CAPABILITIES
        if unsupported:
            raise ValueError(
                f"unsupported plugin capabilities: {sorted(unsupported)!r}"
            )
        allowed = {
            "analyzer": frozenset({"analyzer", "skills", "mcp"}),
            "tool": frozenset({"tool", "skills", "mcp"}),
            "hook": frozenset({"hook", "skills", "mcp"}),
            "combined": _PLUGIN_CAPABILITIES,
        }[self.kind]
        contradictory = self.capabilities - allowed
        if contradictory:
            raise ValueError(
                f"capabilities {sorted(contradictory)!r} are not valid for "
                f"plugin kind {self.kind!r}"
            )
        return self


@dataclass(frozen=True)
class PluginPackage:
    manifest: PluginPackageManifest
    root: Path


@dataclass(frozen=True)
class PluginPackageDiagnostic:
    package: str
    event: PluginPackageDiagnosticEvent
    reason: str


@dataclass
class PluginPackageRegistry:
    installed: dict[str, PluginPackage] = field(default_factory=dict)
    enabled: dict[str, PluginPackage] = field(default_factory=dict)
    components: dict[str, PluginPackageComponents] = field(default_factory=dict)
    diagnostics: list[PluginPackageDiagnostic] = field(default_factory=list)

    def add_diagnostic(
        self, package: str, event: PluginPackageDiagnosticEvent, reason: str
    ) -> None:
        self.diagnostics.append(PluginPackageDiagnostic(package, event, reason))


def _candidate_roots(
    *, global_root: Path | None = None, project_root: Path | None = None
) -> list[Path]:
    roots = [global_root or OMV_HOME.path / "plugins"]
    if project_root is not None:
        roots.append(project_root / ".omv" / "plugins")
    return roots


def _package_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        path for path in root.iterdir() if path.is_dir() and not path.is_symlink()
    )


def _load_manifest(package_dir: Path) -> PluginPackageManifest:
    manifest_path = package_dir / "plugin.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("package must contain a regular root plugin.json")
    payload = json.loads(read_safe(manifest_path, raise_on_error=True).text)
    if not isinstance(payload, dict):
        raise ValueError("plugin.json must contain an object")
    required = {
        "schema",
        "name",
        "version",
        "kind",
        "capabilities",
        "entrypoint",
        "activation",
        "trust",
    }
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"plugin.json is missing required fields: {sorted(missing)!r}")
    manifest = PluginPackageManifest.model_validate(payload)
    if manifest.trust != "trusted_in_process":
        raise ValueError("isolated plugin protocol is not supported yet")
    return manifest


def _validate_layout(package: PluginPackage) -> None:
    root = package.root.resolve()
    for relative in ("plugin.json", "skills", "mcp.json"):
        path = package.root / relative
        if path.is_symlink():
            raise ValueError(f"package component must not be a symlink: {relative}")
        if not path.exists():
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"package component escapes package root: {relative}"
            ) from exc
    if "mcp" in package.manifest.capabilities:
        mcp = package.root / "mcp.json"
        if not mcp.is_file() or mcp.is_symlink():
            raise ValueError("mcp capability requires a regular mcp.json")
    if "skills" in package.manifest.capabilities:
        skills = package.root / "skills"
        if not skills.is_dir() or skills.is_symlink():
            raise ValueError("skills capability requires a regular skills directory")


def discover_package_plugins(
    enabled: set[str],
    *,
    global_root: Path | None = None,
    project_root: Path | None = None,
) -> PluginPackageRegistry:
    """Discover packages without importing or executing plugin code."""
    registry = PluginPackageRegistry()
    for root in _candidate_roots(global_root=global_root, project_root=project_root):
        for package_dir in _package_dirs(root):
            try:
                manifest = _load_manifest(package_dir)
                package = PluginPackage(manifest, package_dir.resolve())
                _validate_layout(package)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                registry.add_diagnostic(package_dir.name, "manifest_rejected", str(exc))
                continue
            if manifest.name in registry.installed:
                registry.add_diagnostic(
                    manifest.name, "duplicate", "plugin identity is already installed"
                )
                continue
            registry.installed[manifest.name] = package
            from vibe.core.plugins.components import load_package_components

            components = load_package_components(package)
            registry.components[manifest.name] = components
            for reason in components.diagnostics:
                registry.add_diagnostic(manifest.name, "component_rejected", reason)
            if components.diagnostics:
                continue
            if manifest.name not in enabled:
                registry.add_diagnostic(
                    manifest.name, "disabled", "plugin is installed but disabled"
                )
                continue
            registry.enabled[manifest.name] = package
    return registry


def add_legacy_entrypoint_diagnostics(
    registry: PluginPackageRegistry, names: list[str]
) -> None:
    for name in names:
        registry.add_diagnostic(
            name,
            "legacy_entrypoint",
            "legacy Python entry point remains available through the internal registry; "
            "it was not enabled as a package",
        )


def discover_legacy_entrypoint_names() -> list[str]:
    try:
        candidates = entry_points(group="omv.plugins")
    except TypeError:  # pragma: no cover - Python 3.11 compatibility
        candidates = entry_points().select(group="omv.plugins")
    return sorted(ep.name for ep in candidates)
