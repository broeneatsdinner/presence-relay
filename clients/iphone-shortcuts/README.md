# iPhone Shortcuts

Client automation artifacts and documentation for the mobile entrypoint.

This client owns the public-safe description of the iOS entrypoint:

- Personal Automations that trigger on geofence boundaries.
- Reusable action Shortcuts that send webhook payloads.
- Sanitized request format and payload examples.
- Operational notes about background execution behavior.

## Personal Automations vs Reusable Action Shortcuts

Use two layers:

- Personal Automation: the iOS geofence trigger, such as arriving at or leaving
  a named example place.
- Reusable action Shortcut: the action that gathers location/timestamp data and
  sends the authenticated HTTPS request.

This keeps location-trigger setup separate from the webhook action. The same
payload shape can be reused for multiple places without encoding the place into
the event name.

See [Place State](../../docs/place-state.md) for the canonical event and
place-state model.

## Expected Shortcut Payload Shape

The Shortcut sends JSON to a public relay endpoint:

```json
{
  "event": "arrive",
  "place": "home",
  "lat": 39.000000,
  "lon": -104.000000,
  "ts": "2026-01-01T08:00:00-07:00"
}
```

Rules:

- `event` is `arrive` or `leave`.
- `place` is a lowercase token such as `home`, `camp`, or `unnamed`.
- Public examples use fake coordinates, fabricated timestamps, placeholder
  endpoints, and redacted tokens.

## Required Privacy Permissions

Each Shortcut needs permission to run while locked, access location, and send
the HTTPS request to the configured relay endpoint. The "Get Contents of URL"
action also needs permission to use Location data.

Public screenshots should be recreated from sanitized demo Shortcuts or heavily
redacted copies. Do not publish screenshots that reveal live endpoints, tokens,
real places, accounts, notifications, or private device context.

## Known iOS Duplication Gotcha

Duplicating a Shortcut may not preserve all Privacy permissions. A copied
Shortcut that only shows "Allow Running When Locked" may be incomplete even if
its actions look correct.

If a duplicated Shortcut behaves inconsistently, recreate it from a known-good
Shortcut, re-check the payload values, and confirm the Privacy tab shows
location and relay endpoint permissions before relying on it.

## Deprecated Legacy Direct-SSH Shortcuts

Older direct-SSH Shortcuts required the phone to reach the private LAN target
over LAN/VPN. They are deprecated in favor of the public relay path:

```text
Personal Automation
  -> reusable No VPN Needed Shortcut
  -> public HTTPS relay
  -> private-side delivery path
  -> trusted LAN automation target
```

Do not commit:
- personal identifiers
- live callback URLs
- tokens
- unreviewed Shortcut exports
- private screenshots
