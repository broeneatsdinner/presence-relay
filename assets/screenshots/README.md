# Screenshot Proofs

These PNGs are sanitized visual proofs for the public Presence Relay repository.
They use only disposable demo state and public Chicago fixture data.

## Files

- `terminal-demo.png` shows the deterministic local demo output. It proves that
  the demo processed `leave sheridan-plaza` and `arrive kilmer-elementary`,
  persisted the expected place transitions, and completed successfully.
- `local-viewer.png` shows viewer-ready rows read through the existing local
  viewer data path. It proves that the disposable SQLite database contains the
  two public fixture events and canonical place-state transitions.

`architecture-overview.png` is intentionally not included. The architecture
diagrams are Mermaid source files rendered by GitHub; no clean local Mermaid
PNG renderer was available without adding a dependency or using an online tool.

## Generation

The terminal image was rendered from the actual output of:

```bash
./demo/bin/demo.sh
```

The viewer image was generated after running the demo, starting the existing
viewer against the disposable demo database on `127.0.0.1`, and reading its
local `/api/events` data. The image excludes path-bearing page metadata,
browser chrome, non-essential columns, and all desktop context.

## Publication Safety

The screenshots deliberately exclude:

- shell prompts, terminal titles with private context, usernames, hostnames, and
  working directories
- browser chrome, bookmarks, history, profile identity, extensions, and desktop
  content
- production credentials, live infrastructure, private domains, and private
  network details
- live geolocation history, private route data, and production databases

Only public fixture values appear:

- `sheridan-plaza`
- `kilmer-elementary`

## Regeneration

Regenerate screenshots from a clean tree by running the demo with disposable
state, capturing only the sanitized output/table, stripping metadata, and then
running:

```bash
./demo/bin/demo.sh --clean
tools/audit/sanitize_scan.sh
tools/audit/public_release_check.sh
tools/audit/public_release_check.sh --strict
```

Terminal-video recording is a separate future workflow and is not represented
by these static screenshots.
