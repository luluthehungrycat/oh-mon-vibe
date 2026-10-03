## Purpose

Reduce repetitive approvals for commands that can safely execute inside a restricted Linux sandbox while preserving project work, explicit fallback controls, and human oversight when sandboxing is unavailable or ambiguous.

## ADDED Requirements

### Requirement: Sandboxing is capability-detected
Oh My Vibe SHALL expose the selected sandbox backend, version or availability status, and effective capabilities before executing a sandboxed command.

#### Scenario: Configured backend is unavailable
- **WHEN** sandbox mode is enabled but the configured backend is missing or unusable
- **THEN** Oh My Vibe SHALL report the unavailable capability and SHALL follow the configured fallback policy rather than silently claiming sandboxed execution

### Requirement: Sandboxed execution preserves the worktree
A sandboxed Bash execution SHALL use the current project worktree as its writable working directory, SHALL prevent access to unrelated host files by default, and SHALL apply the configured network policy.

#### Scenario: Network policy is explicit
- **WHEN** sandboxed Bash execution is configured with `network = "none"`
- **THEN** the selected backend SHALL disable network access and report `network_isolation = true`
- **WHEN** sandboxed Bash execution is configured with `network = "host"`
- **THEN** the selected backend SHALL omit network isolation and report `network_isolation = false`
- **WHEN** configuration specifies `network = "project"`
- **THEN** configuration validation SHALL reject it because no current backend provides a project-scoped network primitive

#### Scenario: A routine project command runs
- **WHEN** a command is eligible for sandboxing and the backend is available
- **THEN** the command SHALL execute in the sandbox with the project worktree as its working directory and the result SHALL identify the execution as sandboxed

### Requirement: Sandbox failure is fail-closed by default
Oh My Vibe SHALL distinguish command failure from sandbox startup failure. A sandbox startup failure SHALL require the configured fallback behavior, and the default fallback SHALL request human approval before unsandboxed execution.

#### Scenario: Sandbox cannot start
- **WHEN** the backend fails before the command starts
- **THEN** Oh My Vibe SHALL not automatically run the command unsandboxed unless an explicit configuration permits that behavior

### Requirement: Dangerous commands retain core guardrails
Sandboxing SHALL NOT convert a core-denied command into an allowed command. Commands involving sensitive operations, interactive shells, or configured deny patterns SHALL remain denied or require human approval regardless of sandbox availability.

#### Scenario: Denied command is requested
- **WHEN** a command matches a built-in deny rule
- **THEN** Oh My Vibe SHALL deny it without attempting sandbox execution
