# Doorway Observations

Doorway observations are physical boundary signals recorded at the doorway.
They complement phone-derived geofence transitions without replacing them or
silently manufacturing movement state.

![Doorway observation button installed beside the doorway boundary](../assets/photos/doorway-observation-installed.jpg)

The installed button, referred to publicly as Button A, is a quiet physical
observation point. It gives the environment a small procedural cue while keeping
observation separate from interpretation.

The implemented write path is deliberately narrow:

```text
physical doorway press
  -> home automation
  -> authenticated invocation
  -> narrow recorder
  -> raw doorway_events row
```

The implemented analytical path is later and read-only:

```text
raw doorway observations + raw geofence transitions
  -> bounded operator correlation
  -> matched or visibly unmatched result
```

The operator implementation is private. This public repository documents its
verified contract and sanitized presentation without claiming to contain the
full operational command.

## Current Status

Implemented and operationally verified:

- physical doorway observation at the doorway boundary
- authenticated invocation into trusted local processing
- narrow raw SQLite persistence
- read-only visibility for recent doorway observations
- arrival-side and departure-side bounded correlations
- non-reuse of matched observations
- visible unmatched anchors
- Unicode box tables for human-readable output
- unchanged machine-readable JSON output

Not implemented by these correlation commands:

- confidence scoring
- learned transition windows
- occupancy conclusions
- journey-level interpretation
- causal analysis

The distinction matters. The physical signal records that something happened at
the doorway. The geofence stream records what the mobile device reported. The
operator commands establish whether eligible records align within explicit
windows; they do not decide why the events happened.

## Raw Observation Contract

The raw doorway event is intentionally small and stable. It records facts that
can remain useful even as interpretation changes later.

Public-safe field shape:

| Field | Meaning | Kind | Privacy notes |
| --- | --- | --- | --- |
| `observed_at` | Time the physical press was observed | observed | public examples use synthetic timestamps |
| `observed_epoch` | Epoch representation of `observed_at` | observed/normalized | useful for ordering without exposing live values |
| `ingested_at` | Time the recorder persisted the row | system | public examples use synthetic timestamps |
| `device` | Stable public-safe device identity | observed/normalized | publish only abstract or example identifiers |
| `press_type` | Press classification from the button event | observed | correlation uses `single` only |
| `source` | Source class for the event | normalized | avoid automation account names or topology |
| `schema_version` | Raw observation schema version | metadata | supports later schema evolution |

The raw row deliberately does not include:

- arrival or departure
- journey direction
- occupancy state
- confidence
- geofence correlation
- causality

Meaning belongs to a derived layer. Keeping the raw record quiet allows the
correlation logic to evolve without rewriting history.

See the synthetic example in
[`examples/observations/doorway-press.example.json`](../examples/observations/doorway-press.example.json).

## Relationship To Geofence Observations

The two signal streams answer different questions.

```text
geofence observation:
  Which named-place boundary did the mobile device report crossing?

doorway observation:
  Was a single doorway-button press recorded, and when?
```

The physical observation is anchored to the doorway boundary. The phone-derived
event reports a named geofence transition from the mobile device. Neither signal
is silently promoted into the other.

The two implemented operator views describe opposite sides of the same flow:

```text
arrival:
  home-geofence arrival
    -> first subsequent single doorway-button observation

departure:
  single doorway-button observation
    -> first subsequent leave-home geofence event
```

Arrival windows start at a home arrival, inclusive, and end at the next home
arrival, exclusive. Departure windows start at a single button observation,
inclusive, and end at the next single button observation, exclusive. The first
eligible counterpart inside each window is selected. Window construction occurs
before the output limit is applied; matched counterparts are not reused.

Results are newest-first, with ID as a deterministic tiebreaker for equal
timestamps. See [Operator Interface](operator-interface.md) for the complete
command contract, limits, JSON behavior, and sanitized Unicode tables.

## Why Unmatched Rows Remain Visible

The system is designed for real use, not ritual-perfect input. A forgotten press
is missing evidence, not a license to invent evidence. A late or duplicate press
may fall outside the applicable window. A geofence event may likewise have no
eligible doorway counterpart.

Keeping unmatched anchors in the output gives the operator three useful
properties:

- gaps and timing mismatches remain inspectable
- one convenient event cannot be reused to complete several stories
- correlation quality is visible without a hidden confidence claim

Human-readable output renders unmatched fields with an em dash (`—`). JSON uses
`null`. Neither representation implies a negative movement claim; it means only
that the bounded rule found no eligible counterpart.

## Correlation Is Not Causality

A matched pair establishes temporal correlation under a documented selection
rule. It is not proof that the same person produced both observations, that the
button press caused a geofence transition, or that either record proves
occupancy.

The evidence ladder remains explicit:

```text
observed doorway event
  -> geofence transition
    -> bounded correlation
      -> possible inferred meaning
```

The first two are independent observations. The third is the implemented
read-only association. The fourth remains interpretation and is not asserted by
these commands.

## Security And Publication Boundary

The doorway signal originates inside the protected environment and is recorded
locally. No LAN service is exposed merely to support the button. The public
ingress boundary for phone-derived geofence events remains separate from the
protected processing node.

Public documentation may describe:

- physical doorway observation
- authenticated local invocation
- protected home-LAN processing
- narrow recorder
- local SQLite event storage
- read-only operator queries
- bounded correlation rules and sanitized output

Public documentation must not publish:

- operational credentials or automation account details
- deployed device identifiers or provider details
- private hostnames, IP addresses, usernames, paths, or database locations
- exact live timestamps, event IDs, rows, logs, or database counts
- residence identifiers, building details, or access-control details
- unreviewed installation photographs

Published installation photographs should be public-safe derivatives with
metadata stripped, neutral filenames, and no visible residence identifier,
signage, reflections, network details, or materially useful access-control
detail.
