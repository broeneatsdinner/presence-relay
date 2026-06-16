# Events to Route Session Example

This example uses the public Chicago reference fixture with synthetic event IDs
and timestamps.

It demonstrates planned future behavior: individual place-boundary events can
become a bounded route session without exposing raw personal location history.

Route-session tables and builders are not implemented yet.

## Input events

| id | event | place | previous_place | current_place | changed | ts_iso | label |
|---:|---|---|---|---|---:|---|---|
| 1001 | leave | sheridan-plaza | sheridan-plaza | unnamed | 1 | 2026-02-27T16:45:00-06:00 | sheridan-plaza |
| 1002 | arrive | kilmer-elementary | unnamed | kilmer-elementary | 1 | 2026-02-27T17:16:00-06:00 | kilmer-elementary |

## Pairing rule

The session builder reads changed events in timestamp order.

A `leave <named place>` event opens a route session.

The next valid `arrive <named place>` event closes the route session.

`unnamed` is a legitimate observed place-state. A missing route-session endpoint
is represented with `null`, not `unnamed`.

## Output session

| field | value |
|---|---|
| status | completed |
| route_key | sheridan-plaza-to-kilmer-elementary |
| start_event_id | 1001 |
| end_event_id | 1002 |
| from_place | sheridan-plaza |
| to_place | kilmer-elementary |
| started_at | 2026-02-27T16:45:00-06:00 |
| ended_at | 2026-02-27T17:16:00-06:00 |
| duration_seconds | 1860 |

## Public-safety notes

This example does not include:

- private coordinates
- real named-place labels
- raw route traces
- live infrastructure names
- private family, school, camp, or appointment names
- authentication tokens
