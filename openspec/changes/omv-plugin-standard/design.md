## Context

Upstream Mistral Vibe v2.25.7 contains the canonical Agent Plugins 1.0 resolver. Oh My Vibe's earlier `omv.plugin.v1` implementation duplicated package discovery and claimed permissions and sandbox guarantees without enforcing them across actual plugin invocation. Keeping both implementations would make manifest interpretation and authority ambiguous.

## Goals / Non-Goals

**Goals:**

- Use the upstream resolver for Agent Plugins package discovery.
- Preserve the published root `plugin.json`, root `mcp.json`, and fixed `skills/` package structure.
- Keep OMV metadata in a stable reverse-domain `extensions` entry without granting it executable authority.
- Preserve the existing Bash safety policy and internal Python analyzer extension separately from Agent Plugins packages.
- State the supported and deferred capability boundary accurately.

**Non-Goals:**

- Defining a custom OMV root manifest or a second package resolver.
- Claiming native Agent Plugin analyzers, tools, or hooks as OMV features.
- Claiming plugin-specific process isolation or sandbox enforcement.
- Extracting an SDK or claiming native Hermes/OpenCode compatibility.

## Decisions

### One package resolver

The upstream `PluginResolver` is the sole resolver for package files. It recognizes the published Agent Plugins 1.0 `$schema` in root `plugin.json`, the corresponding MCP schema and `mcpServers` object in root `mcp.json`, and the fixed `skills/` directory. The OMV-only `omv.plugin.v1` root schema, enablement config, package lifecycle, and plugin sandbox APIs are removed.

### OMV extension namespace

Future OMV-specific package metadata belongs under `extensions["com.ohmyvibe"]`. The namespace currently has no defined fields; the upstream resolver ignores it, so it grants no permission, execution capability, or sandbox status. Standard Agent Plugins fields remain interpreted only according to upstream semantics.

### Scoped v1 claims

Oh My Vibe claims compatibility for standard Agent Plugins skills/MCP and upstream discovery/inspection. Native analyzers, tools, and hooks are not an OMV extension contract. The existing Python analyzer entry-point registry is an internal Bash safety extension and does not load Agent Plugins packages. Plugin-specific real sandbox enforcement is deferred; existing Bash sandbox behavior is a distinct host feature.

## Risks / Trade-offs

- **Upstream resolver behavior can evolve** → retain the upstream versioned schema and tests; do not fork its manifest contract.
- **The extension namespace is reserved but currently inert** → document that it grants no authority until a schema and host enforcement are implemented.
- **The supported claim is narrower than the prior proposal** → avoid implying that manifest metadata itself provides permission or isolation guarantees.
