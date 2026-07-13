# Threat Model

This threat model focuses on publication-safe documentation for a real mobile-to-home geofence reporting system.

## Assets

- geofence event authenticity
- shortcut tokens and request headers
- WireGuard private keys and peer configuration
- TLS certificate and ACME account material
- public relay service configuration
- public relay durability queue
- home-side event database and logs
- derived LAN projections
- environmental enrichment state
- raw doorway observations
- precise location data
- home LAN addressing and service names

## Adversaries

- unauthenticated internet clients probing the public relay
- attackers with access to leaked repository contents
- passive observers of public documentation
- malware or unauthorized users on a node
- accidental disclosure through screenshots, logs, commits, or backups

## Primary Risks

### Token Replay or Forgery

If the webhook token or expected header format is published, an attacker may be able to generate false arrive or leave events.

Controls:

- keep live tokens outside version control
- publish only `.example` templates
- rotate tokens after import review if exposure is suspected
- scan for `X-Auth-Token`, bearer tokens, and similar header patterns

### Trusted LAN Exposure

Directly exposing trusted LAN target services would increase attack surface and
weaken the architecture's security value.

Controls:

- keep trusted LAN services behind NAT or trusted LAN boundaries
- relay accepted events over the private delivery path
- bind home services to loopback, LAN, or tunnel interfaces as appropriate
- avoid port-forwarding home automation services

The physical doorway signal is inside the protected environment. It should use a
narrow authenticated invocation into local processing, not a new public LAN
service.

### Queue Reordering Or Delivery Ambiguity

If accepted public relay events can be delivered out of order, downstream state
may describe a plausible but false history. Retry behavior is especially
sensitive because a temporarily failing head event must not be hidden by newer
successful deliveries.

Controls:

- commit accepted relay events to a SQLite durability queue before delivery
- deliver strictly by durable insertion order
- make a backing-off head row block newer rows
- preserve phone timestamps as event facts, not relay queue ordering authority
- keep retry/backoff behavior across the public/private trust boundary
- publish queue behavior without publishing queue contents

### Acceptance And Enrichment Coupling

If environmental enrichment is part of event acceptance, provider failure or
slow context lookup can block the primary security and state function: accepting
the event. If projections are updated before raw database acceptance, failures
can produce local state that has no authoritative raw event.

Controls:

- commit the raw event to SQLite before derived projection updates
- treat logs, state, and sequence material as projections
- make duplicate events duplicate-safe at the projection layer
- produce no projection changes after failed database acceptance
- run enrichment asynchronously after acceptance
- use oldest-first enrichment lifecycle states for retry and terminal failure
- describe environmental values as modeled regional context, not local sensor
  truth

### Location Disclosure

Raw coordinates, place labels, screenshots, and event logs can reveal sensitive movement patterns.

Controls:

- replace coordinates with neutral examples
- avoid real place names
- keep event databases and JSONL logs ignored
- review screenshots visually before publication

Installation photographs are also operational artifacts. Before publication,
use only a reviewed derivative with metadata stripped, a neutral filename, and
no residence identifiers, reflections, signage, network details, or materially
useful access-control detail.

### Infrastructure Fingerprinting

Publishing real public IP addresses, hostnames, local usernames, exact service paths, and certificate paths may make the live system easier to identify.

Controls:

- redact public IPs and hostnames
- use placeholder paths in published examples
- keep live `/etc` material out of direct imports
- document deployment mappings separately from secrets

### Runtime Artifact Leakage

Databases, logs, backups, certificates, and environment files can contain high-value sensitive data.

Controls:

- enforce deny-first `.gitignore` rules
- run `tools/audit/sanitize_scan.sh` before committing imports
- review staged changes before each commit
- keep backups and runtime state outside the repo

### Operational Verification Leakage

Live verification output can expose the deployment even when the architecture
language is safe. Command transcripts, service unit names, queue row counts,
provider responses, database paths, usernames, hostnames, and timestamps can
become an infrastructure map.

Controls:

- publish verification outcomes rather than raw output
- use role terms such as public relay, durability queue, protected LAN
  processing node, asynchronous enrichment, and recovery timer
- avoid service names, SSH aliases, account names, exact paths, exact event
  timestamps, database rows, and provider URLs
- review documentation diffs with the same standard as code and config imports

## Publication Standard

Public content should explain the security architecture and engineering tradeoffs without enabling direct targeting of the live deployment.
