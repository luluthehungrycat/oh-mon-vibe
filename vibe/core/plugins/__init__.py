"""Stable extension contracts for Oh My Vibe plugins."""

from __future__ import annotations

from vibe.core.plugins.components import (
    PluginPackageComponents,
    load_package_components,
)
from vibe.core.plugins.conformance import (
    PluginConformanceError,
    PluginConformanceEvidence,
    PluginConformanceReport,
    run_plugin_conformance,
)
from vibe.core.plugins.lifecycle import (
    PluginLifecycle,
    PluginLifecycleDiagnostic,
    PluginLifecyclePhase,
)
from vibe.core.plugins.package import (
    OMV_PLUGIN_SCHEMA,
    PluginPackage,
    PluginPackageDiagnostic,
    PluginPackageManifest,
    PluginPackageRegistry,
    add_legacy_entrypoint_diagnostics,
    discover_package_plugins,
)
from vibe.core.plugins.policy import (
    PluginAnalyzerResult,
    PluginDecision,
    PluginPermissionPolicy,
    PluginPermissionRule,
    compose_plugin_decision,
)
from vibe.core.plugins.registry import (
    PLUGIN_API_VERSION,
    PLUGIN_CAPABILITIES,
    PLUGIN_KINDS,
    PluginManifest,
    PluginManifestError,
    PluginRegistry,
    PluginTrust,
    discover_plugins,
)
from vibe.core.plugins.runtime import (
    PluginApprovalRequired,
    PluginLoadError,
    PluginPermissionDenied,
    PluginRuntimeManager,
    load_package_entrypoint,
)
from vibe.core.plugins.sandbox import (
    PLUGIN_STDIO_PROTOCOL,
    PluginCapabilityEvidence,
    PluginSandboxError,
    PluginSandboxPlan,
    PluginStdioRequest,
    PluginStdioResponse,
    require_plugin_isolation,
    select_plugin_sandbox,
)

__all__ = [
    "OMV_PLUGIN_SCHEMA",
    "PLUGIN_API_VERSION",
    "PLUGIN_CAPABILITIES",
    "PLUGIN_KINDS",
    "PLUGIN_STDIO_PROTOCOL",
    "PluginAnalyzerResult",
    "PluginApprovalRequired",
    "PluginCapabilityEvidence",
    "PluginConformanceError",
    "PluginConformanceEvidence",
    "PluginConformanceReport",
    "PluginDecision",
    "PluginLifecycle",
    "PluginLifecycleDiagnostic",
    "PluginLifecyclePhase",
    "PluginLoadError",
    "PluginManifest",
    "PluginManifestError",
    "PluginPackage",
    "PluginPackageComponents",
    "PluginPackageDiagnostic",
    "PluginPackageManifest",
    "PluginPackageRegistry",
    "PluginPermissionDenied",
    "PluginPermissionPolicy",
    "PluginPermissionRule",
    "PluginRegistry",
    "PluginRuntimeManager",
    "PluginSandboxError",
    "PluginSandboxPlan",
    "PluginStdioRequest",
    "PluginStdioResponse",
    "PluginTrust",
    "add_legacy_entrypoint_diagnostics",
    "compose_plugin_decision",
    "discover_package_plugins",
    "discover_plugins",
    "load_package_components",
    "load_package_entrypoint",
    "require_plugin_isolation",
    "run_plugin_conformance",
    "select_plugin_sandbox",
]
