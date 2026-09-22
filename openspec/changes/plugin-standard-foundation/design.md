## Context

The current implementation contains a useful internal registry and safety analyzer boundary, but it is host-specific and intentionally fail-closed. Issue #2 proposes a language-agnostic, cross-harness standard and SDK; that future scope requires stronger contracts than the current internal API alone proves.

## Goals / Non-Goals

**Goals:**

- Define a minimal versioned manifest and capability vocabulary.
- Preserve host authority over permissions, sandboxing, and explicit denial.
- Make timeout/failure/isolation semantics explicit.
- Establish conformance and adapter evidence required before SDK extraction.

**Non-Goals:**

- Publishing a standalone SDK.
- Implementing Hermes Agent or OpenCode adapters.
- Installing arbitrary third-party plugins dynamically.
- Creating a centralized plugin marketplace or registry.
- Building the deferred desktop application.

## Decisions

### Capability-scoped manifests

Use a small versioned manifest with explicit kind and capabilities. Alternatives were unconstrained Python entry points or a broad universal schema. Unconstrained entry points weaken discovery and review; a broad schema would freeze speculative fields. Start minimal and version deliberately.

### Host-authoritative safety

Plugin results remain advisory. The host owns deterministic permission composition and sandbox enforcement. Alternatives were plugin-controlled policy or shared authority; both create bypass risk and make cross-harness semantics unsafe.

### Separate trust and isolation levels

Document trusted in-process execution separately from process-isolated execution. Python threads provide bounded waiting but cannot stop arbitrary code. Alternatives were treating timeout metadata as isolation or requiring process isolation immediately for all plugins; the former is unsafe, the latter would block the current trusted internal use case.

### Conformance before SDK extraction

Contract tests and one reviewed adapter mapping are prerequisites. The
design-only Hermes Agent and OpenCode mappings, evidence fixtures, and SDK
readiness gate are maintained in `adapter-mappings.md`. This prevents an SDK
from encoding unstable assumptions and allows harness feasibility to shape the
standard.

## Risks / Trade-offs

- [Standard overfits Python] → Keep behavior contracts language-neutral and treat Python entry points as one adapter mechanism.
- [Plugin authors expect ALLOW authority] → State advisory semantics and host precedence normatively.
- [In-process timeout is mistaken for isolation] → Make trust metadata and refusal behavior explicit.
- [Premature schema freeze] → Version manifests and keep the initial capability vocabulary deliberately small.
- [Cross-harness semantic mismatch] → Require adapter mapping and conformance before compatibility claims.

## Migration Plan

1. Add contract documentation and tests around the existing registry without changing safety authority.
2. Exercise manifest and failure cases in the current host.
3. Draft and review adapter mappings for Hermes Agent and OpenCode as design artifacts only.
4. Review isolation and version-negotiation gaps and record explicit refusal behavior.
5. Propose SDK extraction only as a later, separate change once the checklist in `adapter-mappings.md` passes.
