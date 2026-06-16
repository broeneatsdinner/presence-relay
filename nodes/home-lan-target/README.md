# Home LAN Target

This directory is the import target for the trusted LAN-side automation node.

Expected imported contents:

- `event.sh` or equivalent event receiver/dispatcher
- `ingest_enrich.py` or equivalent ingest and enrichment logic
- local web viewer assets and service definitions
- sanitized environment templates and deployment notes

Do not import runtime databases, logs, raw geofence events, real coordinates, real device identifiers, private hostnames, tokens, or local absolute paths without sanitization.
