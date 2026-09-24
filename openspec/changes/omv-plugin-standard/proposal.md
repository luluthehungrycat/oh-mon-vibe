## Why

Oh My Vibe inherited a second, OMV-specific `plugin.json` contract beside the upstream Agent Plugins resolver. That contract claimed native analyzers, tools, hooks, permissions, and plugin sandboxing without a single end-to-end runtime enforcement path. Upstream Mistral Vibe v2.25.7 already provides an Agent Plugins 1.0 resolver for canonical `plugin.json`, `mcp.json`, and `skills/` packages. Oh My Vibe must keep that as the only package architecture.

## What Changes

- Reconcile the branch with upstream Mistral Vibe v2.25.7 using a preserved merge commit.
- Use the published Agent Plugins 1.0 root `plugin.json` and MCP `mcp.json` schema through the upstream resolver.
- Remove the competing `omv.plugin.v1` manifest, its package lifecycle, permission and sandbox models, and their configuration surface.
- Reserve `extensions["com.ohmyvibe"]` for future OMV-specific metadata; it remains inert until an extension schema and enforcement are implemented.
- Limit the Oh My Vibe plugin-package claim to standard skills/MCP and upstream discovery/inspection. Defer OMV-specific analyzers, native tool/hook adapters, and plugin sandbox enforcement.
- Keep the existing internal Python analyzer registry distinct from Agent Plugins packages; it is not a package loader or compatibility claim.

## Capabilities

### New Capabilities

- `omv-plugin-packages`: Defines the upstream Agent Plugins package shape and the limited Oh My Vibe compatibility boundary.

### Modified Capabilities

- None.

## Impact

This change uses the upstream resolver as the sole Agent Plugins package implementation. Existing Vibe MCP authorization and tool-permission behavior remain the enforcement path for MCP tools. The existing internal Python analyzer registry remains separate and does not load `plugin.json` packages. OMV-specific native analyzer/tool/hook execution and plugin-specific sandbox enforcement are explicitly deferred.
