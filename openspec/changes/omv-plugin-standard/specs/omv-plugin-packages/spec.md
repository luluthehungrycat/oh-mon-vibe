## ADDED Requirements

### Requirement: Plugins use validated JSON manifests

An OMV plugin package MUST contain a root `plugin.json` with schema version,
name, semantic version, kind, capabilities, entry point, activation, trust,
and sandbox expectation fields. The host MUST reject missing, malformed,
unsupported, or contradictory fields before importing plugin code.

#### Scenario: Valid disabled plugin is installed

- **WHEN** a package has a valid `plugin.json` but is absent from the enabled-plugin allowlist
- **THEN** OMV SHALL record it as installed and SHALL NOT import, register, or execute its code

#### Scenario: Invalid manifest is discovered

- **WHEN** a package has an unknown capability, unsupported schema, duplicate identity, or invalid kind/capability combination
- **THEN** OMV SHALL reject the package with structured diagnostics and SHALL continue discovering unrelated packages

### Requirement: Plugin lifecycle is Hermes-inspired and failure-isolated

OMV SHALL provide explicit discovery, validation, enablement, registration,
activation, invocation, deactivation, and cleanup phases. Lifecycle callbacks
MUST be bounded and a failure in one plugin MUST NOT prevent unrelated plugins
or host shutdown from completing.

#### Scenario: Enabled plugin activates

- **WHEN** a validated plugin is explicitly enabled
- **THEN** OMV SHALL register and activate it through a typed lifecycle context before invocation

#### Scenario: Plugin activation fails

- **WHEN** an enabled plugin raises during registration or activation
- **THEN** OMV SHALL record the phase and failure, disable that plugin for the session, and continue with built-ins and unrelated plugins

#### Scenario: Host shuts down with active plugins

- **WHEN** the session ends
- **THEN** OMV SHALL invoke bounded cleanup for each active plugin and SHALL report cleanup failures without blocking host shutdown
