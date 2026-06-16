# Presence Relay Local Demo

## Purpose

This demo proves the implemented Presence Relay event path with public-safe
fixture data and disposable local state.

## Implemented Path

```text
synthetic named-place events
  -> authenticated local webhook handler
    -> local demo delivery adapter
      -> real trusted-side event processing
        -> real place-state transitions
          -> real ingestion and enrichment code
            -> disposable SQLite persistence
              -> existing viewer reader compatibility check
```

The local delivery adapter replaces the production SSH hop. It drains the
authenticated webhook queue and invokes the trusted-side event script directly.

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

## Boundary

This demo does not run or simulate roadmap functionality:

- route sessions
- route sampling
- historical baselines
- context correlation
- inference
- confidence scoring
- recommendations
