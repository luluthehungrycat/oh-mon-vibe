"""Plugin discovery and registration with failure isolation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import EntryPoint, entry_points
import logging
from typing import Any, Literal, Protocol, cast

PLUGIN_API_VERSION = "1"
PLUGIN_CAPABILITIES = frozenset({"analyzer", "sandbox_backend"})
PLUGIN_KINDS = frozenset({"analyzer", "sandbox", "combined"})
PluginTrust = Literal["trusted_in_process", "process_isolated"]
logger = logging.getLogger(__name__)


class PluginManifestError(ValueError):
    pass


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    api_version: str
    kind: str
    capabilities: frozenset[str] = frozenset()
    trust: PluginTrust = "trusted_in_process"

    def validate(self) -> None:
        for field_name in ("name", "version", "api_version", "kind"):
            if not getattr(self, field_name).strip():
                raise PluginManifestError(
                    f"plugin manifest field {field_name!r} is required"
                )
        if self.api_version != PLUGIN_API_VERSION:
            raise PluginManifestError(
                f"unsupported plugin API version {self.api_version!r}; "
                f"expected {PLUGIN_API_VERSION!r}"
            )
        if self.kind not in PLUGIN_KINDS:
            raise PluginManifestError(f"unsupported plugin kind {self.kind!r}")
        unsupported = self.capabilities - PLUGIN_CAPABILITIES
        if unsupported:
            raise PluginManifestError(
                f"unsupported plugin capabilities: {sorted(unsupported)!r}"
            )
        allowed = {
            "analyzer": frozenset({"analyzer"}),
            "sandbox": frozenset({"sandbox_backend"}),
            "combined": PLUGIN_CAPABILITIES,
        }[self.kind]
        undeclared = self.capabilities - allowed
        if undeclared:
            raise PluginManifestError(
                f"capabilities {sorted(undeclared)!r} are not valid for "
                f"plugin kind {self.kind!r}"
            )
        if self.trust != "trusted_in_process":
            raise PluginManifestError(
                "process-isolated plugins are unsupported until an isolating "
                "runtime is available"
            )


@dataclass(frozen=True)
class PluginDiagnostic:
    plugin: str
    event: Literal["manifest_rejected", "registration_failed"]
    reason: str
    trust: PluginTrust = "trusted_in_process"
    isolation: Literal["in_process", "process"] = "in_process"


class PluginRegistrar(Protocol):
    manifest: PluginManifest

    def register(self, registry: PluginRegistry) -> None: ...


@dataclass
class PluginRegistry:
    """Registry of extension callbacks; core safety rules remain outside it."""

    manifests: dict[str, PluginManifest] = field(default_factory=dict)
    analyzers: dict[str, Callable[..., Any]] = field(default_factory=dict)
    sandbox_backends: dict[str, Callable[..., Any]] = field(default_factory=dict)
    diagnostics: list[PluginDiagnostic] = field(default_factory=list)

    def register_plugin(self, plugin: PluginRegistrar) -> None:
        plugin.manifest.validate()
        if plugin.manifest.name in self.manifests:
            raise ValueError(f"duplicate plugin name: {plugin.manifest.name}")
        self.manifests[plugin.manifest.name] = plugin.manifest
        plugin.register(self)

    def register_analyzer(self, name: str, analyzer: Callable[..., Any]) -> None:
        if not name.strip():
            raise ValueError("analyzer name cannot be empty")
        self.analyzers[name] = analyzer

    def register_sandbox_backend(self, name: str, factory: Callable[..., Any]) -> None:
        if not name.strip():
            raise ValueError("sandbox backend name cannot be empty")
        self.sandbox_backends[name] = factory

    def record_diagnostic(
        self,
        *,
        plugin: str,
        event: Literal["manifest_rejected", "registration_failed"],
        reason: str,
        trust: PluginTrust = "trusted_in_process",
    ) -> None:
        self.diagnostics.append(PluginDiagnostic(plugin, event, reason, trust=trust))


def _load_entry_point(ep: EntryPoint) -> PluginRegistrar:
    loaded = ep.load()
    plugin = (
        loaded() if callable(loaded) and not hasattr(loaded, "manifest") else loaded
    )
    if not hasattr(plugin, "manifest") or not hasattr(plugin, "register"):
        raise TypeError(f"entry point {ep.name!r} is not an Oh My Vibe plugin")
    return cast(PluginRegistrar, plugin)


def discover_plugins(
    enabled: set[str], *, registry: PluginRegistry | None = None
) -> PluginRegistry:
    """Load only explicitly enabled plugins; isolate each plugin failure."""
    result = registry or PluginRegistry()
    try:
        candidates = entry_points(group="omv.plugins")
    except TypeError:  # pragma: no cover - Python 3.11 compatibility
        candidates = entry_points().select(group="omv.plugins")
    for ep in candidates:
        if ep.name not in enabled:
            continue
        try:
            plugin = _load_entry_point(ep)
        except Exception as exc:
            result.record_diagnostic(
                plugin=ep.name, event="registration_failed", reason=str(exc)
            )
            logger.exception("Skipping Oh My Vibe plugin %s", ep.name)
            continue
        try:
            result.register_plugin(plugin)
        except PluginManifestError as exc:
            result.record_diagnostic(
                plugin=ep.name, event="manifest_rejected", reason=str(exc)
            )
            logger.exception("Rejecting Oh My Vibe plugin manifest %s", ep.name)
        except Exception as exc:
            result.record_diagnostic(
                plugin=ep.name, event="registration_failed", reason=str(exc)
            )
            logger.exception("Skipping Oh My Vibe plugin %s", ep.name)
    return result
