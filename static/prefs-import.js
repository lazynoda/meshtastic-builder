// Import a userPrefs.jsonc (the one this page previews, or a hand-written one)
// back into the form. Everything happens in the browser: nothing is sent.
//
// Loaded after app.js and uses its globals (state, $, t, buildPrefs...). The
// firmware, version and device are never in the JSON, so they are left alone
// and the import is applied on top of whatever is selected.
//
// The owner names are not imported on purpose: every node needs its own, and a
// name that can be shipped unchanged will be (see the "no prefilled identity"
// rule in docs/frontend.md).

const IMPORT_MAX_BYTES = 65536;
const IMPORT_SKIPPED_KEYS = new Set(["USERPREFS_CONFIG_OWNER_LONG_NAME", "USERPREFS_CONFIG_OWNER_SHORT_NAME"]);

// Inputs filled from a plain key. Absent key = empty field, because that is what
// the page writes for an empty field.
const IMPORT_TEXT_FIELDS = [
  ["USERPREFS_LORACONFIG_TX_POWER", "loraTxPower"],
  ["USERPREFS_CONFIG_DEVICE_NODE_INFO_BROADCAST_SECS", "nodeInfoSecs"],
  ["USERPREFS_CONFIG_DEVICE_TELEM_UPDATE_INTERVAL", "deviceTelemInterval"],
  ["USERPREFS_MQTT_USERNAME", "mqttUsername"],
  ["USERPREFS_MQTT_PASSWORD", "mqttPassword"],
  ["USERPREFS_MQTT_ROOT_TOPIC", "mqttRootTopic"],
  ["USERPREFS_CONFIG_GPS_UPDATE_INTERVAL", "gpsUpdateInterval"],
  ["USERPREFS_CONFIG_POSITION_BROADCAST_INTERVAL", "positionBroadcastInterval"],
  ["USERPREFS_FIXED_GPS_LAT", "fixedGpsLat"],
  ["USERPREFS_FIXED_GPS_LON", "fixedGpsLon"],
  ["USERPREFS_FIXED_GPS_ALT", "fixedGpsAlt"],
  ["USERPREFS_NETWORK_WIFI_SSID", "wifiSsid"],
  ["USERPREFS_NETWORK_WIFI_PSK", "wifiPsk"],
];

// Selects and booleans the page always writes: an absent key means the
// exporting firmware had no such key, so the current value is kept.
const IMPORT_SELECT_FIELDS = [
  ["USERPREFS_CONFIG_LORA_REGION", "loraRegion"],
  ["USERPREFS_CONFIG_DEVICE_ROLE", "deviceRole"],
  ["USERPREFS_LORACONFIG_MODEM_PRESET", "modemPreset"],
  ["USERPREFS_CONFIG_DEVICE_REBROADCAST_MODE", "rebroadcastMode"],
  ["USERPREFS_CONFIG_GPS_MODE", "gpsMode"],
  ["USERPREFS_CONFIG_SECURITY_PACKET_SIGNATURE_POLICY", "signaturePolicy"],
];
const IMPORT_BOOL_FIELDS = [
  ["USERPREFS_CONFIG_LORA_IGNORE_MQTT", "ignoreMqtt"],
  ["USERPREFS_CONFIG_SMART_POSITION_ENABLED", "smartPosition"],
  ["USERPREFS_MQTT_ENCRYPTION_ENABLED", "mqttEncryption"],
  ["USERPREFS_MQTT_TLS_ENABLED", "mqttTls"],
];

// Presence flags: the page writes them only when ticked.
const IMPORT_FLAG_FIELDS = [
  ["USERPREFS_MQTT_ENABLED", "mqttEnabled"],
  ["USERPREFS_BLOCK_POSITION_ON_EVENT_CHANNEL", "blockPositionOnEvent"],
  ["USERPREFS_FIXED_GPS", "fixedGpsEnabled"],
  ["USERPREFS_NETWORK_WIFI_ENABLED", "wifiEnabled"],
  ["USERPREFS_CONFIG_SECURITY_IS_MANAGED", "securityIsManaged"],
];

const IMPORT_ADMIN_KEYS = [
  ["USERPREFS_USE_ADMIN_KEY_0", "adminKey"],
  ["USERPREFS_USE_ADMIN_KEY_1", "adminKey1"],
  ["USERPREFS_USE_ADMIN_KEY_2", "adminKey2"],
];

class ImportError extends Error {}

// JSONC -> JSON: drops // and /* */ comments and trailing commas, leaving
// anything inside strings alone. Comment bodies are returned too, because the
// preview discloses the advanced-option macros as comments.
function stripJsoncForImport(text) {
  let out = "";
  const comments = [];
  let i = 0;
  while (i < text.length) {
    const char = text[i];
    if (char === '"') {
      let j = i + 1;
      while (j < text.length && text[j] !== '"') j += text[j] === "\\" ? 2 : 1;
      out += text.slice(i, j + 1);
      i = j + 1;
    } else if (char === "/" && text[i + 1] === "/") {
      const end = text.indexOf("\n", i);
      const stop = end === -1 ? text.length : end;
      comments.push(text.slice(i + 2, stop));
      i = stop;
    } else if (char === "/" && text[i + 1] === "*") {
      const end = text.indexOf("*/", i + 2);
      const stop = end === -1 ? text.length : end + 2;
      comments.push(text.slice(i + 2, end === -1 ? text.length : end));
      out += " ";
      i = stop;
    } else {
      out += char;
      i += 1;
    }
  }
  // Trailing commas, again outside strings only.
  let json = "";
  for (let k = 0; k < out.length; k += 1) {
    const char = out[k];
    if (char === '"') {
      let j = k + 1;
      while (j < out.length && out[j] !== '"') j += out[j] === "\\" ? 2 : 1;
      json += out.slice(k, j + 1);
      k = j;
      continue;
    }
    if (char === ",") {
      const rest = out.slice(k + 1).match(/^\s*([}\]])/);
      if (rest) continue;
    }
    json += char;
  }
  return { json, comments };
}

function codeOptionMacroSet() {
  const spec = state.buildOptions;
  if (!spec) return new Set();
  return new Set([
    spec.okToMqtt.macro,
    spec.okToMqtt.nativeMacro,
    spec.customLora.usePresetMacro,
    ...Object.values(spec.customLora.fields).map((field) => field.macro),
  ]);
}

// Returns { prefs, macros } or throws ImportError with a translated message.
function parseImportedPrefs(text) {
  if (!text.trim()) throw new ImportError(t("import.errEmpty"));
  if (encoder.encode(text).length > IMPORT_MAX_BYTES) {
    throw new ImportError(t("import.errTooBig", { kb: IMPORT_MAX_BYTES / 1024 }));
  }
  const { json, comments } = stripJsoncForImport(text);
  let parsed;
  try {
    parsed = JSON.parse(json);
  } catch (error) {
    throw new ImportError(t("import.errSyntax", { detail: error.message }));
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new ImportError(t("import.errNotObject"));
  }
  const badKeys = Object.keys(parsed).filter((key) => !/^USERPREFS_[A-Z0-9_]+$/.test(key));
  if (badKeys.length) {
    throw new ImportError(t("import.errKeys", { keys: badKeys.join(", ") }));
  }
  for (const [key, value] of Object.entries(parsed)) {
    if (!["string", "number", "boolean"].includes(typeof value)) {
      throw new ImportError(t("import.errValue", { key }));
    }
  }
  const macroNames = codeOptionMacroSet();
  const prefs = {};
  const macros = {};
  for (const [key, value] of Object.entries(parsed)) {
    if (macroNames.has(key)) macros[key] = String(value);
    else prefs[key] = String(value);
  }
  // Commented advanced-option macros, as the preview writes them. Only those
  // names: a firmware template is full of commented examples that must not
  // come back to life.
  for (const comment of comments) {
    const match = comment.match(/^\s*"(USERPREFS_[A-Z0-9_]+)"\s*:\s*("(?:[^"\\]|\\.)*"|[^,\s]+)\s*,?\s*$/);
    if (!match || !macroNames.has(match[1]) || match[1] in macros) continue;
    try {
      macros[match[1]] = String(JSON.parse(match[2]));
    } catch (error) {
      macros[match[1]] = match[2];
    }
  }
  if (!Object.keys(prefs).length && !Object.keys(macros).length) {
    throw new ImportError(t("import.errNoPrefs"));
  }
  return { prefs, macros };
}

function importBool(value) {
  return value === "true" || value === "1";
}

// "{ 0x01, 0x02 }" -> base64, the way the form shows keys.
function byteArrayToBase64(value, key, expectedLength = null) {
  const inner = value.trim().match(/^\{([\s\S]*)\}$/);
  const parts = inner ? inner[1].split(",").map((part) => part.trim()).filter(Boolean) : null;
  const bytes = parts?.map((part) => (/^0x[0-9a-f]{1,2}$/i.test(part) ? parseInt(part, 16) : /^\d{1,3}$/.test(part) ? Number(part) : NaN));
  if (!bytes || bytes.some((byte) => !(byte >= 0 && byte <= 255)) || (expectedLength !== null && bytes.length !== expectedLength)) {
    throw new ImportError(t("import.errBytes", { key, bytes: expectedLength ?? "1-32" }));
  }
  return btoa(String.fromCharCode(...bytes));
}

function importChannels(prefs, ignored) {
  const indexes = Object.keys(prefs)
    .map((key) => key.match(/^USERPREFS_CHANNEL_(\d+)_/))
    .filter(Boolean)
    .map((match) => Number(match[1]));
  if (!indexes.length && !("USERPREFS_CHANNELS_TO_WRITE" in prefs)) return;
  let count = Number(prefs.USERPREFS_CHANNELS_TO_WRITE);
  if (!Number.isInteger(count) || count < 1) count = Math.max(...indexes) + 1;
  if (count > state.maxChannels) {
    for (let index = state.maxChannels; index < count; index += 1) {
      ignored.push(`CHANNEL_${index}_*`);
    }
    count = state.maxChannels;
  }
  const channels = [];
  for (let index = 0; index < count; index += 1) {
    const get = (field) => prefs[`USERPREFS_CHANNEL_${index}_${field}`];
    const psk = get("PSK");
    channels.push({
      name: get("NAME") ?? (index === 0 ? DEFAULT_CHANNEL_NAME : `${t("channel.defaultName")} ${index + 1}`),
      psk: psk === undefined || psk.trim() === "{}" ? "" : byteArrayToBase64(psk, `CHANNEL_${index}_PSK`),
      precision: get("PRECISION") ?? "14",
      downlink: get("DOWNLINK_ENABLED") === undefined ? true : importBool(get("DOWNLINK_ENABLED")),
      uplink: get("UPLINK_ENABLED") === undefined ? true : importBool(get("UPLINK_ENABLED")),
      muted: importBool(get("IS_MUTED") ?? "false"),
    });
  }
  state.channels = channels;
}

function importCodeOptions(prefs, macros) {
  const spec = state.buildOptions;
  if (!spec) return;
  const okToMqtt = macros[spec.okToMqtt.nativeMacro] ?? macros[spec.okToMqtt.macro];
  if (okToMqtt !== undefined) $("okToMqtt").checked = importBool(okToMqtt);
  const custom = macros[spec.customLora.usePresetMacro] === "false";
  $("customLoraEnabled").checked = custom;
  if (!custom) return;
  const ids = {
    bandwidthKhz: "loraBandwidth",
    spreadFactor: "loraSpreadFactor",
    codingRate: "loraCodingRate",
    channelNum: "loraChannelNum",
    overrideFrequencyMhz: "loraOverrideFreq",
  };
  for (const [name, field] of Object.entries(spec.customLora.fields)) {
    const value = macros[field.macro];
    if (value !== undefined && ids[name]) $(ids[name]).value = value;
  }
}

// Everything an import may touch, so a failed one can be rolled back.
function snapshotFormForImport() {
  const fields = Array.from($("buildForm").querySelectorAll("input, select, textarea")).filter(
    (el) =>
      el.id &&
      !["firmwareId", "firmwareTag", "deviceId", "prefsJsonc"].includes(el.id) &&
      !el.closest("#channelRows") &&
      !el.closest("#extraRows"),
  );
  return {
    fields: fields.map((el) => ({ el, value: el.value, checked: el.checked })),
    channels: state.channels.map((channel) => ({ ...channel })),
    extraPrefs: state.extraPrefs.map((row) => ({ ...row })),
    presetChannelName: state.presetChannelName,
  };
}

function restoreFormSnapshot(snapshot) {
  for (const { el, value, checked } of snapshot.fields) {
    el.value = value;
    el.checked = checked;
  }
  state.channels = snapshot.channels;
  state.extraPrefs = snapshot.extraPrefs;
  state.presetChannelName = snapshot.presetChannelName;
  syncCustomLora();
  renderChannels();
  renderExtraPrefs();
}

function applyImportedPrefs({ prefs, macros }) {
  const ignored = [];
  const keyKnown = (key) => state.templateKeys.has(key) || isExtraChannelKey(key);

  for (const [key, id] of IMPORT_TEXT_FIELDS) $(id).value = prefs[key] ?? "";
  const address = prefs.USERPREFS_MQTT_ADDRESS;
  $("mqttAddress").value = address === undefined ? "" : address.replace(/^'(.*)'$/, "$1");
  // A value this version's list lacks (an enum added later) keeps the current
  // choice; importMismatches() then reports the key.
  for (const [key, id] of IMPORT_SELECT_FIELDS) {
    if (key in prefs && Array.from($(id).options).some((option) => option.value === prefs[key])) {
      $(id).value = prefs[key];
    }
  }
  for (const [key, id] of IMPORT_BOOL_FIELDS) {
    if (key in prefs) $(id).checked = importBool(prefs[key]);
  }
  // Always written by the page, so only a hand-written file lacks it.
  if ("USERPREFS_TZ_STRING" in prefs) $("tzString").value = prefs.USERPREFS_TZ_STRING;
  for (const [key, id] of IMPORT_FLAG_FIELDS) {
    $(id).checked = key in prefs && (key === "USERPREFS_FIXED_GPS" || prefs[key] === "" || importBool(prefs[key]));
  }
  const pin = prefs.USERPREFS_FIXED_BLUETOOTH;
  $("blePin").value = pin !== undefined ? pin : "";
  for (const [key, id] of IMPORT_ADMIN_KEYS) {
    $(id).value = key in prefs ? byteArrayToBase64(prefs[key], shortPrefKey(key), 32) : "";
  }
  // Managed mode needs an admin key; set it again now the keys are in.
  $("securityIsManaged").disabled = !IMPORT_ADMIN_KEYS.some(([, id]) => $(id).value);
  $("securityIsManaged").checked = "USERPREFS_CONFIG_SECURITY_IS_MANAGED" in prefs && importBool(prefs.USERPREFS_CONFIG_SECURITY_IS_MANAGED);

  importCodeOptions(prefs, macros);
  importChannels(prefs, ignored);

  // Whatever the dedicated controls do not own goes to "other config values",
  // unless it is just this firmware's own default (that comes back by itself).
  state.extraPrefs = [];
  for (const [key, value] of Object.entries(prefs)) {
    if (IMPORT_SKIPPED_KEYS.has(key)) continue;
    if (!keyKnown(key)) {
      // A channel beyond the cap is already reported as a whole.
      if (!/^USERPREFS_CHANNEL_\d+_/.test(key)) ignored.push(shortPrefKey(key));
      continue;
    }
    if (isFormManagedKey(key)) continue;
    if (key in state.templateDefaults && String(state.templateDefaults[key]) === value) continue;
    if (value.trim() === "") continue;
    state.extraPrefs.push({ key, value });
  }

  state.presetChannelName = presetChannelName();
  syncCustomLora();
  renderChannels();
  renderExtraPrefs();
  return ignored;
}

// Byte arrays compare by their bytes, so "{ 1 }" equals "{ 0x01 }".
function normalizeForCompare(value) {
  // The page writes the MQTT address in upstream's 'host' form; a bare host is the same thing.
  const compact = String(value).replace(/\s+/g, "").toLowerCase().replace(/^'(.*)'$/, "$1");
  const inner = compact.match(/^\{(.*)\}$/);
  if (!inner) return compact;
  return inner[1]
    .split(",")
    .filter(Boolean)
    .map((part) => String(Number(part)))
    .join(",");
}

// Re-read the form and list the keys that did not come out as they went in:
// an enum this version lacks, a precision the slider cannot show, and so on.
function importMismatches({ prefs, macros }) {
  const built = buildPrefs();
  const builtMacros = Object.fromEntries(codeOptionMacros());
  const spec = state.buildOptions;
  const mismatched = [];
  for (const [key, value] of Object.entries(prefs)) {
    if (IMPORT_SKIPPED_KEYS.has(key)) continue;
    if (!state.templateKeys.has(key) && !isExtraChannelKey(key)) continue;
    if (/^USERPREFS_CHANNEL_(\d+)_/.test(key) && Number(key.match(/^USERPREFS_CHANNEL_(\d+)_/)[1]) >= state.maxChannels) continue;
    if (!(key in built) || normalizeForCompare(built[key]) !== normalizeForCompare(value)) {
      mismatched.push(shortPrefKey(key));
    }
  }
  for (const [key, value] of Object.entries(macros)) {
    if (key === spec?.okToMqtt.macro || key === spec?.okToMqtt.nativeMacro) {
      if (String($("okToMqtt").checked) !== String(importBool(value))) mismatched.push(shortPrefKey(key));
      continue;
    }
    if (!state.codeOptionsAvailable) {
      mismatched.push(shortPrefKey(key));
      continue;
    }
    if (normalizeForCompare(builtMacros[key] ?? "") !== normalizeForCompare(value)) mismatched.push(shortPrefKey(key));
  }
  return mismatched;
}

function setImportError(message) {
  const el = $("importError");
  el.textContent = message || "";
  el.hidden = !message;
}

function openImportDialog() {
  setImportError("");
  $("importDialog").showModal();
  $("importText").focus();
}

function closeImportDialog() {
  $("importDialog").close();
}

function runImport() {
  if (!state.templateKeys.size) {
    setImportError(t("import.errNotReady"));
    return;
  }
  let parsed;
  try {
    parsed = parseImportedPrefs($("importText").value);
  } catch (error) {
    setImportError(error instanceof ImportError ? error.message : String(error.message || error));
    return;
  }
  const snapshot = snapshotFormForImport();
  let ignored;
  let mismatched;
  try {
    ignored = applyImportedPrefs(parsed);
    mismatched = importMismatches(parsed);
  } catch (error) {
    restoreFormSnapshot(snapshot);
    updatePrefsPreview();
    setImportError(error instanceof ImportError ? error.message : t("import.errForm", { detail: error.message }));
    return;
  }
  closeImportDialog();
  updatePrefsPreview();

  const imported = Object.keys(parsed.prefs).filter((key) => !IMPORT_SKIPPED_KEYS.has(key)).length + Object.keys(parsed.macros).length;
  const lines = [t("import.done", { n: imported })];
  if (ignored.length) lines.push(t("import.ignored", { keys: ignored.join(", ") }));
  if (mismatched.length) lines.push(t("import.mismatch", { keys: mismatched.join(", ") }));
  const notice = $("importNotice");
  notice.textContent = lines.join(" ");
  notice.classList.toggle("status-warn", ignored.length > 0 || mismatched.length > 0);
  notice.hidden = false;

  // The names are the one thing the import never fills: take the user there.
  $("longName").scrollIntoView({ block: "center" });
  $("longName").focus();
}

async function loadImportFile(file) {
  if (!file) return;
  if (file.size > IMPORT_MAX_BYTES) {
    setImportError(t("import.errTooBig", { kb: IMPORT_MAX_BYTES / 1024 }));
    return;
  }
  try {
    $("importText").value = await file.text();
    setImportError("");
  } catch (error) {
    setImportError(t("import.errFile"));
  }
}

function bindImport() {
  $("openImport").addEventListener("click", openImportDialog);
  $("importCancel").addEventListener("click", closeImportDialog);
  $("importConfirm").addEventListener("click", runImport);
  $("importPickFile").addEventListener("click", () => $("importFile").click());
  $("importFile").addEventListener("change", async (event) => {
    await loadImportFile(event.target.files[0]);
    // Picking the same file again must fire change again.
    event.target.value = "";
  });
  $("importText").addEventListener("input", () => setImportError(""));
  $("importText").addEventListener("dragover", (event) => event.preventDefault());
  $("importText").addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    event.preventDefault();
    loadImportFile(file);
  });
}

bindImport();
