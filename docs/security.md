# Security Model

The most important rule is separation: the web process accepts input, but only the worker can invoke Docker.

## User Input Controls

- Emails are normalized and validated.
- Devices are allowlisted in `data/devices.json`.
- Firmware versions must come from cached Meshtastic tags.
- Submitted refs are not accepted directly.
- `userPrefs.jsonc` is parsed before storage.
- Preference keys must start with `USERPREFS_`.
- Unknown keys are rejected when a tag-specific template is available.
- Preference values must be scalar.
- Submitted preference files are size-limited.
- `codeOptions` keys and values are allowlisted in `data/build_options.json`.
- The firmware patch is repo-controlled. Users never supply patch content, only
  which allowlisted options to enable.
- Synthetic macros are merged after user overrides, so `prefsJsonc` cannot set
  or override them.

## Download Tokens

Public URLs use `secrets.token_urlsafe(32)`.

Internal database IDs are never exposed as download identifiers.

## Builder Isolation

Docker mode runs the builder with:

- `--rm`
- configurable Docker networking
- CPU limit
- memory limit
- PID limit
- read-only input mount
- separate output mount

The worker passes only three positional arguments:

- firmware tag
- firmware SHA
- PlatformIO environment

The PlatformIO environment is selected from `data/devices.json`, not from free user input.

The default `MB_DOCKER_NETWORK=bridge` is a functional MVP choice because
historical Meshtastic tags can require PlatformIO platforms or libraries that
were not present in the image built from another ref. Use
`MB_DOCKER_NETWORK=none` only when the builder image is prewarmed for the exact
tag/device set that the service exposes.

## Secrets

Current implementation does not require user accounts or API keys. SMTP credentials are provided via environment variables.

`userPrefs.jsonc` is not returned by public status endpoints and is not included in email.

## Known Hardening Work

- Run the app behind HTTPS and a reverse proxy in production. Set
  `MB_TRUST_PROXY=1` there so rate limiting keys on the real client IP, and only
  when the app is not directly reachable, otherwise `X-Forwarded-For` is spoofable.
- Add persistent IP/email rate limiting instead of in-memory rate limiting.
- Add CSRF protection if cookies or sessions are introduced.
- Run the worker under a restricted OS user.
- Consider S3/MinIO object storage with signed URLs for production.
- Add tag smoke-test automation before marking historical tags supported.
