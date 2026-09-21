# Testing

Run all tests:

```bash
python3 -B -m unittest discover -s tests
```

`-B` avoids writing `__pycache__` directories during local verification.

## Current Coverage Areas

- JSONC parsing, comments, trailing commas, and normalization.
- Preference key extraction with comments ignored.
- Public token validation.
- Firmware tag pagination.
- Automatic support policy for latest firmware tags.
- Submission validation and tag/SHA resolution.
- Worker fake-mode lifecycle.
- ZIP artifact creation.
- Artifact expiry and deletion.
- Admin firmware support toggles.
- Device allowlist validation against Meshtastic `variants/**`.
- Docker daemon diagnostics.
- Advanced build option validation, version gating, and macro expansion.
- Patch shipping into job inputs and `code_options` in `BUILD_INFO.txt`.
- `code_options` column migration on pre-existing databases.
- Client IP resolution behind a reverse proxy (`MB_TRUST_PROXY`).
- Value hardening for keys that reach the compiler unquoted.
- Channel cap (3 vs 8) by firmware version.
- Advanced-option macro naming and patch skipping on native firmware.
- Fixed-GPS patch gating by firmware version and by the prefs actually asking
  for a fixed position, and its retirement once a release carries the fix.
- Build failure classification, including that secrets in the `-D` dump never
  reach the user-facing detail line.
- Newest-first firmware version ordering.

## Test Files

- `tests/test_jsonc.py`
- `tests/test_security.py`
- `tests/test_firmware_versions.py`
- `tests/test_submissions.py`
- `tests/test_fake_worker_flow.py`
- `tests/test_cleanup.py`
- `tests/test_builder.py`
- `tests/test_admin.py`
- `tests/test_code_options.py`
- `tests/test_app.py`

## Why Fake Mode Exists

Real Meshtastic builds require Docker, network, PlatformIO packages, and significant time. Fake mode lets refactors verify the internal queue contract quickly:

1. create request,
2. claim job,
3. write inputs,
4. produce ZIP,
5. update DB.

Fake mode does not replace a real builder smoke test before deployment.

## Recommended Future Tests

- Browser-level form test.
- Concurrency test for multiple workers once concurrency increases.
- Automated `git apply --check` of every `docker/patches/*.patch` across each
  supported tag, so neither the `minFirmwareVersion` floor nor
  `fixedGpsPatch.fixedSinceFirmwareVersion` can silently rot.
