# Place State

This document is the canonical public-safe description of the current
presence-relay event and place-state model.

## Current Status

The place-based state model is implemented, deployed, and verified.

Verified behavior:

- iPhone Shortcuts send named-place boundary events.
- The public relay accepts authenticated webhooks and relays accepted events to
  the trusted LAN target.
- The trusted LAN target logs, ingests, enriches, stores, and displays events.
- `previous_place` and `current_place` are recorded for new ingested events.

Public-safe verification examples:

```text
leave home:
  previous_place = home
  current_place  = unnamed

arrive home:
  previous_place = unnamed
  current_place  = home
```

The implementation was tested with disposable local data and verified with real
authenticated iPhone boundary events. Public documentation must not include real
coordinates, exact private timestamps, live hostnames, IP addresses, usernames,
tokens, raw rows, private paths, or exact private locations.

## Event Model

Payloads use two separate dimensions:

- `event`: `arrive` or `leave`
- `place`: a named lowercase slug or `unnamed`

Examples of named place slugs:

- `home`
- `camp`
- `school`
- `office`
- `gym`

Do not encode the place into the event name.

Prefer:

```text
event = arrive
place = camp
```

Do not use:

```text
event = arrive-camp
```

Named geofences can be added without changing the schema or state vocabulary.

## Place-State Rules

All current state vocabulary uses places.

`unnamed` is intentional. It means the device is not currently associated with a
named geofence/place, or the observed location is not semantically labeled. It
does not mean the location is unknown, and it should not be replaced with
`away`, `outside`, or `inside` in the place-state model.

Rules:

```text
arrive <place>:
  previous_place = unnamed
  current_place  = <place>

leave <place>:
  previous_place = <place>
  current_place  = unnamed
```

Examples:

```text
leave home:
  previous_place = home
  current_place  = unnamed

arrive camp:
  previous_place = unnamed
  current_place  = camp
```

## Legacy Compatibility Fields

The legacy fields remain for backward compatibility:

- `previous_status`
- `new_status`

Those fields may contain older home/away state-machine values such as `home`,
`away`, and `unknown`. They are retained so older views and existing operational
logic keep working, but new design and future route logic should not rely on
them as the primary state model.

## Historical Rows

Existing historical database rows were intentionally not rewritten.

Rows ingested before the new place-state columns existed may have:

```text
previous_place = unnamed
current_place  = unnamed
```

That is expected migration behavior. It preserves historical data and avoids
inventing transitions after the fact.

## Design Boundary

Implemented now:

- authenticated public webhook ingress
- public relay / trusted LAN target separation
- `event + place` payloads
- `previous_place + current_place` for new ingested events
- local event enrichment and viewer display

Roadmap only:

- `route_sessions`
- route samples
- event-context prediction
- public event correlation
- congestion prediction
- custom iOS route collector

The intended future direction is:

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
