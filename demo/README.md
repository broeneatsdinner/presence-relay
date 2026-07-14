# Presence Relay Local Demo

## Purpose

This demo proves the implemented Presence Relay event path with public-safe
fixture data and disposable local state.

## Implemented Path

```text
synthetic named-place events
  -> authenticated local webhook handler at /hook/presence
    -> local demo delivery adapter
      -> oldest unfinished queued row
        -> SQLite-first raw event acceptance
          -> derived place-state projections
            -> disposable presence.sqlite persistence
              -> existing viewer reader compatibility check
```

The local delivery adapter replaces the production SSH hop. It drains the
authenticated webhook queue one oldest unfinished row at a time and invokes the
trusted-side event script directly. The deterministic demo disables the
background enrichment trigger so local runs do not depend on timers, network
providers, or optional astronomy/weather libraries.

## Requirements

- bash
- python3
- curl
- sqlite3

No internet access, live mobile automation, private infrastructure, production
credentials, or private data are used.

## Run

```bash
./demo/bin/demo.sh
```

The demo uses the public Chicago fixture:

- `leave sheridan-plaza`
- `arrive kilmer-elementary`

It uses `presence-relay-demo-token`, a deterministic non-secret demo credential.

## Cleanup

```bash
./demo/bin/demo.sh --clean
```

Demo-generated state lives only under `demo/tmp/`. The default run leaves the
disposable SQLite database there for inspection; `--clean` removes it.

## Expected Outcome

The terminal output shows two persisted place transitions:

```text
leave   sheridan-plaza     sheridan-plaza   unnamed
arrive  kilmer-elementary  unnamed          kilmer-elementary
```

It also verifies that the existing viewer server reader can fetch the resulting
SQLite rows.

Sanitized examples of the separate private operator interface are available in
[`demo/transcripts/`](transcripts/README.md). Those Unicode tables are
presentation fixtures; this deterministic demo does not generate them or contain
the private `bin/presence` implementation.

## Boundary

This demo does model:

- authenticated local ingress
- durable relay queueing before delivery
- strict oldest-row local delivery
- SQLite-first raw acceptance
- duplicate-safe projection behavior for accepted rows
- viewer compatibility with the accepted-event table

This demo does not run or simulate roadmap functionality:

- route sessions
- route sampling
- historical baselines
- context correlation
- inference
- confidence scoring
- recommendations

It also does not run the privately implemented doorway/geofence correlation
commands. Their public transcripts document the verified interface without
claiming that private runtime logic or data is included here.

It also does not run the production asynchronous enrichment trigger. The public
implementation contains the sanitized one-event enrichment worker; the demo
keeps it disabled for deterministic offline execution.
