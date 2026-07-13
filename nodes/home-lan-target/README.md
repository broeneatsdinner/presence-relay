# Home LAN Target

This directory is the import target for the trusted LAN-side automation node.

Expected imported contents:

- `event.sh` or equivalent event receiver/dispatcher
- `ingest_enrich.py` or equivalent ingest and enrichment logic
- local web viewer assets and service definitions
- sanitized environment templates and deployment notes

The public-safe implementation in this tree models the current protected-LAN
contract without live configuration:

- `event.sh` validates the invocation shape and delegates accepted event
  persistence to SQLite before compatibility projections are emitted.
- `ingest_enrich.py` owns the accepted raw event table, duplicate-safe
  projection metadata, and a one-event oldest-first enrichment lifecycle.
- log, state, and sequence files are compatibility projections, not the
  authoritative record.
- enrichment is best-effort and asynchronous from the event entrypoint; public
  demo runs disable that trigger for deterministic offline execution.

Do not import runtime databases, logs, raw geofence events, real coordinates, real device identifiers, private hostnames, tokens, or local absolute paths without sanitization.
