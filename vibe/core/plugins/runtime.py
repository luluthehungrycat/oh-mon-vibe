"""Explicit package entrypoint loading and lifecycle activation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

from vibe.core.plugins.lifecycle import PluginLifecycle
from vibe.core.plugins.package import PluginPackage, PluginPackageRegistry
from vibe.core.plugins.policy import PluginPermissionPolicy, compose_plugin_decision
from vibe.core.plugins.sandbox import (
    PluginSandboxBackend,
    PluginSandboxError,
    PluginSandboxPolicy,
    require_plugin_isolation,
    select_plugin_sandbox,
)
from vibe.core.safety.policy import CommandDecision, Decision


class PluginLoadError(RuntimeError):
    pass


class PluginPermissionDenied(RuntimeError):
    pass


class PluginApprovalRequired(RuntimeError):
    pass


def load_package_entrypoint(package: PluginPackage) -> object:
    entrypoint = package.manifest.entrypoint
    if entrypoint.count(":") != 1:
        raise PluginLoadError(
            "entrypoint must use exactly one module:attribute separator"
        )
    module_name, attribute = entrypoint.split(":")
    if (
        not module_name
        or not attribute
        or not all(part.isidentifier() for part in module_name.split("."))
        or not attribute.isidentifier()
    ):
        raise PluginLoadError("entrypoint must use module:attribute syntax")
    module_path = _module_path(package.root, module_name)
    if module_path is None:
        raise PluginLoadError(f"entrypoint module not found: {module_name}")
    import_name = f"_omv_plugin_{package.manifest.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(import_name, module_path)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"cannot load entrypoint module: {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[import_name] = module
    try:
        spec.loader.exec_module(module)
        loaded = getattr(module, attribute)
        implementation = loaded() if callable(loaded) else loaded
    except Exception as exc:
        sys.modules.pop(import_name, None)
        raise PluginLoadError(f"entrypoint failed: {exc}") from exc
    if implementation is None:
        raise PluginLoadError("entrypoint factory returned no plugin implementation")
    return implementation


class PluginRuntimeManager:
    def __init__(
        self,
        registry: PluginPackageRegistry,
        lifecycle: PluginLifecycle,
        permission_policy: PluginPermissionPolicy | None = None,
        *,
        sandbox_policy: PluginSandboxPolicy = "off",
        sandbox_backend: PluginSandboxBackend = "auto",
    ) -> None:
        self.registry = registry
        self.lifecycle = lifecycle
        self.permission_policy = permission_policy or PluginPermissionPolicy()
        self.sandbox_policy: PluginSandboxPolicy = sandbox_policy
        self.sandbox_backend: PluginSandboxBackend = sandbox_backend

    async def activate_enabled(self) -> None:
        for package in self.registry.enabled.values():
            try:
                self._validate_activation_isolation(package)
                implementation = load_package_entrypoint(package)
            except (PluginLoadError, PluginSandboxError) as exc:
                self.lifecycle.record_failure(package.manifest.name, str(exc))
                continue
            await self.lifecycle.activate(package, implementation)

    def _validate_activation_isolation(self, package: PluginPackage) -> None:
        if "mcp" in package.manifest.capabilities:
            raise PluginSandboxError(
                "plugin MCP components require a policy-aware host adapter; activation refused"
            )
        if package.manifest.trust == "isolated_process":
            raise PluginSandboxError(
                "isolated-process plugin runtime is unavailable; activation refused"
            )
        plan = select_plugin_sandbox(
            self.sandbox_policy,
            self.sandbox_backend,
            command=package.manifest.entrypoint,
            cwd=package.root,
        )
        require_plugin_isolation(
            manifest_expectation=package.manifest.sandbox,
            policy=self.sandbox_policy,
            plan=plan,
        )
        if self.sandbox_policy == "auto" and plan is None:
            raise PluginSandboxError(
                "optional plugin sandbox backend is unavailable; activation refused"
            )
        if plan is not None and not plan.evidence.complete:
            raise PluginSandboxError(
                "selected plugin sandbox lacks executable timeout and cleanup evidence"
            )
        if plan is not None:
            raise PluginSandboxError(
                "isolated-process plugin activation is unavailable"
            )

    async def invoke_authorized(
        self,
        name: str,
        method_name: str,
        *,
        capability: str,
        action: str,
        command: str,
        side_effect: bool,
        core: CommandDecision | None = None,
        args: tuple[Any, ...] = (),
    ) -> object:
        result = self.permission_policy.analyze(
            plugin=name,
            capability=capability,
            action=action,
            command=command,
            side_effect=side_effect,
        )
        decision = compose_plugin_decision(
            core or CommandDecision(Decision.ALLOW, "host policy passed", "core"),
            result,
            plugin=name,
        )
        if decision.outcome == Decision.DENY:
            raise PluginPermissionDenied(decision.reason)
        if decision.outcome != Decision.ALLOW:
            raise PluginApprovalRequired(decision.reason)
        return await self.lifecycle.invoke(name, method_name, *args)

    async def shutdown(self) -> None:
        await self.lifecycle.shutdown()


def _module_path(root: Path, module_name: str) -> Path | None:
    relative = Path(*module_name.split("."))
    candidates = (root / f"{relative}.py", root / relative / "__init__.py")
    for candidate in candidates:
        if not candidate.is_file() or candidate.is_symlink():
            continue
        try:
            candidate.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        return candidate
    return None


__all__ = [
    "PluginApprovalRequired",
    "PluginLoadError",
    "PluginPermissionDenied",
    "PluginRuntimeManager",
    "load_package_entrypoint",
]
