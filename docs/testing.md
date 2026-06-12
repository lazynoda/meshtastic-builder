# Testing

Run all tests:

```bash
python3 -B -m unittest discover -s tests
```

`-B` avoids writing `__pycache__` directories during local verification.

## Current Coverage Areas

- JSONC parsing, comments, trailing commas, and normalization.
- Preference key extraction with comments ignored.
- Email and public token validation.
- Firmware tag pagination.
- Automatic support policy for latest firmware tags.
- Submission validation and tag/SHA resolution.
- Worker fake-mode lifecycle.
- ZIP artifact creation.
- Outbox email writing.
- Artifact expiry and deletion.
- Admin firmware support toggles.
- Device allowlist validation against Meshtastic `variants/**`.
- Docker daemon diagnostics.

## Test Files

- `tests/test_jsonc.py`
- `tests/test_security.py`
- `tests/test_firmware_versions.py`
- `tests/test_submissions.py`
- `tests/test_fake_worker_flow.py`
- `tests/test_cleanup.py`
- `tests/test_builder.py`
- `tests/test_mailer.py`
- `tests/test_admin.py`

## Why Fake Mode Exists

Real Meshtastic builds require Docker, network, PlatformIO packages, and significant time. Fake mode lets refactors verify the internal queue contract quickly:

1. create request,
2. claim job,
3. write inputs,
4. produce ZIP,
5. update DB,
6. send email.

Fake mode does not replace a real builder smoke test before deployment.

## Recommended Future Tests

- Real Docker builder smoke test for one supported environment.
- Browser-level form test.
- SMTP integration test using Mailpit.
- Migration test if schema migrations are introduced.
- Concurrency test for multiple workers once concurrency increases.
