## Why

PR #1 established an internal plugin registry and safety-aware analyzer boundary, but issue #2 proposes a cross-harness plugin standard and standalone SDK. Extracting immediately would freeze incomplete trust, timeout, manifest, and adapter semantics. This foundation change will define and validate the prerequisites without shipping a premature interoperability promise.

## What Changes

- Specify the minimum plugin capability, manifest, versioning, and discovery contracts.
- Define trust levels, authority boundaries, failure behavior, timeout semantics, and process-isolation requirements.
- Add conformance fixtures and contract tests for the existing Oh My Vibe implementation.
- Document the adapter requirements for Hermes Agent and OpenCode without implementing those adapters yet.
- Identify the prerequisites and exit criteria for a future standalone `oh-my-vibe-plugin-sdk`.
- Explicitly defer desktop integration, centralized plugin registry hosting, and dynamic untrusted plugin installation.

## Capabilities

### New Capabilities

- `plugin-contract-foundation`: Defines the stable, harness-neutral plugin contract prerequisites.
- `plugin-conformance`: Defines tests and evidence required before SDK extraction or adapter claims.

### Modified Capabilities

- None.

This is primarily a specification, contract-test, and documentation change
around `vibe/core/plugins`, safety analyzers, sandbox interfaces, and future
adapter boundaries. Adapter mappings, fixture requirements, review evidence,
and SDK exit criteria live in the change artifacts; owner review remains
required before any SDK implementation proposal. It must not weaken the
merged deterministic safety precedence or claim process isolation until an
isolating runtime exists.
