"""Structured host conformance checks for OMV plugin package claims."""

from __future__ import annotations

from dataclasses import dataclass
import json

from vibe.core.plugins.components import load_package_components
from vibe.core.plugins.package import PluginPackage, PluginPackageManifest
from vibe.utils.io import read_safe


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
    root = package.root
    manifest_path = root / "plugin.json"
    manifest_ok = False
    manifest_detail = "regular root plugin.json"
    if manifest_path.is_symlink():
        manifest_detail = "plugin.json must not be a symlink"
    else:
        try:
            payload = json.loads(read_safe(manifest_path, raise_on_error=True).text)
            parsed = PluginPackageManifest.model_validate(payload)
            manifest_ok = parsed == package.manifest
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            manifest_detail = f"invalid plugin.json: {exc}"
    evidence.append(PluginConformanceEvidence("manifest", manifest_ok, manifest_detail))
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
    evidence.append(
        PluginConformanceEvidence(
            "sandbox",
            package.manifest.sandbox == "optional",
            "trusted in-process execution does not claim isolation"
            if package.manifest.sandbox == "optional"
            else "required sandbox evidence must be supplied by an isolation runtime",
        )
    )
    components = load_package_components(package)
    evidence.extend(
        PluginConformanceEvidence("component", False, detail)
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
