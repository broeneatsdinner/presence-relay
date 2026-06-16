# Route Data Model

This document defines future route samples and synthetic route geometry. These
contracts are roadmap-only and are not implemented yet.

## Route Samples

A route sample is an optional observation associated with an open route session.
A route session can exist without samples.

A sample is not a semantic place. It is a measured point-in-time observation.

Minimal future contract:

| Field | Meaning | Source | Kind | Null behavior | Privacy notes |
| --- | --- | --- | --- | --- | --- |
| `id` | Sample primary key | generated | metadata | never null | no sensitive value by itself |
| `route_session_id` | Open session the sample belongs to | session builder | derived link | never null after association | prevents unbounded tracking records |
| `observed_at` | Time the device observed the sample | collector | observed | never null for accepted samples | public examples use synthetic timestamps |
| `latitude` | Sample latitude | collector | observed | never null for accepted samples | raw private geometry is operational data |
| `longitude` | Sample longitude | collector | observed | never null for accepted samples | raw private geometry is operational data |
| `horizontal_accuracy_m` | Reported accuracy in meters | collector | observed | nullable if unavailable | useful for filtering noisy points |
| `source` | Collector/source label | collector | normalized | never null | avoid device names in public examples |

Optional later fields:

| Field | Use |
| --- | --- |
| `altitude_m` | Useful only if elevation changes matter. |
| `speed_mps` | Useful for route-quality checks but can be noisy. |
| `course_degrees` | Useful for corridor matching and direction checks. |
| `is_simulated` | Useful for test fixtures and simulator-generated samples. |
| `collection_state` | Useful for lifecycle states such as active, paused, or delayed. |
| `sequence_number` | Useful when collector ordering is more reliable than timestamps. |

Late-arriving samples need explicit handling. A future implementation should
either associate them to an already-open session by timestamp and policy or
reject them as late/unpaired. Do not silently attach samples outside the
session window.

## Privacy Controls

Raw private route samples are operational data.

Public examples may use public reference geometry, but sample observations
should remain synthetic unless intentionally published from a public fixture.
Public summaries should prefer:

- route classification
- aggregate distance or duration
- point-to-corridor statistics
- reduced precision
- retention-limited summaries

Precision reduction and retention limits are future controls. Source
provenance must not become a hidden personal-data channel.

## Reference Geometry

Reference route geometry is used before a mobile route collector exists and for
public examples/tests after it exists.

The public fixture uses a geographically unrelated Chicago North Side scenario:

- Origin endpoint: `sheridan-plaza`
- Destination endpoint: `kilmer-elementary`
- Context landmark: `loyola-lake-shore-campus`
- Context landmark: `gentile-arena`
- Routes: `sheridan-corridor`, `ashland-clark-alternate`

The university campus and arena are along or adjacent to the primary reference
corridor. They can affect route conditions through scheduled-event or venue
context without becoming route endpoints.

See [Chicago Reference Scenario](chicago-reference-scenario.md) for fixture
purpose, addresses, coordinate sources, and OPSEC boundaries.

Reference geometry can prove contracts for:

- route/session linking
- point-to-corridor distance
- route classification
- alternate-route comparison
- event venue proximity
- public examples and tests

No spatial computation is implemented in this pass.

The Chicago fixture separates real/public and synthetic layers:

```text
real/public:
  Chicago reference landmarks
  OSRM-derived route geometry
  sample point positions selected along that geometry

synthetic:
  route-session IDs
  timestamps
  accuracy values
  event history
  observed durations
  context conditions
  baseline statistics
  inference results
```

OSRM duration is a public routing-reference estimate without live traffic.
Route-session duration is a synthetic observed example. Baseline and inference
durations are synthetic analytical examples.

Example files:

- `examples/routes/chicago-loyola-places.geojson.example.json`
- `examples/routes/chicago-loyola-routes.geojson.example.json`
- `examples/routes/chicago-loyola-samples.example.json`
