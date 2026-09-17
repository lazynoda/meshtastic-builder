const WIFI_FAMILIES = new Set(["esp32", "esp32-s3", "esp32-c3", "esp32-c6"]);

// Keys the dedicated controls own. Everything else in the selected tag's template
// is offered in the free-form section, so the two sets must never overlap.
const FORM_MANAGED_KEYS = new Set([
  "USERPREFS_CHANNELS_TO_WRITE",
  "USERPREFS_CONFIG_DEVICE_NODE_INFO_BROADCAST_SECS",
  "USERPREFS_CONFIG_DEVICE_REBROADCAST_MODE",
  "USERPREFS_CONFIG_DEVICE_ROLE",
  "USERPREFS_CONFIG_DEVICE_TELEM_UPDATE_INTERVAL",
  "USERPREFS_CONFIG_LORA_IGNORE_MQTT",
  "USERPREFS_CONFIG_LORA_REGION",
  "USERPREFS_CONFIG_OWNER_LONG_NAME",
  "USERPREFS_CONFIG_OWNER_SHORT_NAME",
  "USERPREFS_CONFIG_SECURITY_IS_MANAGED",
  "USERPREFS_CONFIG_SECURITY_PACKET_SIGNATURE_POLICY",
  "USERPREFS_FIXED_BLUETOOTH",
  "USERPREFS_LORACONFIG_MODEM_PRESET",
  "USERPREFS_LORACONFIG_TX_POWER",
  "USERPREFS_MQTT_ADDRESS",
  "USERPREFS_MQTT_ENABLED",
  "USERPREFS_MQTT_ENCRYPTION_ENABLED",
  "USERPREFS_MQTT_PASSWORD",
  "USERPREFS_MQTT_ROOT_TOPIC",
  "USERPREFS_MQTT_TLS_ENABLED",
  "USERPREFS_MQTT_USERNAME",
  "USERPREFS_NETWORK_WIFI_ENABLED",
  "USERPREFS_NETWORK_WIFI_PSK",
  "USERPREFS_NETWORK_WIFI_SSID",
  "USERPREFS_TZ_STRING",
  "USERPREFS_USE_ADMIN_KEY_0",
  "USERPREFS_USE_ADMIN_KEY_1",
  "USERPREFS_USE_ADMIN_KEY_2",
]);

const state = {
  deviceFamilies: {},
  extraPrefs: [],
  templateExamples: {},
  currentBuildToken: null,
  pollTimer: null,
  templateKeys: new Set(),
  channels: [],
  statusIsError: false,
  statusKey: null,
  buildOptions: null,
  codeOptionsAvailable: false,
  codeOptionsNative: false,
  maxChannels: 3,
  lastBuild: null,
  lastDownloadUrl: null,
  lastBuildUrl: null,
};

const $ = (id) => document.getElementById(id);
const encoder = new TextEncoder();

// Third element is the firmware version that introduced the enum value.
const REGION_OPTIONS = [
  ["EU_868", "EU 868 MHz"],
  ["EU_433", "EU 433 MHz"],
  ["EU_866", "EU 866 MHz", "2.7.23"],
  ["EU_874", "EU 874 MHz", "2.7.23"],
  ["EU_917", "EU 917 MHz", "2.7.23"],
  ["EU_N_868", "EU narrow 868 MHz", "2.7.23"],
  ["US", "US 915 MHz"],
  ["ANZ", "Australia / New Zealand 915 MHz"],
  ["ANZ_433", "Australia / New Zealand 433 MHz"],
  ["BR_902", "Brazil 902 MHz"],
  ["CN", "China"],
  ["IN", "India"],
  ["JP", "Japan"],
  ["KR", "Korea"],
  ["KZ_433", "Kazakhstan 433 MHz"],
  ["KZ_863", "Kazakhstan 863 MHz"],
  ["MY_433", "Malaysia 433 MHz"],
  ["MY_919", "Malaysia 919 MHz"],
  ["NP_865", "Nepal 865 MHz"],
  ["NZ_865", "New Zealand 865 MHz"],
  ["PH_433", "Philippines 433 MHz"],
  ["PH_868", "Philippines 868 MHz"],
  ["PH_915", "Philippines 915 MHz"],
  ["RU", "Russia"],
  ["SG_923", "Singapore 923 MHz"],
  ["TH", "Thailand"],
  ["TW", "Taiwan"],
  ["UA_433", "Ukraine 433 MHz"],
  ["UA_868", "Ukraine 868 MHz"],
  ["LORA_24", "2.4 GHz"],
  ["ITU1_2M", "ITU region 1, 2 m", "2.7.23"],
  ["ITU2_2M", "ITU region 2, 2 m", "2.7.25"],
  ["ITU3_2M", "ITU region 3, 2 m", "2.7.25"],
  ["ITU1_70CM", "ITU region 1, 70 cm", "2.8.0"],
  ["ITU2_70CM", "ITU region 2, 70 cm", "2.8.0"],
  ["ITU3_70CM", "ITU region 3, 70 cm", "2.8.0"],
  ["ITU2_125CM", "ITU region 2, 1.25 m", "2.8.0"],
];

const ROLE_OPTIONS = [
  ["CLIENT", "Client"],
  ["CLIENT_MUTE", "Client mute"],
  ["CLIENT_HIDDEN", "Client hidden"],
  ["TRACKER", "Tracker"],
  ["SENSOR", "Sensor"],
  ["TAK", "TAK"],
  ["TAK_TRACKER", "TAK tracker"],
];

const PRESET_OPTIONS = [
  ["LONG_FAST", "Long fast"],
  ["LONG_MODERATE", "Long moderate"],
  ["MEDIUM_FAST", "Medium fast"],
  ["MEDIUM_SLOW", "Medium slow"],
  ["MEDIUM_TURBO", "Medium turbo", "2.8.0"],
  ["SHORT_FAST", "Short fast"],
  ["SHORT_SLOW", "Short slow"],
  ["SHORT_TURBO", "Short turbo"],
  ["LONG_TURBO", "Long turbo"],
  ["LITE_FAST", "Lite fast", "2.7.23"],
  ["LITE_SLOW", "Lite slow", "2.7.23"],
  ["NARROW_FAST", "Narrow fast", "2.7.23"],
  ["NARROW_SLOW", "Narrow slow", "2.7.23"],
  ["TINY_FAST", "Tiny fast", "2.8.0"],
  ["TINY_SLOW", "Tiny slow", "2.8.0"],
];

const REBROADCAST_OPTIONS = [
  ["ALL", "All"],
  ["ALL_SKIP_DECODING", "All, skip decoding"],
  ["LOCAL_ONLY", "Local only"],
  ["KNOWN_ONLY", "Known only"],
  ["CORE_PORTNUMS_ONLY", "Core portnums only"],
  ["NONE", "None"],
];

const SIGNATURE_POLICY_OPTIONS = [
  ["PACKET_SIGNATURE_POLICY_COMPATIBLE", "Compatible"],
  ["PACKET_SIGNATURE_POLICY_BALANCED", "Balanced"],
  ["PACKET_SIGNATURE_POLICY_STRICT", "Strict"],
];

// Firmware bandwidth codes are not all the real value in kHz.
const BANDWIDTH_LABELS = { 31: "31.25", 62: "62.5" };

// Position precision values the Meshtastic clients expose: 0 hides the position,
// 32 sends it exact, 10..19 truncate the coordinates to that many bits.
const PRECISION_STEPS = [0, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 32];
const DEFAULT_PRECISION_INDEX = PRECISION_STEPS.indexOf(14);

// 23.3 km at 10 bits, halved per extra bit: same table the Meshtastic docs publish.
function precisionLabel(precision) {
  const bits = Number(precision);
  if (bits === 0) return t("channel.precisionOff");
  if (bits >= 32) return t("channel.precisionExact");
  const metres = 23300 / 2 ** (bits - 10);
  return metres >= 1000 ? `~${(metres / 1000).toFixed(1)} km` : `~${Math.round(metres)} m`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function setStatus(message, isError = false, key = null) {
  const el = $("statusText");
  el.textContent = message;
  el.classList.toggle("status-error", isError);
  state.statusIsError = isError;
  state.statusKey = key;
}

function setStatusKey(key) {
  setStatus(t(key), false, key);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function parseVersion(tag) {
  const match = /^v?(\d+)\.(\d+)\.(\d+)/.exec(String(tag).trim());
  return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : null;
}

function versionAtLeast(tag, minimum) {
  const current = parseVersion(tag);
  const floor = parseVersion(minimum);
  if (!current || !floor) return false;
  for (let i = 0; i < 3; i += 1) {
    if (current[i] !== floor[i]) return current[i] > floor[i];
  }
  return true;
}

function optionHtml(options, selectedId, valuePrefix, tag = null) {
  return options
    .filter(([, , minVersion]) => !minVersion || !tag || versionAtLeast(tag, minVersion))
    .map(([id, label]) => {
      const value = `${valuePrefix}${id}`;
      return `<option value="${value}" ${id === selectedId ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function fillSelect(el, options, prefix, fallbackId, tag) {
  const previous = el.value;
  el.innerHTML = optionHtml(options, fallbackId, prefix, tag);
  if (previous && Array.from(el.options).some((option) => option.value === previous)) {
    el.value = previous;
  }
}

function populateStaticSelects(tag = null) {
  fillSelect($("loraRegion"), REGION_OPTIONS, "meshtastic_Config_LoRaConfig_RegionCode_", "EU_868", tag);
  fillSelect($("deviceRole"), ROLE_OPTIONS, "meshtastic_Config_DeviceConfig_Role_", "CLIENT", tag);
  fillSelect($("modemPreset"), PRESET_OPTIONS, "meshtastic_Config_LoRaConfig_ModemPreset_", "LONG_FAST", tag);
  fillSelect(
    $("rebroadcastMode"),
    REBROADCAST_OPTIONS,
    "meshtastic_Config_DeviceConfig_RebroadcastMode_",
    "CORE_PORTNUMS_ONLY",
    tag,
  );
  fillSelect(
    $("signaturePolicy"),
    SIGNATURE_POLICY_OPTIONS,
    "meshtastic_Config_SecurityConfig_PacketSignaturePolicy_",
    "PACKET_SIGNATURE_POLICY_BALANCED",
    tag,
  );
}

function numericOptionHtml(values, selected, labeller = String) {
  return values
    .map(
      (value) =>
        `<option value="${value}" ${value === selected ? "selected" : ""}>${escapeHtml(labeller(value))}</option>`,
    )
    .join("");
}

function range(min, max) {
  return Array.from({ length: max - min + 1 }, (_, index) => min + index);
}

async function loadBuildOptions() {
  state.buildOptions = await fetchJson("/api/build-options");
  const fields = state.buildOptions.customLora.fields;
  $("loraBandwidth").innerHTML = numericOptionHtml(
    fields.bandwidthKhz.choices,
    fields.bandwidthKhz.default,
    (value) => BANDWIDTH_LABELS[value] || String(value),
  );
  $("loraSpreadFactor").innerHTML = numericOptionHtml(
    range(fields.spreadFactor.min, fields.spreadFactor.max),
    fields.spreadFactor.default,
  );
  $("loraCodingRate").innerHTML = numericOptionHtml(
    range(fields.codingRate.min, fields.codingRate.max),
    fields.codingRate.default,
  );
  $("loraChannelNum").min = fields.channelNum.min;
  $("loraChannelNum").max = fields.channelNum.max;
  $("loraChannelNum").value = fields.channelNum.default;
  const frequency = fields.overrideFrequencyMhz;
  $("loraOverrideFreq").min = frequency.min;
  $("loraOverrideFreq").max = frequency.max;
  $("loraOverrideFreq").step = frequency.step;
  $("loraOverrideFreq").value = frequency.default;
  $("okToMqtt").checked = state.buildOptions.okToMqtt.default;
  renderTtlNotice();
}

function renderTtlNotice() {
  const days = state.buildOptions?.artifactTtlDays;
  if (!days) return;
  $("submitTtl").textContent = t("step7.ttl", { days });
  $("resultTtl").textContent = t("result.ttl", { days });
}

function syncAdvancedAvailability() {
  const tag = $("firmwareTag").value;
  const options = state.buildOptions;
  state.codeOptionsAvailable = Boolean(options && versionAtLeast(tag, options.minFirmwareVersion));
  state.codeOptionsNative = Boolean(options && versionAtLeast(tag, options.nativeSinceFirmwareVersion));
  state.maxChannels = options && versionAtLeast(tag, options.eightChannelsSinceFirmwareVersion) ? 8 : 3;
  document.querySelectorAll(".code-option").forEach((el) => {
    el.hidden = !state.codeOptionsAvailable;
  });
  document.querySelectorAll(".patch-only").forEach((el) => {
    el.hidden = state.codeOptionsNative;
  });
  $("advancedUnavailable").hidden = state.codeOptionsAvailable;
  syncCustomLora();
}

function syncCustomLora() {
  const enabled = state.codeOptionsAvailable && $("customLoraEnabled").checked;
  $("customLoraFields").hidden = !enabled;
  $("modemPreset").disabled = enabled;
  $("presetDisabledHint").hidden = !enabled;
}

function wifiSupported() {
  const family = state.deviceFamilies[$("deviceId").value];
  return !family || WIFI_FAMILIES.has(family);
}

// Recomputed from both conditions every time: a control hidden because the board
// has no WiFi must come back when the user picks a board that does.
function syncWifiAvailability() {
  const supported = wifiSupported();
  const inTemplate = (key) => state.templateKeys.size === 0 || state.templateKeys.has(key);
  const controls = Array.from($("wifiPanel").querySelectorAll("[data-pref-key]"));
  for (const el of controls) {
    el.hidden = !supported || !inTemplate(el.dataset.prefKey);
  }
  // Firmware that has no WiFi keys at all: drop the panel. Board with no WiFi
  // radio: keep it, so the note explaining the missing fields stays visible.
  $("wifiPanel").hidden = !controls.some((el) => inTemplate(el.dataset.prefKey));
  $("wifiUnsupported").hidden = supported;
}

function syncManagedMode() {
  const hasAdminKey = ["adminKey", "adminKey1", "adminKey2"].some((id) => $(id).value.trim() !== "");
  const checkbox = $("securityIsManaged");
  checkbox.disabled = !hasAdminKey;
  if (!hasAdminKey) checkbox.checked = false;
}

// Controls for keys the selected firmware template does not define are hidden; setPref drops them anyway.
function syncTemplateGatedControls() {
  for (const el of document.querySelectorAll("[data-pref-key]")) {
    el.hidden = state.templateKeys.size > 0 && !state.templateKeys.has(el.dataset.prefKey);
  }
  syncWifiAvailability();
}

async function loadDevices() {
  const { devices } = await fetchJson("/api/devices");
  state.deviceFamilies = Object.fromEntries(devices.map((device) => [device.id, device.family]));
  $("deviceId").innerHTML = devices
    .map((device) => `<option value="${escapeHtml(device.id)}">${escapeHtml(device.label)}</option>`)
    .join("");
  $("deviceId").addEventListener("change", syncWifiAvailability);
}

async function loadVersions(forceRefresh = false) {
  setStatusKey(forceRefresh ? "status.refreshingTags" : "status.loadingTags");
  const { versions } = await fetchJson(`/api/firmware-versions${forceRefresh ? "?refresh=1" : ""}`);
  if (!versions.length) {
    throw new Error(t("error.noVersions"));
  }
  $("firmwareTag").innerHTML = versions
    .map((version) => `<option value="${escapeHtml(version.tag)}">${escapeHtml(version.tag)}</option>`)
    .join("");
  await onFirmwareTagChange();
  setStatusKey("status.ready");
}

async function onFirmwareTagChange() {
  populateStaticSelects($("firmwareTag").value);
  syncAdvancedAvailability();
  await loadTemplate();
}

async function loadTemplate() {
  const tag = $("firmwareTag").value;
  if (!tag) return;
  const response = await fetch(`/api/prefs-template?tag=${encodeURIComponent(tag)}`);
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.error || t("error.template"));
  }
  const template = await response.text();
  state.templateKeys = extractTemplateKeys(template);
  state.templateExamples = extractTemplateExamples(template);
  // A key the previous tag had may not exist in this one.
  state.extraPrefs = state.extraPrefs.filter((row) => !row.key || state.templateKeys.has(row.key));
  syncTemplateGatedControls();
  if (!state.channels.length) {
    state.channels = [defaultChannel()];
  }
  if (state.channels.length > state.maxChannels) {
    state.channels = state.channels.slice(0, state.maxChannels);
  }
  renderChannels();
  renderExtraPrefs();
}

function extractTemplateKeys(template) {
  return new Set(Array.from(template.matchAll(/"(USERPREFS_[A-Z0-9_]+)"\s*:/g), (match) => match[1]));
}

// The template documents a sample value for most keys; show it as the placeholder
// so the free-form section hints at the shape each key expects.
function extractTemplateExamples(template) {
  const examples = {};
  for (const match of template.matchAll(/"(USERPREFS_[A-Z0-9_]+)"\s*:\s*("(?:[^"\\]|\\.)*")/g)) {
    try {
      examples[match[1]] = JSON.parse(match[2]);
    } catch (error) {
      // A malformed sample is not worth failing the page over.
    }
  }
  return examples;
}

function shortPrefKey(key) {
  return key.replace(/^USERPREFS_/, "");
}

function isFormManagedKey(key) {
  return FORM_MANAGED_KEYS.has(key) || /^USERPREFS_CHANNEL_\d+_/.test(key);
}

function availableExtraKeys(exceptIndex) {
  const taken = new Set(
    state.extraPrefs.filter((_row, index) => index !== exceptIndex).map((row) => row.key).filter(Boolean),
  );
  return Array.from(state.templateKeys)
    .filter((key) => !isFormManagedKey(key) && !taken.has(key))
    .sort();
}

function renderExtraPrefs() {
  $("extraRows").innerHTML = state.extraPrefs
    .map((row, index) => {
      const options = availableExtraKeys(index);
      if (row.key && !options.includes(row.key)) options.push(row.key);
      options.sort();
      return `
    <div class="extra-row" data-index="${index}">
      <label>
        ${escapeHtml(t("extra.key"))}
        <select data-field="key">
          <option value="">${escapeHtml(t("extra.choose"))}</option>
          ${options
            .map(
              (key) =>
                `<option value="${escapeHtml(key)}" ${key === row.key ? "selected" : ""}>${escapeHtml(shortPrefKey(key))}</option>`,
            )
            .join("")}
        </select>
      </label>
      <label>
        ${escapeHtml(t("extra.value"))}
        <input data-field="value" type="text" autocomplete="off" value="${escapeHtml(row.value)}"
          placeholder="${escapeHtml(state.templateExamples[row.key] || "")}">
      </label>
      <button class="btn btn-mini" type="button" data-action="remove-extra">${escapeHtml(t("channel.remove"))}</button>
    </div>`;
    })
    .join("");
  $("addExtraPref").disabled = !availableExtraKeys(-1).length;
  updatePrefsPreview();
}

function syncExtraFromInput(input) {
  const container = input.closest(".extra-row");
  if (!container) return;
  const row = state.extraPrefs[Number(container.dataset.index)];
  if (row) row[input.dataset.field] = input.value;
}

function channelMuteSupported() {
  return state.maxChannels === 8 || state.templateKeys.has("USERPREFS_CHANNEL_0_IS_MUTED");
}

function defaultChannel() {
  return {
    name: "LongFast",
    psk: "AQ==",
    precision: "14",
    downlink: false,
    uplink: true,
    muted: false,
  };
}

function renderChannels() {
  const withMute = channelMuteSupported();
  const canReorder = state.channels.length > 1;
  $("channelRows").innerHTML = state.channels.map((channel, index) => `
    <div class="channel-row" data-index="${index}">
      <button class="drag-handle" type="button" data-action="drag" ${canReorder ? "" : "disabled"}
        aria-label="${escapeHtml(t("channel.reorder"))}" title="${escapeHtml(t("channel.reorder"))}">⠿</button>
      <label>
        ${escapeHtml(t("channel.name"))}
        <input data-field="name" type="text" value="${escapeHtml(channel.name)}" autocomplete="off" required>
      </label>
      <label>
        ${escapeHtml(t("channel.psk"))}
        <input data-field="psk" type="text" value="${escapeHtml(channel.psk)}" autocomplete="off" placeholder="AQ==">
      </label>
      <label class="precision-cell">
        ${escapeHtml(t("channel.precision"))}
        <input data-field="precision" type="range" min="0" max="${PRECISION_STEPS.length - 1}"
          value="${precisionStepIndex(channel.precision)}">
        <small class="field-hint" data-precision-label>${escapeHtml(precisionLabel(channel.precision))}</small>
      </label>
      <label class="check-line">
        <input data-field="downlink" type="checkbox" ${channel.downlink ? "checked" : ""}>
        <span>${escapeHtml(t("channel.downlink"))}</span>
      </label>
      <label class="check-line">
        <input data-field="uplink" type="checkbox" ${channel.uplink ? "checked" : ""}>
        <span>${escapeHtml(t("channel.uplink"))}</span>
      </label>
      ${withMute ? `
      <label class="check-line">
        <input data-field="muted" type="checkbox" ${channel.muted ? "checked" : ""}>
        <span>${escapeHtml(t("channel.muted"))}</span>
      </label>` : ""}
      <button class="btn btn-mini" type="button" data-action="remove" ${state.channels.length === 1 ? "disabled" : ""}>${escapeHtml(t("channel.remove"))}</button>
    </div>
  `).join("");
  $("addChannel").disabled = state.channels.length >= state.maxChannels;
  $("channelHint").textContent = t("step4.hint", { max: state.maxChannels });
  updatePrefsPreview();
}

function precisionStepIndex(precision) {
  const index = PRECISION_STEPS.indexOf(Number(precision));
  return index >= 0 ? index : DEFAULT_PRECISION_INDEX;
}

function syncChannelFromInput(input) {
  const row = input.closest(".channel-row");
  if (!row) return;
  const channel = state.channels[Number(row.dataset.index)];
  if (!channel) return;
  const field = input.dataset.field;
  if (field === "precision") {
    // The slider walks PRECISION_STEPS; the stored value stays the firmware one.
    channel.precision = String(PRECISION_STEPS[Number(input.value)]);
    const label = row.querySelector("[data-precision-label]");
    if (label) label.textContent = precisionLabel(channel.precision);
    return;
  }
  channel[field] = input.type === "checkbox" ? input.checked : input.value;
}

// Reordering channel 0 changes the primary channel, so the whole row order matters.
// Pointer events (not HTML5 drag) because they also work on touch screens.
let channelDrag = null;

function onChannelDragStart(event) {
  const handle = event.target.closest("[data-action='drag']");
  if (!handle || handle.disabled) return;
  const row = handle.closest(".channel-row");
  if (!row) return;
  event.preventDefault();
  handle.setPointerCapture(event.pointerId);
  row.classList.add("dragging");
  channelDrag = { row, pointerId: event.pointerId };
}

function onChannelDragMove(event) {
  if (!channelDrag || event.pointerId !== channelDrag.pointerId) return;
  const rows = Array.from($("channelRows").querySelectorAll(".channel-row"));
  const target = rows.find((row) => {
    if (row === channelDrag.row) return false;
    const box = row.getBoundingClientRect();
    return event.clientY >= box.top && event.clientY <= box.bottom;
  });
  if (!target) return;
  const box = target.getBoundingClientRect();
  const after = event.clientY > box.top + box.height / 2;
  target.parentNode.insertBefore(channelDrag.row, after ? target.nextSibling : target);
}

function onChannelDragEnd(event) {
  if (!channelDrag || event.pointerId !== channelDrag.pointerId) return;
  channelDrag.row.classList.remove("dragging");
  channelDrag = null;
  const order = Array.from(
    $("channelRows").querySelectorAll(".channel-row"),
    (row) => Number(row.dataset.index),
  );
  state.channels = order.map((index) => state.channels[index]);
  renderChannels();
}

function bytesToByteArray(bytes) {
  if (!bytes.length) return "{}";
  return `{ ${Array.from(bytes, (byte) => `0x${byte.toString(16).padStart(2, "0")}`).join(", ")} }`;
}

function base64ToBytes(value, label, expectedLength = null) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  try {
    const binary = atob(trimmed);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const normalized = btoa(String.fromCharCode(...bytes)).replace(/=+$/, "");
    if (trimmed.replace(/=+$/, "") !== normalized) {
      throw new Error("not canonical");
    }
    if (expectedLength !== null && bytes.length !== expectedLength) {
      throw new Error("wrong length");
    }
    return bytes;
  } catch (error) {
    throw new Error(
      expectedLength === null
        ? t("error.base64", { label })
        : t("error.base64Length", { label, bytes: expectedLength }),
    );
  }
}

function setPref(prefs, key, value) {
  if (!state.templateKeys.size || state.templateKeys.has(key) || isExtraChannelKey(key)) {
    prefs[key] = value;
  }
}

// Firmware >= 2.8.0 reads channels 0..7 even though the template only documents the first three.
function isExtraChannelKey(key) {
  return state.maxChannels === 8 && /^USERPREFS_CHANNEL_[0-7]_[A-Z_]+$/.test(key);
}

function setOptionalPref(prefs, key, rawValue) {
  const value = String(rawValue).trim();
  if (value !== "") setPref(prefs, key, value);
}

function validateShortName() {
  const input = $("shortName");
  const byteLength = encoder.encode(input.value).length;
  $("shortNameBytes").textContent = `${byteLength}/4 bytes`;
  input.classList.toggle("fieldError", byteLength > 4);
  if (byteLength > 4) {
    throw new Error(t("error.shortName"));
  }
}

// bin/platformio-custom.py only quotes a value that does not already look like a
// number, bool, enum, hex or byte array, so these would reach the compiler bare.
function validateCompilesAsString(value, label) {
  const looksUnquoted =
    value.startsWith("{") ||
    /^-?[\d.]+$/.test(value) ||
    /^0[xX][0-9a-fA-F]+$/.test(value) ||
    value === "true" ||
    value === "false" ||
    value.startsWith("meshtastic_");
  if (looksUnquoted) {
    throw new Error(t("error.mustBeText", { label }));
  }
  return value;
}

function validateMaxBytes(value, label, maxBytes) {
  if (encoder.encode(value).length > maxBytes) {
    throw new Error(t("error.maxBytes", { label, bytes: maxBytes }));
  }
  return value;
}

function validateChannel(channel, index) {
  const precision = Number(channel.precision);
  if (!channel.name.trim()) {
    throw new Error(t("error.channelName", { n: index + 1 }));
  }
  if (!Number.isInteger(precision) || precision < 0 || precision > 32) {
    throw new Error(t("error.channelPrecision", { n: index + 1 }));
  }
  return {
    name: channel.name.trim(),
    pskBytes: base64ToBytes(channel.psk, t("label.channelKey", { n: index + 1 })),
    precision: String(precision),
  };
}

function buildPrefs() {
  validateShortName();
  const prefs = {};

  setPref(prefs, "USERPREFS_CONFIG_OWNER_LONG_NAME", $("longName").value.trim());
  setPref(prefs, "USERPREFS_CONFIG_OWNER_SHORT_NAME", $("shortName").value.trim());
  setPref(prefs, "USERPREFS_CONFIG_LORA_REGION", $("loraRegion").value);
  setPref(prefs, "USERPREFS_CONFIG_DEVICE_ROLE", $("deviceRole").value);
  setPref(prefs, "USERPREFS_LORACONFIG_MODEM_PRESET", $("modemPreset").value);
  setPref(prefs, "USERPREFS_TZ_STRING", $("tzString").value.trim());
  setOptionalPref(prefs, "USERPREFS_LORACONFIG_TX_POWER", $("loraTxPower").value);

  setPref(prefs, "USERPREFS_CONFIG_DEVICE_REBROADCAST_MODE", $("rebroadcastMode").value);
  setOptionalPref(prefs, "USERPREFS_CONFIG_DEVICE_NODE_INFO_BROADCAST_SECS", $("nodeInfoSecs").value);
  setOptionalPref(prefs, "USERPREFS_CONFIG_DEVICE_TELEM_UPDATE_INTERVAL", $("deviceTelemInterval").value);

  const mqttAddress = $("mqttAddress").value.trim();
  if (mqttAddress) {
    validateMaxBytes(mqttAddress, t("label.mqttAddress"), 61);
    setPref(prefs, "USERPREFS_MQTT_ADDRESS", `'${mqttAddress.replace(/'/g, "")}'`);
  }
  if ($("mqttEnabled").checked) {
    setPref(prefs, "USERPREFS_MQTT_ENABLED", "1");
  }
  const mqttUsername = $("mqttUsername").value.trim();
  if (mqttUsername) {
    setPref(prefs, "USERPREFS_MQTT_USERNAME", validateMaxBytes(mqttUsername, t("label.mqttUsername"), 63));
  }
  const mqttPassword = $("mqttPassword").value;
  if (mqttPassword) {
    setPref(prefs, "USERPREFS_MQTT_PASSWORD", validateMaxBytes(mqttPassword, t("label.mqttPassword"), 31));
  }
  const mqttRoot = $("mqttRootTopic").value.trim();
  if (mqttRoot) {
    setPref(prefs, "USERPREFS_MQTT_ROOT_TOPIC", validateMaxBytes(mqttRoot, t("label.mqttRoot"), 31));
  }
  setPref(prefs, "USERPREFS_CONFIG_LORA_IGNORE_MQTT", String($("ignoreMqtt").checked));

  if ($("blePinEnabled").checked) {
    setOptionalPref(prefs, "USERPREFS_FIXED_BLUETOOTH", $("blePin").value);
  }
  // A board with no WiFi radio gets no WiFi macros, whatever is still typed in the form.
  if (wifiSupported()) {
    buildWifiPrefs(prefs);
  }

  setPref(prefs, "USERPREFS_MQTT_ENCRYPTION_ENABLED", String($("mqttEncryption").checked));
  setPref(prefs, "USERPREFS_MQTT_TLS_ENABLED", String($("mqttTls").checked));

  [
    ["adminKey", "USERPREFS_USE_ADMIN_KEY_0", t("label.adminKey")],
    ["adminKey1", "USERPREFS_USE_ADMIN_KEY_1", t("label.adminKey1")],
    ["adminKey2", "USERPREFS_USE_ADMIN_KEY_2", t("label.adminKey2")],
  ].forEach(([id, key, label]) => {
    const bytes = base64ToBytes($(id).value, label, 32);
    if (bytes) setPref(prefs, key, bytesToByteArray(bytes));
  });
  setPref(prefs, "USERPREFS_CONFIG_SECURITY_PACKET_SIGNATURE_POLICY", $("signaturePolicy").value);
  if ($("securityIsManaged").checked) {
    setPref(prefs, "USERPREFS_CONFIG_SECURITY_IS_MANAGED", "true");
  }

  setPref(prefs, "USERPREFS_CHANNELS_TO_WRITE", String(state.channels.length));
  const withMute = channelMuteSupported();
  state.channels.forEach((channel, index) => {
    const valid = validateChannel(channel, index);
    setPref(prefs, `USERPREFS_CHANNEL_${index}_NAME`, valid.name);
    setPref(prefs, `USERPREFS_CHANNEL_${index}_PRECISION`, valid.precision);
    if (valid.pskBytes) {
      setPref(prefs, `USERPREFS_CHANNEL_${index}_PSK`, bytesToByteArray(valid.pskBytes));
    }
    setPref(prefs, `USERPREFS_CHANNEL_${index}_DOWNLINK_ENABLED`, String(Boolean(channel.downlink)));
    setPref(prefs, `USERPREFS_CHANNEL_${index}_UPLINK_ENABLED`, String(Boolean(channel.uplink)));
    if (withMute) {
      setPref(prefs, `USERPREFS_CHANNEL_${index}_IS_MUTED`, String(Boolean(channel.muted)));
    }
  });

  for (const row of state.extraPrefs) {
    const value = row.value.trim();
    if (row.key && value) setPref(prefs, row.key, value);
  }

  return prefs;
}

function buildWifiPrefs(prefs) {
  if ($("wifiEnabled").checked) {
    setPref(prefs, "USERPREFS_NETWORK_WIFI_ENABLED", "true");
  }
  const ssid = $("wifiSsid").value.trim();
  if (ssid) {
    validateMaxBytes(ssid, t("label.wifiSsid"), 32);
    setPref(prefs, "USERPREFS_NETWORK_WIFI_SSID", validateCompilesAsString(ssid, t("label.wifiSsid")));
  }
  const psk = $("wifiPsk").value;
  if (psk) {
    validateMaxBytes(psk, t("label.wifiPsk"), 64);
    setPref(prefs, "USERPREFS_NETWORK_WIFI_PSK", validateCompilesAsString(psk, t("label.wifiPsk")));
  }
}

function buildCodeOptions() {
  if (!state.codeOptionsAvailable) return null;
  const options = { okToMqtt: $("okToMqtt").checked };
  if ($("customLoraEnabled").checked) {
    options.customLora = {
      bandwidthKhz: Number($("loraBandwidth").value),
      spreadFactor: Number($("loraSpreadFactor").value),
      codingRate: Number($("loraCodingRate").value),
      channelNum: Number($("loraChannelNum").value),
      overrideFrequencyMhz: Number($("loraOverrideFreq").value),
    };
  }
  return options;
}

function describeCodeOptions(options) {
  if (!options) return "";
  const parts = [];
  if (options.okToMqtt !== undefined) {
    parts.push(`ok_to_mqtt=${options.okToMqtt}`);
  }
  if (options.customLora) {
    const lora = options.customLora;
    const bandwidth = BANDWIDTH_LABELS[lora.bandwidthKhz] || lora.bandwidthKhz;
    parts.push(`BW ${bandwidth} kHz / SF ${lora.spreadFactor} / CR ${lora.codingRate} / slot ${lora.channelNum}`);
    if (lora.overrideFrequencyMhz) {
      parts.push(`${lora.overrideFrequencyMhz} MHz`);
    }
  }
  return parts.join(" · ");
}

// The advanced options are not userPrefs keys: the server expands them into these
// macros and merges them after the user overrides. Show them so the preview is honest.
function codeOptionMacros() {
  const options = buildCodeOptions();
  const spec = state.buildOptions;
  if (!options || !spec) return [];
  const macros = [];
  if (options.okToMqtt !== undefined) {
    macros.push([state.codeOptionsNative ? spec.okToMqtt.nativeMacro : spec.okToMqtt.macro, String(options.okToMqtt)]);
  }
  if (options.customLora) {
    macros.push([spec.customLora.usePresetMacro, "false"]);
    for (const [name, field] of Object.entries(spec.customLora.fields)) {
      macros.push([field.macro, String(options.customLora[name])]);
    }
  }
  return macros;
}

function prefsPreviewText(prefs) {
  const json = JSON.stringify(prefs, null, 2);
  const macros = codeOptionMacros();
  if (!macros.length) return `${json}\n`;
  const comment = [
    "",
    `  // ${t("preview.injected")}`,
    ...macros.map(([key, value]) => `  // "${key}": "${value}"`),
  ].join("\n");
  // Comments sit inside the object, so the submitted text still parses as JSONC.
  return `${json.replace(/\n\}$/, `${comment}\n}`)}\n`;
}

function updatePrefsPreview() {
  try {
    syncManagedMode();
    const prefs = buildPrefs();
    $("prefsJsonc").value = prefsPreviewText(prefs);
    if (state.statusIsError) {
      setStatusKey("status.ready");
    }
    return true;
  } catch (error) {
    setStatus(error.message, true);
    return false;
  }
}

async function submitBuild(event) {
  event.preventDefault();
  if (!updatePrefsPreview()) return;
  $("submitBuild").disabled = true;
  try {
    setStatusKey("status.creating");
    const payload = {
      deviceId: $("deviceId").value,
      firmwareTag: $("firmwareTag").value,
      prefsJsonc: $("prefsJsonc").value,
    };
    const codeOptions = buildCodeOptions();
    if (codeOptions) {
      payload.codeOptions = codeOptions;
    }
    const result = await fetchJson("/api/builds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    history.replaceState(null, "", `/?build=${encodeURIComponent(result.build.token)}`);
    showBuild(result.build, result.downloadUrl, result.buildUrl);
    startPolling(result.build.token);
    setStatusKey("status.queued");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    $("submitBuild").disabled = false;
  }
}

function showBuild(build, downloadUrl = null, buildUrl = null) {
  state.lastBuild = build;
  if (downloadUrl) state.lastDownloadUrl = downloadUrl;
  if (buildUrl) state.lastBuildUrl = buildUrl;
  $("result").hidden = false;
  $("buildStatus").textContent = build.status;
  $("buildToken").textContent = build.token;

  const url = state.lastBuildUrl || `${location.origin}/?build=${build.token}`;
  $("buildUrl").textContent = url;
  $("buildUrl").href = url;

  const summary = describeCodeOptions(build.codeOptions);
  $("buildOptionsRow").hidden = !summary;
  $("buildOptions").textContent = summary;

  const link = $("downloadLink");
  if (build.status === "succeeded") {
    link.textContent = t("result.downloadZip");
    link.href = state.lastDownloadUrl || `/download/${build.token}`;
  } else if (build.status === "failed") {
    link.textContent = build.error || t("result.failed");
    link.removeAttribute("href");
  } else {
    link.textContent = t("result.pending");
    link.removeAttribute("href");
  }
}

function startPolling(token) {
  state.currentBuildToken = token;
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const { build } = await fetchJson(`/api/builds/${token}`);
      showBuild(build);
      if (["succeeded", "failed", "expired"].includes(build.status)) {
        clearInterval(state.pollTimer);
      }
    } catch (error) {
      setStatus(error.message, true);
    }
  }, 5000);
}

async function loadExistingBuild(token) {
  setStatusKey("status.loadingBuild");
  const { build } = await fetchJson(`/api/builds/${encodeURIComponent(token)}`);
  showBuild(build);
  if (!["succeeded", "failed", "expired"].includes(build.status)) {
    startPolling(build.token);
  }
  setStatusKey("status.ready");
}

function bindEvents() {
  $("buildForm").addEventListener("submit", submitBuild);
  $("firmwareTag").addEventListener("change", () => {
    onFirmwareTagChange().catch((error) => setStatus(error.message, true));
  });
  $("refreshVersions").addEventListener("click", () => loadVersions(true).catch((error) => setStatus(error.message, true)));
  $("customLoraEnabled").addEventListener("change", syncCustomLora);
  $("copyBuildUrl").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("buildUrl").textContent);
      setStatusKey("result.copied");
    } catch (error) {
      setStatus(error.message, true);
    }
  });
  $("addChannel").addEventListener("click", () => {
    if (state.channels.length >= state.maxChannels) return;
    state.channels.push({
      ...defaultChannel(),
      name: `${t("channel.defaultName")} ${state.channels.length + 1}`,
      uplink: false,
    });
    renderChannels();
  });
  $("channelRows").addEventListener("input", (event) => {
    if (!(event.target instanceof HTMLInputElement)) return;
    syncChannelFromInput(event.target);
    updatePrefsPreview();
  });
  $("channelRows").addEventListener("change", (event) => {
    if (!(event.target instanceof HTMLInputElement)) return;
    syncChannelFromInput(event.target);
    updatePrefsPreview();
  });
  $("channelRows").addEventListener("pointerdown", onChannelDragStart);
  $("channelRows").addEventListener("pointermove", onChannelDragMove);
  $("channelRows").addEventListener("pointerup", onChannelDragEnd);
  $("channelRows").addEventListener("pointercancel", onChannelDragEnd);
  $("channelRows").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action='remove']");
    if (!button) return;
    state.channels.splice(Number(button.closest(".channel-row").dataset.index), 1);
    renderChannels();
  });
  $("addExtraPref").addEventListener("click", () => {
    state.extraPrefs.push({ key: "", value: "" });
    renderExtraPrefs();
  });
  $("extraRows").addEventListener("change", (event) => {
    if (!event.target.matches("select[data-field]")) return;
    syncExtraFromInput(event.target);
    renderExtraPrefs();
  });
  $("extraRows").addEventListener("input", (event) => {
    if (!event.target.matches("input[data-field]")) return;
    syncExtraFromInput(event.target);
    updatePrefsPreview();
  });
  $("extraRows").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action='remove-extra']");
    if (!button) return;
    state.extraPrefs.splice(Number(button.closest(".extra-row").dataset.index), 1);
    renderExtraPrefs();
  });
  document.querySelectorAll("input, select").forEach((input) => {
    if (input.closest("#channelRows") || input.closest("#extraRows")) return;
    input.addEventListener("input", updatePrefsPreview);
    input.addEventListener("change", updatePrefsPreview);
  });
  document.querySelectorAll("[data-tz]").forEach((button) => {
    button.addEventListener("click", () => {
      $("tzString").value = button.dataset.tz;
      updatePrefsPreview();
    });
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => setLang(button.dataset.lang));
  });
  document.addEventListener("languagechange", () => {
    renderTtlNotice();
    renderExtraPrefs();
    renderChannels();
    if (state.statusKey) setStatusKey(state.statusKey);
    if (state.lastBuild) showBuild(state.lastBuild);
  });
}

applyI18n();
populateStaticSelects();
bindEvents();
state.channels = [defaultChannel()];
renderChannels();

const requestedBuild = new URLSearchParams(location.search).get("build");
Promise.all([loadDevices(), loadBuildOptions()])
  .then(() => loadVersions(false))
  .then(() => (requestedBuild ? loadExistingBuild(requestedBuild) : undefined))
  .catch((error) => setStatus(error.message, true));
