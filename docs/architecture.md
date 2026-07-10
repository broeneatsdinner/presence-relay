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
	| private-side delivery path
	v
Trusted LAN target
	|
	| local logging, enrichment, storage, and viewer
	v
Trusted LAN resources
```

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
requests, and relays accepted events through the private delivery path.

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
