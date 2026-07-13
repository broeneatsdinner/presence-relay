# Architecture

This system reports mobile place-boundary events into a trusted LAN environment
without exposing LAN services directly to the public internet.

## High-Level Flow

```text
iPhone Shortcuts / Personal Automations
	|
	| authenticated HTTPS webhook
	v
Public relay
	|
	| durable strict-FIFO queue and private-side delivery path
	v
Trusted LAN target
	|
	| SQLite-first acceptance, projections, asynchronous enrichment, and viewer
	v
Trusted LAN resources
```

The public relay accepts authenticated webhook requests, validates the narrow
event payload, and commits each accepted event to a SQLite durability queue
before attempting delivery. Relay delivery is strict FIFO by durable insertion
order. The worker selects the oldest unfinished row; if that head row is in
backoff, newer rows wait behind it rather than leapfrogging. Phone-provided
timestamps are preserved as event facts, but they do not determine relay queue
order.

Delivery retries cross the public/private trust boundary through the configured
private-side path. Backoff is a failure-isolation mechanism: accepted events are
durable on the public relay while the protected LAN side is unavailable, and
newer events do not hide or reorder an older delivery problem.

## Current Event Semantics

The current phone-derived geofence model uses separate `event` and `place`
dimensions:

- `event`: `arrive` or `leave`
- `place`: named lowercase slug or `unnamed`

Place-state fields use only place vocabulary:

- `previous_place`
- `current_place`

See [Place State](place-state.md) for the canonical model and migration notes.

The system also records physical doorway observations at the doorway boundary.
Those observations are intentionally raw facts, not geofence transitions:

```text
physical doorway press
	|
	| home automation and authenticated invocation
	v
narrow recorder
	|
	v
local SQLite raw observation
```

A doorway observation asks whether the button was pressed and when. It does not
infer arrival, departure, journey direction, occupancy, confidence, or causality.
Later correlation with phone-derived geofence transitions is designed but not
implemented.

See [Doorway Observations](doorway-observations.md).

## Protected LAN Acceptance

The protected LAN processing node treats SQLite as authoritative for accepted
raw events. The raw event record is committed before downstream material is
updated.

Implemented acceptance behavior:

- raw event acceptance is SQLite-first
- log, state, and sequence material are derived projections
- duplicate events do not duplicate projections
- failed database acceptance produces no projection changes
- environmental enrichment is not part of the raw acceptance transaction

This keeps the accepted event record separate from local presentation,
compatibility fields, and operational conveniences. It also gives later schema
evolution a stable base: projections can be regenerated or extended without
redefining what was originally accepted.

## Asynchronous Enrichment

Environmental enrichment runs after raw acceptance and projection updates. The
acceptance path issues a nonblocking best-effort trigger, and a recovery timer
handles backlog, missed triggers, reboot recovery, and retry work. Mobile
acknowledgment and raw event acceptance do not wait for enrichment.

The enrichment worker processes exactly one oldest unfinished event at a time.
Lifecycle states are:

- `pending`
- `retry`
- `complete`
- `terminal`

Selection is by accepted event row order, not by current weather or wall-clock
conditions at processing time. Enrichment uses the accepted event's historical
timestamp and stored coordinates, preserves the normalized UTC environmental
hour, calculates astronomy for the historical event time, and selects weather
for the corresponding UTC hour.

Environmental enrichment is modeled regional context. It is not doorway-local
sensor truth, not live current weather, and not part of the initial event
acceptance transaction. Raw numeric values are preserved separately from
descriptive labels.

## Trust Boundaries

### Mobile Device Boundary

The iPhone is an event source. It can initiate `arrive` and `leave` shortcut
requests for named places, but it should not receive privileged access to
home-side services through this repository's public surfaces.

Sensitive material:

- shortcut authentication token
- location trigger definitions
- device identifiers
- screenshots of Shortcut configuration

### Public Relay Boundary

The public relay is internet reachable and should be treated as exposed
infrastructure. It terminates the public webhook path, validates incoming
requests, durably queues accepted events, and relays them through the private
delivery path in strict FIFO order.

Sensitive material:

- public IP address and DNS records
- webhook token
- service account details
- reverse proxy configuration
- TLS certificate paths and account material
- WireGuard peer configuration

### Private Delivery Boundary

The private delivery path is the controlled path between public relay and
trusted LAN target. It should reduce exposure of the LAN by avoiding direct
inbound access from the internet.

Public diagrams use the generic term `private-side delivery path`. Deployed
implementations may use mechanisms such as private VPN reachability and
authenticated SSH. Exact peer configuration, addressing, hostnames, and
credentials remain private.

Sensitive material:

- peer addresses
- private keys
- allowed IPs
- endpoint details

### Trusted LAN Boundary

The trusted LAN target receives validated events and performs local logging,
enrichment, storage, display, or automation. It should remain reachable only
from trusted local interfaces or the private delivery path.

For phone-derived events, SQLite is the authoritative accepted-event store.
Derived files, sequence counters, compatibility state, and viewer-facing data
are projections after database acceptance. Enrichment is asynchronous so
provider failure, retry delay, or backlog does not block event acceptance.

The physical doorway signal originates inside this protected environment. It
uses a narrow authenticated invocation into local processing and writes a raw
observation locally; no LAN service is exposed to the public internet merely to
support the button.

Sensitive material:

- raw event database
- local logs
- local automation names
- physical automation configuration
- viewer URLs
- private LAN IP addresses
- enriched coordinates or place labels

## Diagrams

The public trust-boundary, place-state, and local-demo diagrams are maintained
as Mermaid source under `docs/diagrams/` and rendered in
[Architecture Diagrams](architecture-diagrams.md).

The production diagram shows the trust boundaries above without revealing real
IP addresses, hostnames, coordinates, local usernames, or private service paths.

## Operational Verification

The implemented architecture has been verified in live operation without
publishing private deployment output. Verification covered:

- public relay restart with strict FIFO delivery in place
- healthy relay durability queue at deployment
- protected LAN database migration with integrity intact
- historical event enrichment using stored event time and corresponding UTC hour
- successful asynchronous enrichment service completion
- active recovery timer behavior
- pending historical rows draining oldest-first

Exact command output, timestamps, hostnames, service unit names, paths, account
names, queue rows, provider details, and machine identities remain outside the
public repository.
