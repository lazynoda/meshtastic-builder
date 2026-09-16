const state = {
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
    "ALL",
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
    (value) => `4/${value}`,
  );
  $("loraChannelNum").min = fields.channelNum.min;
  $("loraChannelNum").max = fields.channelNum.max;
  $("loraChannelNum").value = fields.channelNum.default;
  $("okToMqtt").checked = state.buildOptions.okToMqtt.default;
}

function syncAdvancedAvailability() {
  const tag = $("firmwareTag").value;
  const options = state.buildOptions;
  state.codeOptionsAvailable = Boolean(options && versionAtLeast(tag, options.minFirmwareVersion));
  state.codeOptionsNative = Boolean(options && versionAtLeast(tag, options.nativeSinceFirmwareVersion));
  state.maxChannels = options && versionAtLeast(tag, options.eightChannelsSinceFirmwareVersion) ? 8 : 3;
  $("advancedControls").hidden = !state.codeOptionsAvailable;
  $("advancedUnavailable").hidden = state.codeOptionsAvailable;
  $("advancedBadge").hidden = state.codeOptionsNative;
  $("advancedWarning").hidden = state.codeOptionsNative;
  $("advancedNative").hidden = !state.codeOptionsNative;
  $("advancedPanel").classList.toggle("panel-experimental", !state.codeOptionsNative);
  syncCustomLora();
}

function syncCustomLora() {
  const enabled = state.codeOptionsAvailable && $("customLoraEnabled").checked;
  $("customLoraFields").hidden = !enabled;
  $("modemPreset").disabled = enabled;
  $("presetDisabledHint").hidden = !enabled;
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
  $("behaviourPanel").hidden = Array.from(
    $("behaviourPanel").querySelectorAll("[data-pref-key]"),
  ).every((el) => el.hidden);
}

async function loadDevices() {
  const { devices } = await fetchJson("/api/devices");
  $("deviceId").innerHTML = devices
    .map((device) => `<option value="${escapeHtml(device.id)}">${escapeHtml(device.label)}</option>`)
    .join("");
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
  syncTemplateGatedControls();
  if (!state.channels.length) {
    state.channels = [defaultChannel()];
  }
  if (state.channels.length > state.maxChannels) {
    state.channels = state.channels.slice(0, state.maxChannels);
  }
  renderChannels();
}

function extractTemplateKeys(template) {
  return new Set(Array.from(template.matchAll(/"(USERPREFS_[A-Z0-9_]+)"\s*:/g), (match) => match[1]));
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
  $("channelRows").innerHTML = state.channels.map((channel, index) => `
    <div class="channel-row" data-index="${index}">
      <label>
        ${escapeHtml(t("channel.name"))}
        <input data-field="name" type="text" value="${escapeHtml(channel.name)}" autocomplete="off" required>
      </label>
      <label>
        ${escapeHtml(t("channel.psk"))}
        <input data-field="psk" type="text" value="${escapeHtml(channel.psk)}" autocomplete="off" placeholder="AQ==">
      </label>
      <label>
        ${escapeHtml(t("channel.precision"))}
        <input data-field="precision" type="number" min="0" max="32" value="${escapeHtml(channel.precision)}">
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

function syncChannelFromInput(input) {
  const row = input.closest(".channel-row");
  if (!row) return;
  const channel = state.channels[Number(row.dataset.index)];
  if (!channel) return;
  const field = input.dataset.field;
  channel[field] = input.type === "checkbox" ? input.checked : input.value;
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
  setOptionalPref(prefs, "USERPREFS_CONFIG_ENV_TELEM_UPDATE_INTERVAL", $("envTelemInterval").value);
  if ($("envMeasurementEnabled").checked) {
    setPref(prefs, "USERPREFS_CONFIG_ENVIRONMENT_MEASUREMENT_ENABLED", "true");
  }

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

  return prefs;
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
    parts.push(`BW ${bandwidth} kHz / SF ${lora.spreadFactor} / CR 4/${lora.codingRate} / slot ${lora.channelNum}`);
  }
  return parts.join(" · ");
}

function updatePrefsPreview() {
  try {
    syncManagedMode();
    const prefs = buildPrefs();
    $("prefsJsonc").value = `${JSON.stringify(prefs, null, 2)}\n`;
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
  $("channelRows").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action='remove']");
    if (!button) return;
    state.channels.splice(Number(button.closest(".channel-row").dataset.index), 1);
    renderChannels();
  });
  document.querySelectorAll("input, select").forEach((input) => {
    if (input.closest("#channelRows")) return;
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
