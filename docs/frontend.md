# Frontend

The frontend is plain HTML, CSS and JavaScript served straight from `static/`
by `meshtastic_builder.app`. There is no bundler, no `package.json`, and no
build step: editing a file in `static/` and reloading the page is the whole
development loop.

## Files

| File | Purpose |
| --- | --- |
| `static/index.html` | Page shell and the step form. |
| `static/styles.css` | Design tokens, shell, panels, buttons, form controls. |
| `static/i18n.js` | Spanish/English dictionary, `t()`, language toggle. |
| `static/app.js` | Form logic, `userPrefs.jsonc` generation, submit and polling. |
| `static/favicon.svg` | Shared meshtastic.es mark. |

## Styling

Tokens, reset, `.shell`, `.app-header`, `.panel`, `.btn` and `.status-line` come
from the shared meshtastic.es app template, so this service matches the other
community tools. The template ships no form control styles, so inputs, selects,
grids, channel rows and the result list are authored here following the same
recipe: `--panel2` background, `--border` outline, accent-coloured focus ring,
transitions capped at 0.15s.

Design rules worth keeping:

- `--accent` (cyan) is the only brand colour. `--warn` and `--danger` mean state,
  never branding.
- State colours appear as ~12% tints over transparent, never as solid fills.
- Dark theme only, by design.
- Two button emphasis levels: `.btn` and `.btn.btn-primary`.
- Radius 10px for panels, 8px (`--radius`) for controls.
- Step numbers come from a CSS counter on `#buildForm .panel h2::before`, so
  panels can be added, hidden or reordered without renumbering markup.

## Internationalization

`i18n.js` holds one flat dictionary per language. Static markup is translated
through `data-i18n` and `data-i18n-placeholder` attributes; strings built in
JavaScript call `t(key, vars)` with `{name}` placeholders.

The initial language comes from `localStorage`, falling back to
`navigator.language`. Switching dispatches a `languagechange` event, which
re-renders the channel rows, the status line and the result panel.

Backend error messages are still Spanish only and are shown verbatim.

## Deep Links

A build is addressable as `/?build=<token>`. The token is a query parameter
rather than a path segment so no server routing is needed. After a successful
submit the URL is rewritten with `history.replaceState`, and the result panel
shows that URL as its headline with a copy button. Nothing else records the
build for the user, so the panel says so explicitly. On load, a `build`
parameter fetches that build and resumes polling if it is still running.

## Version Gating

Two independent mechanisms keep the form honest across firmware versions:

- **Template gating.** Any element carrying `data-pref-key="USERPREFS_..."` is
  hidden when the selected tag's `userPrefs.jsonc` template does not define that
  key. `setPref` drops such keys anyway, so the hiding is cosmetic but keeps the
  form from promising settings the build would ignore.
- **Enum gating.** `REGION_OPTIONS` and `PRESET_OPTIONS` carry an optional third
  element, the firmware version that introduced the value. `populateStaticSelects(tag)`
  filters on it and preserves the current selection when it survives. This
  matters because protobuf enum names change: `ITU23_2M` existed only in
  2.7.23–2.7.24 and became `ITU2_2M`/`ITU3_2M`, and an unknown identifier fails
  at compile time, not at submit time.

The channel cap (3, or 8 from `eightChannelsSinceFirmwareVersion`) comes from
`/api/build-options` as well.

## Form Groups

The form is split into the settings most users touch and everything else:

1. Device and firmware.
2. Node: long/short name and timezone.
3. LoRa radio: region, modem preset, TX power, manual LoRa parameters.
4. Device: role, rebroadcast mode, node info and device telemetry intervals.
5. `<details class="advanced-section">`, collapsed by default: Channels, MQTT,
   Security, Environment sensors. Panels inside it are not numbered steps.
6. Review and submit.

Panels marked `data-gated` hide themselves when every `[data-pref-key]` control
inside them is absent from the selected tag's template.

## Code Options

Manual LoRa parameters (LoRa panel) and `ok_to_mqtt` (MQTT panel) are code
options, not userPrefs keys. Their controls carry `.code-option` and hide when
the selected tag is below `minFirmwareVersion`; a `SOURCE PATCH` badge and
warning (`.patch-only`) show below `nativeSinceFirmwareVersion`, where the
builder applies `docker/patches/userprefs-ext.patch`. Value ranges come from
`GET /api/build-options`, so they live in `data/build_options.json` and are
never duplicated in JavaScript. Enabling manual LoRa configuration disables the
modem preset selector with an inline explanation.

See [Advanced Build Options](build-options.md) for the backend half.

## Checking Changes

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.app
```

Then open `http://localhost:8080/`, and verify a build end to end with a worker:

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker --once
```
