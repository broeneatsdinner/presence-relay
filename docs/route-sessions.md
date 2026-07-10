# Route Sessions

Route sessions are roadmap work. They are not implemented yet.

This document defines the public-safe contract for bounded movement windows
inferred from place-boundary events. Current event semantics are defined in
[Place State](place-state.md).

## Purpose

A route session represents a bounded movement window:

```text
leave <named place>
  -> open route session

arrive <named place>
  -> complete matching open route session

no matching named arrival before configured limit
  -> expire route session
```

Route sessions should support privacy-aware duration analysis, future route
samples, and contextual inference without publishing raw personal movement
history.

## Non-Goals

This pass does not implement:

- production database tables
- route-session builders
- route sampling
- context adapters
- prediction logic
- custom iOS collection

Public examples must use synthetic event IDs, timestamps, and conditions. Route
geometry may use the public-safe Chicago reference fixture documented in
[Chicago Reference Scenario](chicago-reference-scenario.md).

## Source Events

Route-session logic should rely on:

- `event`
- `place`
- `previous_place`
- `current_place`
- event IDs
- event timestamps

It should not rely primarily on legacy compatibility fields:

- `previous_status`
- `new_status`

`unnamed` is a legitimate observed place-state. It is not the same as a missing
route-session endpoint. If no matching arrival was observed, endpoint fields
such as `end_event_id`, `ended_at`, `to_place`, and `route_key` should remain
`null`.

## Lifecycle

Use a minimal lifecycle:

- `open`: a named-place departure has opened a route session and no terminal
  condition has occurred.
- `completed`: a matching named-place arrival closed the session.
- `expired`: no matching named-place arrival occurred before a configured time
  limit.
- `ambiguous`: event ordering or duplicate/retry behavior prevents a single
  reliable interpretation.

Do not use `partial` in the initial vocabulary. Its likely meanings overlap
with `open`, `expired`, or `ambiguous`.

## Edge Cases

Arrival with no open session:

- Do not fabricate a departure.
- Record or report an anomaly such as `arrival_without_open_session`.
- A future implementation may ignore it for v1 rebuilding.

Repeated departure:

- If a session is already open, mark the prior session `ambiguous` or expire it
  according to configured policy, then open a new session if appropriate.

Repeated arrival:

- If a session is already completed, treat the later arrival as duplicate,
  retry noise, or an anomaly depending on event IDs and timestamps.

Events received out of order:

- Rebuilders should sort by event timestamp and stable ID.
- If ordering remains impossible, mark the affected session `ambiguous`.

Retry or duplicate events:

- Prefer event IDs and existing raw uniqueness behavior over payload copying.
- Do not create multiple sessions from the same boundary event.

Missing timestamps:

- Do not infer precise duration.
- Mark the session `ambiguous` if pairing cannot be trusted.

Session timeout:

- Expire an `open` session when no named-place arrival occurs before the
  configured limit.

Arrival back at origin:

- A route can start and end at the same named place.
- `route_key` may be `origin-example-to-origin-example` only when both
  endpoints are observed.

Manual tests mixed with real events:

- Keep test tagging as a future concern.
- Do not silently fold manual tests into strong baseline claims.

Missing coordinates:

- A session can exist without coordinates because place-boundary events are the
  primary source.
- Route classification and geometry comparison may be unavailable.

`changed = 0`:

- Ignore for initial route-session pairing unless a future policy explicitly
  needs retry/noise analysis.

`unnamed` events:

- Do not open or complete route sessions from `unnamed` endpoints in the first
  implementation.
- They may become anomalies or context for later analysis.

Multiple devices:

- Reserve design space for future device/source identity, but do not implement
  multi-device support yet.

## Field Contract

Initial implementation fields:

| Field | Meaning | Source | Kind | Null behavior | Privacy notes |
| --- | --- | --- | --- | --- | --- |
| `id` | Route-session primary key | generated | lifecycle metadata | never null | no sensitive value by itself |
| `status` | `open`, `completed`, `expired`, or `ambiguous` | derived | lifecycle metadata | never null | public-safe if detached from real labels |
| `start_event_id` | Event that opened the session | event row | observed link | never null | prefer linking to event ID over copying payload |
| `end_event_id` | Event that closed the session | event row | observed link | null until observed | null means no endpoint observation |
| `from_place` | Named departure place | start event | observed/normalized | never null for valid sessions | use slug, not real address |
| `to_place` | Named arrival place | end event | observed/normalized | null until observed | do not use `unnamed` for missing endpoint |
| `started_at` | Start event timestamp | start event | observed | never null if source event valid | public examples use fake timestamps |
| `ended_at` | End event timestamp | end event | observed | null until observed | avoid exact private timestamps in public docs |
| `duration_seconds` | Elapsed time between endpoints | timestamps | derived | null until both timestamps exist | suitable for aggregate summaries |
| `route_key` | Stable `from_place-to_place` key | endpoints | derived | null until both endpoints exist | public-safe with sanitized or reference slugs |
| `sample_count` | Number of associated route samples | samples | derived | `0` if none | publish aggregates, not traces |
| `created_at` | Session record creation time | system | lifecycle metadata | never null | implementation detail |
| `updated_at` | Session record update time | system | lifecycle metadata | never null | implementation detail |
| `pairing_version` | Pairing rule version | implementation | lifecycle metadata | never null | supports idempotent rebuilds |
| `anomaly_code` | Machine-readable anomaly | pairing logic | derived | null when normal | avoid sensitive prose |

Later-phase fields:

| Field | Why later |
| --- | --- |
| `opened_at` / `closed_at` / `expired_at` | Useful audit metadata but not required to model route facts. |
| `direction` | Often subjective unless explicitly configured from place pairs. |
| `inference_version` | Belongs with inference outputs, not initial route-session pairing. |
| `anomaly_detail` | Can leak operational context; keep out of v1 or sanitize heavily. |

Avoid copying raw payloads, raw coordinates, or full event rows into route
sessions. Keep the model rebuildable from event IDs and deterministic pairing
rules.

## Public-Safe Example

See:

- `examples/route-sessions/route-session-complete.example.json`
- `examples/route-sessions/route-session-expired.example.json`
- `examples/route-sessions/events-to-session.example.md`

## Relationship To Later Layers

Route sessions are the bridge between place-boundary events and later analysis:

```text
named-place boundary events
  -> route session
  -> optional route samples
  -> historical duration baseline
  -> public event context
  -> proactive inference
```

Project principle:

```text
Predict. Not react.
```

## Relationship To Doorway Observations

Doorway observations are an independent physical signal, not a route-session
endpoint by themselves.

They may later help classify or explain route sessions:

```text
doorway press
  -> leave-home geofence transition
  -> open route session

arrive-home geofence transition
  -> doorway press
  -> complete route session with physical-boundary support
```

That correlation is future work. Initial route-session pairing should continue
to rely on phone-derived named-place boundary events. A doorway press should not
silently create a geofence transition, open a route session, close a route
session, or imply occupancy state.

Future correlation rules should use bounded time windows, avoid reusing a single
doorway observation for multiple transitions, tolerate late or duplicate
presses, and preserve uncertainty with classifications such as:

```text
matched
no_plausible_press
ambiguous
outside_expected_window
```

See [Doorway Observations](doorway-observations.md).
