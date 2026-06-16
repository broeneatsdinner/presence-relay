# Private quarantine policy

The `private/` directory must not exist in a public export or public
repository. In the private working repository it is intentionally excluded from
version control and may contain raw logs, databases, secrets, keys, tokens, and
other sensitive artifacts.

Rules:
- Never add or commit `private/` contents.
- Before any public release, confirm `private/` does not exist in the working tree
  of the release branch/export.
