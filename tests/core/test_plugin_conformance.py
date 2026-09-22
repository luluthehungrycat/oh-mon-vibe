from __future__ import annotations

from pathlib import Path

import pytest

from vibe.core.plugins.conformance import PluginConformanceError, run_plugin_conformance
from vibe.core.plugins.package import PluginPackage, PluginPackageManifest


def _package(root: Path, *, capabilities: list[str] | None = None) -> PluginPackage:
    return PluginPackage(
        PluginPackageManifest(
            name="demo",
            version="1.0.0",
            kind="analyzer",
            capabilities=frozenset(capabilities or []),
            entrypoint="plugin:create",
        ),
        root,
    )


def test_conformance_report_records_complete_manifest_evidence(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (tmp_path / "plugin.json").write_text("{}")

    report = run_plugin_conformance(package)

    assert report.complete
    report.require_complete()
    assert {item.check for item in report.evidence} >= {"manifest", "schema", "trust"}


def test_conformance_refuses_broken_component_claim(tmp_path: Path) -> None:
    package = _package(tmp_path, capabilities=["mcp"])
    (tmp_path / "plugin.json").write_text("{}")

    report = run_plugin_conformance(package)

    assert not report.complete
    with pytest.raises(PluginConformanceError, match="mcp component"):
        report.require_complete()
