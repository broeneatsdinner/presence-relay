# Public Relay Node

This directory contains sanitized deployment templates and notes for the public
relay node.

Expected imported contents:

- systemd unit files under a local `systemd/` directory
- lighttpd route fragments under a local `lighttpd/` directory
- deployment notes needed to reproduce the service safely

Canonical application code lives outside this node directory:

- `app/webhookd.py`
- `app/webhookd.env.example`

Do not import runtime databases, logs, certificates, private keys, real hostnames, real public IP addresses, real tokens, or live `/etc` material directly. Copy live configuration into this repo only after redaction and review.
