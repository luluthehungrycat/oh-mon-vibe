# Conformance fixture matrix

These fixtures define the evidence required by the plugin contract before an
adapter or SDK can claim compatibility. They are host-side fixture contracts,
not a claim that Hermes Agent or OpenCode already implements them.

## Manifest and discovery

| ID | Setup | Expected result |
| --- | --- | --- |
| `manifest-valid-analyzer` | Enable an analyzer manifest with API `1` and capability `analyzer`. | Registration succeeds with the manifest retained. |
| `manifest-disabled` | Install an entry point not present in `enabled_plugins`. | The entry point is not imported or executed. |
| `manifest-unknown-api` | Enable a manifest with an API other than `1`. | Registration is rejected with `manifest_rejected`; no executable behavior is registered. |
| `manifest-unknown-capability` | Enable a manifest declaring a capability outside the vocabulary. | Registration is rejected with `manifest_rejected`. |
| `manifest-kind-mismatch` | Declare `sandbox_backend` under kind `analyzer`. | Registration is rejected with `manifest_rejected`. |
| `manifest-untrusted` | Request `process_isolated` trust without an isolation runtime. | Registration is rejected; the plugin is not labeled isolated. |
| `registration-failure` | A valid plugin raises from `register()`. | `registration_failed` is recorded; built-ins and unrelated plugins remain usable. |

## Analyzer authority and failure

| ID | Setup | Expected result |
| --- | --- | --- |
| `advisory-allow-core-deny` | Analyzer returns `allow` for a deterministic deny. | Core denial remains authoritative. |
| `advisory-allow-human-deny` | Analyzer returns `allow` after explicit human denial. | Human denial remains authoritative. |
| `advisory-allow-sandbox` | Analyzer returns `allow` for a command requiring sandbox execution. | Sandbox requirement is preserved. |
| `analyzer-timeout` | Analyzer exceeds the configured timeout. | The result becomes `ask` with timeout diagnostics; no automatic approval occurs. |
| `analyzer-exception` | Analyzer raises during evaluation. | The result becomes `ask` with failure diagnostics; deterministic policy continues. |
| `analyzer-malformed` | Analyzer returns a value other than `CommandDecision`. | The result becomes `ask`; malformed output cannot approve execution. |

## Sandbox evidence

| ID | Setup | Expected result |
| --- | --- | --- |
| `sandbox-none-network` | Use the built-in backend with `network = "none"`. | Network isolation is explicit and capability metadata reports `true`. |
| `sandbox-host-network` | Use the built-in backend with `network = "host"`. | Isolation is omitted and capability metadata reports `false`. |
| `sandbox-unavailable` | Configure a missing backend. | Availability is false or absent; configured fallback policy is applied. |
| `sandbox-startup-failure` | Backend fails before command start. | Startup failure is distinct from command failure and does not silently bypass fallback policy. |
| `sandbox-workdir` | Build backend argv for a project worktree. | Writable-workdir evidence identifies only the configured worktree as writable. |

## Adapter fixture obligations

Hermes Agent and OpenCode adapters MUST map every fixture ID to a native
installation, discovery, invocation, diagnostic, or refusal test. If a native
host cannot represent a fixture's expected result, the adapter MUST reject the
capability rather than weakening the host invariant.
