# Diagram Sources

These files are the editable source diagrams for the public Presence Relay
documentation. They are kept as Mermaid so the architecture can be reviewed as
plain text, rendered by GitHub, and revised without binary design assets.

## Diagrams

- `trust-boundary-architecture.mmd` shows the implemented production trust
  boundary: mobile event source, public relay validation and queueing, private
  delivery boundary, and trusted LAN processing/storage/viewing.
- `place-state-transitions.mmd` shows the canonical place-state semantics:
  `arrive` moves from `unnamed` to a named place, and `leave` moves from a named
  place to `unnamed`.
- `local-demo-flow.mmd` shows exactly what the deterministic local demo runs:
  public synthetic fixtures, real local webhook authentication, a demo-only
  delivery adapter, real trusted-side processing, disposable SQLite state, and
  existing viewer-reader verification.

## Implemented Versus Demo Boundary

The production diagram shows the real trust-boundary architecture without
revealing topology, hostnames, addresses, usernames, or credentials. The local
demo diagram is separate because it intentionally replaces the production
private delivery hop with a clearly marked local adapter. The demo does not
simulate or claim the production SSH/private-delivery transport.

Roadmap work such as route sessions, historical baselines, context correlation,
inference, confidence scoring, and recommendations is intentionally absent from
these diagrams unless explicitly identified as out of scope in prose.

## Rendered Assets

Future SVGs, presentation images, or video assets should derive from these
Mermaid sources. Rendered assets should be treated as generated documentation
and reviewed for metadata, private identifiers, accidental topology details,
and visual disclosure before publication.
