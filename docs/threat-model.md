# Threat Model

This threat model focuses on publication-safe documentation for a real mobile-to-home geofence reporting system.

## Assets

- geofence event authenticity
- shortcut tokens and request headers
- WireGuard private keys and peer configuration
- TLS certificate and ACME account material
- public relay service configuration
- home-side event database and logs
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

## Publication Standard

Public content should explain the security architecture and engineering tradeoffs without enabling direct targeting of the live deployment.
