"""Structured host conformance checks for OMV plugin package claims."""

from __future__ import annotations

from dataclasses import dataclass

from vibe.core.plugins.components import load_package_components
from vibe.core.plugins.package import PluginPackage


class PluginConformanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PluginConformanceEvidence:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PluginConformanceReport:
    plugin: str
    evidence: tuple[PluginConformanceEvidence, ...]

    @property
    def complete(self) -> bool:
        return all(item.passed for item in self.evidence)

    def require_complete(self) -> None:
        if not self.complete:
            failed = "; ".join(
                f"{item.check}: {item.detail}"
                for item in self.evidence
                if not item.passed
            )
            raise PluginConformanceError(f"incomplete plugin conformance: {failed}")


def run_plugin_conformance(package: PluginPackage) -> PluginConformanceReport:
    evidence: list[PluginConformanceEvidence] = []
    root = package.root.resolve()
    manifest_path = root / "plugin.json"
    evidence.append(
        PluginConformanceEvidence(
            "manifest",
            manifest_path.is_file() and not manifest_path.is_symlink(),
            "regular root plugin.json"
            if manifest_path.is_file()
            else "missing plugin.json",
        )
    )
    evidence.append(
        PluginConformanceEvidence(
            "schema",
            package.manifest.schema_version == "omv.plugin.v1",
            package.manifest.schema_version,
        )
    )
    evidence.append(
        PluginConformanceEvidence(
            "trust",
            package.manifest.trust == "trusted_in_process",
            package.manifest.trust,
        )
    )
    components = load_package_components(package)
    evidence.extend(
        PluginConformanceEvidence("component", not components.diagnostics, detail)
        for detail in components.diagnostics
    )
    if not components.diagnostics:
        evidence.append(
            PluginConformanceEvidence("components", True, "fixed components validated")
        )
    return PluginConformanceReport(package.manifest.name, tuple(evidence))


__all__ = [
    "PluginConformanceError",
    "PluginConformanceEvidence",
    "PluginConformanceReport",
    "run_plugin_conformance",
]
