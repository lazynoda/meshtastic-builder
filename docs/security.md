# Security Model

The most important rule is separation: the web process accepts input, but only the worker can invoke Docker.

## User Input Controls

- Devices are allowlisted in `data/devices.json`.
- Firmware versions must come from cached Meshtastic tags.
- Submitted refs are not accepted directly.
- `userPrefs.jsonc` is parsed before storage.
- Preference keys must start with `USERPREFS_`.
- Unknown keys are rejected when a tag-specific template is available.
- Preference values must be scalar.
- Submitted preference files are size-limited.
- `codeOptions` keys and values are allowlisted in `data/build_options.json`.
- Firmware patches are repo-controlled. Users never supply patch content, only
  which allowlisted options to enable.
- Synthetic macros are merged after user overrides, so `prefsJsonc` cannot set
  or override them.
- Preference values are shape-checked. `bin/platformio-custom.py` emits values
  beginning with `meshtastic_` or `{` into `-D` flags unquoted and quotes the
  rest, so identifiers must match `meshtastic_[A-Za-z0-9_]+`, brace values must
  be byte arrays, and other strings may not contain `"`, backslashes, `$`,
  backticks or control characters. Without this, any template key is an
  injection point into the compiler command line.

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

The service requires no user accounts, API keys, or outbound credentials. It
stores no email address: a build is reachable only through its private token.

Values for keys the firmware consumes as C strings are rejected when they would
reach the compiler unquoted. `bin/platformio-custom.py` only wraps a value in
quotes if it does not already look like a number, bool, hex literal, enum or
byte array, so an all-digit WiFi password or node name would be emitted bare and
break the build. `STRING_MACRO_KEYS` in `meshtastic_builder/jsonc.py` guards
those keys, and the page applies the same rule while typing.

`/api/health` is unauthenticated, so it reports only aggregate counts and the
time of the last request. It carries no token, no preferences and no device or
firmware choice, and its failure body names no path or query.

`userPrefs.jsonc` is not returned by public status endpoints. MQTT credentials
entered in the form are compiled into the firmware in clear text, which is a
property of `userPrefs.jsonc` itself; the UI warns about it.

## Known Hardening Work

- Run the app behind HTTPS and a reverse proxy in production. Set
  `MB_TRUST_PROXY=1` there so rate limiting keys on the real client IP, and only
  when the app is not directly reachable, otherwise `X-Forwarded-For` is spoofable.
- Add persistent IP-based rate limiting instead of in-memory rate limiting.
- Add CSRF protection if cookies or sessions are introduced.
- Run the worker under a restricted OS user.
- Consider S3/MinIO object storage with signed URLs for production.
- Add tag smoke-test automation before marking historical tags supported.
