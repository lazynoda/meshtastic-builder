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
5. Channels.
6. MQTT, including the `ok_to_mqtt` code option.
7. `<details class="collapsible">`: Bluetooth and WiFi.
8. `<details class="collapsible">`: Position and GPS.
9. `<details class="collapsible">`: Security.
10. `<details class="collapsible">`: Other config values.
11. Review and submit.

`USERPREFS_FIXED_GPS` is a presence flag: the firmware only tests `#ifdef`, so the
form writes it with an empty value. That is why fixed position needs a control of
its own and cannot be set from the free-form section, which skips empty values.
The coordinates are multiplied into an int32 by the firmware, so they are checked
against a plain-decimal pattern as well as a range; scientific notation would be
quoted by the build script and then fail to compile.

Every collapsed section is closed by default and its panels are not numbered
steps.

## What the Preview Guarantees

The textarea is submitted verbatim as `prefsJsonc`, so it is the source of truth
for the build, not a display. Audited by mutating all 50 controls and diffing the
preview: every one is reflected, and a full submission produced an artifact whose
`userPrefs.jsonc` matched the preview key for key and value for value.

Keys are grouped and ordered to mirror the form, with a comment naming each
block, so a setting is found where the page put it. `previewGroups` holds that
order; a key missing from it still appears, under the trailing defaults block,
so nothing can be hidden by forgetting to list it.

Two things reach the firmware without being ordinary entries:

- The template's active (uncommented) defaults. `buildPrefs` seeds them from
  `state.templateDefaults` so the preview shows them rather than the server
  silently adding them during the merge.
- The macros the advanced options expand into, which are not template keys and
  would be rejected as entries. They appear as JSONC comments, so the text stays
  submittable while still disclosing them.

When a value fails validation the preview keeps its last good content and the
status line carries the error. `submitBuild` re-runs `updatePrefsPreview` and
aborts if it fails, so a stale preview can never be submitted.

## Comboboxes

The device picker and the free-form key picker are comboboxes, not `<select>`
elements: a text box that filters its list by substring as you type. `<datalist>`
would have been less code, but iOS Safari barely supports it and this page is
mostly read on a phone.

The visible input only searches. A hidden `.combo-value` sibling holds the real
value and fires `change`, so the rest of the form reads it like any other field
(`$("deviceId").value` still works). Matching drops punctuation from both sides,
so "promicro" finds "Pro-micro" and "gpsmode" finds `CONFIG_GPS_MODE`. Focusing
reveals the whole list, because the box holds the current label and would
otherwise filter down to the option already chosen.

## Other Config Values

Rather than grow a control per key, the last section lets the user pick any key
from the selected tag's template and type its value. The dropdown lists keys
alphabetically without the `USERPREFS_` prefix, and uses the sample value from
the template as the input placeholder so the expected shape is visible.

`FORM_MANAGED_KEYS` in `static/app.js`, plus the channel-key pattern and the
macro names the advanced options expand into, lists what the dedicated controls
already own; those keys are filtered out so a setting can never have two sources. **Add to that set whenever a new dedicated control is
added**, or the same key becomes settable twice. A key already chosen in one row
is filtered out of the others.

The values go through `setPref` like any other, so they land in the preview and
in the submission, and the server validates them against the same per-key rules.
There is no client-side value check here, so a wrong value is reported by the
server on submit.

`[hidden]` is forced to `display: none !important` in `static/styles.css`. Author
rules set `display` on labels and panels, which otherwise beats the user-agent
rule for the attribute and leaves a control that JavaScript has hidden still on
screen. Every gating path here sets `.hidden`, so that rule is what makes them
work. Bluetooth and WiFi are ordinary settings rather than advanced ones, but
they are folded away because the page is long.

The WiFi controls hide themselves, and emit nothing, when the selected device's
family has no WiFi radio, so an nRF52 build never carries WiFi macros.

Form defaults aim at a quiet mesh: rebroadcast `CORE_PORTNUMS_ONLY`, node info
every 259200 s (72 h), and both telemetry intervals empty. Empty is not "firmware
default" for telemetry: `installDefaultModuleConfig` sets `device_update_interval`
to `MAX_INTERVAL` when the macro is absent, so leaving it blank disables it.

Channel rows carry a drag handle and reorder through pointer events, not HTML5
drag, so reordering also works on touch screens. Row order is the channel index,
so dragging a row to the top makes it the primary channel. Precision is a slider
over `PRECISION_STEPS` (0, 10..19, 32) that shows the approximate radius instead
of the raw bit count, halving 23.3 km per extra bit as the Meshtastic docs do.

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

Because these macros are not userPrefs keys, `setPref` would drop them from the
preview. The preview instead appends them as JSONC comments inside the object, so
what the user reads matches what the server merges and the submitted text still
parses.

See [Advanced Build Options](build-options.md) for the backend half.

## Checking Changes

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.app
```

Then open `http://localhost:8080/`, and verify a build end to end with a worker:

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker --once
```
