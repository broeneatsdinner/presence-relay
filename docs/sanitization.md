# Sanitization

Sanitization is required before importing live node files into this repository or publishing screenshots and diagrams.

## Redaction Rules

Replace sensitive values with stable placeholders:

| Sensitive value | Placeholder style |
| --- | --- |
| Public IP address | `203.0.113.10` or `PUBLIC_IP_EXAMPLE` |
| Private IP address | `TUNNEL_PEER_IP_EXAMPLE` or `LAN_IP_EXAMPLE` |
| Hostname | `geofence.example.invalid` |
| Token or secret | `replace-with-long-random-token` |
| Latitude/longitude | `0.0` or `EXAMPLE_COORDINATE` |
| Local username | `example` |
| Home path | `<operator-home>/...` |
| macOS path | `<local-workstation-path>/...` |
| Certificate path | `/path/to/sanitized/cert.pem` |

## Workflow

1. Work from a local copy or disposable export, not from live systems.
2. Remove runtime artifacts such as logs, databases, caches, backups, and generated state.
3. Replace secrets, IP addresses, hostnames, usernames, private coordinates, and device identifiers.
4. Rename files to public-safe names when needed.
5. Run `tools/audit/sanitize_scan.sh`.
6. Review every finding and either remediate it or document why it is an intentional placeholder or public fixture.
7. Review the final diff before committing.

## Screenshot Rules

Screenshots must be treated as data-rich artifacts.

Before committing screenshots:

- strip metadata
- crop unrelated UI
- blur or replace real coordinates, addresses, domains, notifications, contacts, and tokens
- verify no browser tabs, account names, local paths, or network identifiers are visible
- store only final reviewed images in a public asset directory

## Import Boundary

Do not sanitize by editing live files in place. Work from a copy, review the copy, and import only the sanitized result.
