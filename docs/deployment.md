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
