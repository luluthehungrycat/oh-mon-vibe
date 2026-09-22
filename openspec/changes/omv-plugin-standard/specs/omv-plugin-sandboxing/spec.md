## ADDED Requirements

### Requirement: Plugin sandbox expectations are explicit

A plugin MUST declare `sandbox: optional` or `sandbox: required`; omission SHALL
mean `optional`. User policy MUST support `off`, `auto`, and `required` modes.
The host owns sandbox selection and MUST expose capability evidence before
activation.

#### Scenario: Optional plugin runs with sandboxing disabled

- **WHEN** user policy is `off` and an optional plugin is enabled
- **THEN** OMV MAY run it only as trusted in-process code and SHALL not claim it is sandboxed

#### Scenario: Required plugin cannot be isolated

- **WHEN** user policy or the plugin requires isolation but no compatible process sandbox is available
- **THEN** OMV SHALL refuse activation and SHALL not fall back to unsandboxed execution

#### Scenario: User opts into optional plugin sandboxing

- **WHEN** user policy is `auto` or `required` and an optional plugin provides a compatible isolated-process protocol
- **THEN** OMV SHALL run it through the selected backend and SHALL report availability, network isolation, writable-workdir, timeout, and cleanup capabilities

### Requirement: Untrusted plugins cannot claim isolation without evidence

OMV MUST distinguish trusted in-process plugins from isolated-process plugins.
Thread timeouts and manifest metadata alone MUST NOT satisfy isolation. An
isolated plugin MUST provide a versioned protocol, bounded resource contract,
cancellation behavior, and cleanup guarantee.

#### Scenario: Untrusted plugin lacks an isolation runtime

- **WHEN** a plugin declares `isolated_process` but the host lacks the required protocol or backend
- **THEN** OMV SHALL reject it before activation with structured trust and isolation diagnostics

#### Scenario: Sandbox startup fails

- **WHEN** the selected backend fails before plugin code starts
- **THEN** OMV SHALL apply the configured fallback policy and SHALL keep required-sandbox plugins disabled
