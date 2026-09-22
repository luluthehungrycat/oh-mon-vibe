## ADDED Requirements

### Requirement: Plugin analyzers are advisory and ambiguity asks

A plugin command analyzer MUST return a typed `allow`, `ask`, or `deny`
classification with a reason. Host deterministic policy and user rules remain
authoritative.

#### Scenario: Clearly safe command is analyzed

- **WHEN** the command passes deterministic guardrails, stays within permitted paths, and the analyzer returns `allow`
- **THEN** OMV MAY auto-approve it without an extra user prompt

#### Scenario: Ambiguous command is analyzed

- **WHEN** the command is not deterministically safe and the analyzer cannot establish a safe classification
- **THEN** OMV SHALL request human approval and SHALL not auto-allow it

#### Scenario: Destructive command is analyzed

- **WHEN** the command matches a deterministic dangerous-command rule
- **THEN** OMV SHALL deny it regardless of plugin output or user `always` rules

### Requirement: Users control granular plugin permissions

OMV SHALL support explicit per-plugin, capability, action, or command rules
with `always`, `ask`, and `deny` outcomes. The default for side-effecting plugin
actions SHALL be `ask`.

#### Scenario: User explicitly denies a plugin action

- **WHEN** a plugin requests an action matching an explicit `deny` rule
- **THEN** OMV SHALL refuse the action without invoking the plugin callback

#### Scenario: User explicitly always-allows a safe action

- **WHEN** a plugin requests an action matching an explicit `always` rule and no core safeguard requires approval or denial
- **THEN** OMV SHALL execute it without an additional prompt

#### Scenario: Plugin advisory allow conflicts with a required approval

- **WHEN** a plugin returns `allow` but path, sensitivity, sandbox, or human policy requires approval
- **THEN** OMV SHALL preserve the required approval
