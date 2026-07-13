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

The public-safe relay code commits accepted authenticated events to a SQLite
durability queue before acknowledgment. Delivery is strict FIFO by durable row
order: the worker inspects the oldest unfinished row, waits if that head row is
backing off, and only then attempts private-side delivery. Phone timestamps are
preserved in the payload but do not control queue order.

Do not import runtime databases, logs, certificates, private keys, real hostnames, real public IP addresses, real tokens, or live `/etc` material directly. Copy live configuration into this repo only after redaction and review.
