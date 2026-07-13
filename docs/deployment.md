# Deployment

This document maps repository locations to public-safe deployment roles. It is
not a secret inventory and should not contain live credentials, live hostnames,
or private paths.

## Repository Targets

```text
app/                       sanitized relay application code
clients/iphone-shortcuts/  sanitized iPhone Shortcut documentation and export notes
examples/payloads/         fake JSON payload examples
nodes/public-relay/        sanitized public relay service configuration
nodes/home-lan-target/     sanitized trusted LAN automation code and viewer assets
tools/audit/               local audit tools for import and publication review
```

## Public-Safe Deployment Mapping

| Node | Repository path | Example deployment target | Notes |
| --- | --- | --- | --- |
| iPhone Shortcuts | `clients/iphone-shortcuts/` | iOS Shortcuts configuration | Keep live endpoints, tokens, screenshots, and location labels out of public docs. Fake payload examples live in `examples/payloads/`. |
| Public relay app | `app/webhookd.py` | `/opt/presence-relay/app/webhookd.py` | Relay application binds to localhost by default and expects a reverse proxy. |
| Public relay config | `nodes/public-relay/systemd/` | systemd unit directory | Use sanitized service templates only. |
| Public relay proxy | `nodes/public-relay/lighttpd/` | reverse-proxy route fragment | Use sanitized route/proxy fragments only. |
| Trusted LAN target | `nodes/home-lan-target/` | `/opt/presence-relay/home-lan-target/` | Automation, ingest/enrich code, and local viewer assets. |

## Deployment Principle

The repo should describe how the system is deployed, but the live deployment should keep private environment files, runtime state, certificates, keys, logs, and databases outside version control.

Implemented deployment behavior is described at the role level:

- the public relay authenticates incoming mobile events
- accepted relay events are committed to a SQLite durability queue before
  delivery
- relay delivery is strict FIFO by durable insertion order, with retry/backoff
  across the public/private trust boundary
- the protected LAN processing node commits the raw event to SQLite before
  updating derived projections
- enrichment is asynchronous and recovery-driven; event acceptance and mobile
  acknowledgment do not wait for environmental context

Do not convert those role descriptions into public deployment instructions that
publish live service unit names, private hostnames, SSH aliases, account names,
exact database paths, provider URLs, command output, or runtime row contents.

## Operational Verification Boundary

The live system has been verified after the latest architecture changes:

- public relay service restart completed with strict FIFO delivery in place
- relay durability queue was healthy at deployment
- protected LAN database migration completed with integrity intact
- historical event enrichment completed using the stored event time and UTC
  environmental hour
- asynchronous enrichment completed successfully
- recovery timer behavior is enabled and active
- pending historical enrichment rows are draining oldest-first

Public documentation may state those outcomes. It must not include exact
commands, timestamps, hostnames, service names, usernames, paths, queue row
contents, provider responses, or machine identities.

## Example File Policy

Commit:

- `*.env.example`
- sanitized `*.service.example`
- sanitized `*.conf.example`
- docs and diagrams after OPSEC review

Do not commit:

- `.env`
- live systemd units with real users, paths, tokens, or hostnames
- live lighttpd files with real domains or certificate paths
- WireGuard private keys
- event databases
- logs or JSONL event streams
