## ADDED Requirements

### Requirement: OMV uses the upstream Agent Plugins package resolver

Oh My Vibe MUST use the upstream Agent Plugins resolver as the sole package implementation. A supported package uses the published Agent Plugins 1.0 root `plugin.json`, the published MCP schema in root `mcp.json` with `mcpServers`, and the fixed `skills/` directory. OMV MUST NOT define a competing root manifest, package activation model, or custom package permission/sandbox contract.

#### Scenario: Canonical package is discovered

- **WHEN** a package in a configured user or project plugin directory contains a valid Agent Plugins 1.0 `plugin.json`
- **THEN** the upstream resolver MUST inspect the package using the published schema and its standard `skills/` and `mcp.json` components

#### Scenario: Noncanonical OMV manifest is present

- **WHEN** a package uses `omv.plugin.v1` or OMV-only root fields instead of the published Agent Plugins schema
- **THEN** OMV MUST NOT treat it as an alternate supported package format

### Requirement: OMV extension metadata is namespaced and inert

OMV-specific metadata MUST be placed under `extensions["com.ohmyvibe"]`. Until an OMV extension schema and enforcement path are implemented, that entry MUST NOT grant executable capabilities, permissions, or sandbox guarantees.

#### Scenario: Package declares OMV extension data

- **WHEN** a canonical package includes `extensions["com.ohmyvibe"]`
- **THEN** the upstream resolver MUST leave that data inert and MUST NOT interpret it as authority

### Requirement: OMV plugin compatibility claims are scoped

The Oh My Vibe v1 package claim SHALL cover Agent Plugins-compatible skills/MCP and upstream discovery/inspection only. OMV-specific native analyzer, tool, and hook execution, and plugin-specific sandbox enforcement, SHALL remain deferred until invocation and permission behavior are implemented and tested.

#### Scenario: Documentation describes plugin support

- **WHEN** Oh My Vibe documentation describes package support
- **THEN** it MUST state the supported skills/MCP scope and MUST NOT claim OMV-native analyzer/tool/hook execution or plugin sandbox enforcement
