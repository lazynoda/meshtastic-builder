const state = {
  currentBuildToken: null,
  pollTimer: null,
  templateKeys: new Set(),
  channels: [],
  statusIsError: false,
  statusKey: null,
  buildOptions: null,
  codeOptionsAvailable: false,
  lastBuild: null,
  lastDownloadUrl: null,
};

const $ = (id) => document.getElementById(id);
const encoder = new TextEncoder();

const REGION_OPTIONS = [
  ["EU_868", "EU 868 MHz"],
  ["EU_433", "EU 433 MHz"],
  ["EU_866", "EU 866 MHz"],
  ["EU_874", "EU 874 MHz"],
  ["EU_917", "EU 917 MHz"],
  ["EU_N_868", "EU narrow 868 MHz"],
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
  ["ITU1_2M", "ITU region 1, 2 m"],
  ["ITU23_2M", "ITU region 2/3, 2 m"],
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
  ["SHORT_FAST", "Short fast"],
  ["SHORT_SLOW", "Short slow"],
  ["SHORT_TURBO", "Short turbo"],
  ["LONG_TURBO", "Long turbo"],
  ["LITE_FAST", "Lite fast"],
  ["LITE_SLOW", "Lite slow"],
  ["NARROW_FAST", "Narrow fast"],
  ["NARROW_SLOW", "Narrow slow"],
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

function optionHtml(options, selectedId, valuePrefix) {
  return options
    .map(([id, label]) => {
      const value = `${valuePrefix}${id}`;
      return `<option value="${value}" ${id === selectedId ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function populateStaticSelects() {
  $("loraRegion").innerHTML = optionHtml(
    REGION_OPTIONS,
    "EU_868",
    "meshtastic_Config_LoRaConfig_RegionCode_",
  );
  $("deviceRole").innerHTML = optionHtml(
    ROLE_OPTIONS,
    "CLIENT",
    "meshtastic_Config_DeviceConfig_Role_",
  );
  $("modemPreset").innerHTML = optionHtml(
    PRESET_OPTIONS,
    "LONG_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_",
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

function syncAdvancedAvailability() {
  const tag = $("firmwareTag").value;
  state.codeOptionsAvailable = Boolean(
    state.buildOptions && versionAtLeast(tag, state.buildOptions.minFirmwareVersion),
  );
  $("advancedControls").hidden = !state.codeOptionsAvailable;
  $("advancedUnavailable").hidden = state.codeOptionsAvailable;
  syncCustomLora();
}

function syncCustomLora() {
  const enabled = state.codeOptionsAvailable && $("customLoraEnabled").checked;
  $("customLoraFields").hidden = !enabled;
  $("modemPreset").disabled = enabled;
  $("presetDisabledHint").hidden = !enabled;
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
  syncAdvancedAvailability();
  await loadTemplate();
  setStatusKey("status.ready");
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
  if (!state.channels.length) {
    state.channels = [defaultChannel()];
    renderChannels();
  }
  updatePrefsPreview();
}

function extractTemplateKeys(template) {
  return new Set(Array.from(template.matchAll(/"(USERPREFS_[A-Z0-9_]+)"\s*:/g), (match) => match[1]));
}

function defaultChannel() {
  return {
    name: "LongFast",
    psk: "AQ==",
    precision: "14",
    downlink: false,
    uplink: true,
  };
}

function renderChannels() {
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
      <button class="btn btn-mini" type="button" data-action="remove" ${state.channels.length === 1 ? "disabled" : ""}>${escapeHtml(t("channel.remove"))}</button>
    </div>
  `).join("");
  $("addChannel").disabled = state.channels.length >= 3;
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
  if (!state.templateKeys.size || state.templateKeys.has(key)) {
    prefs[key] = value;
  }
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

  const mqttAddress = $("mqttAddress").value.trim();
  if (mqttAddress) {
    setPref(prefs, "USERPREFS_MQTT_ADDRESS", `'${mqttAddress.replace(/'/g, "")}'`);
  }
  if ($("mqttEnabled").checked) {
    setPref(prefs, "USERPREFS_MQTT_ENABLED", "1");
  }

  const adminKey = base64ToBytes($("adminKey").value, t("label.adminKey"), 32);
  if (adminKey) {
    setPref(prefs, "USERPREFS_USE_ADMIN_KEY_0", bytesToByteArray(adminKey));
  }

  setPref(prefs, "USERPREFS_CHANNELS_TO_WRITE", String(state.channels.length));
  state.channels.forEach((channel, index) => {
    const valid = validateChannel(channel, index);
    setPref(prefs, `USERPREFS_CHANNEL_${index}_NAME`, valid.name);
    setPref(prefs, `USERPREFS_CHANNEL_${index}_PRECISION`, valid.precision);
    if (valid.pskBytes) {
      setPref(prefs, `USERPREFS_CHANNEL_${index}_PSK`, bytesToByteArray(valid.pskBytes));
    }
    setPref(prefs, `USERPREFS_CHANNEL_${index}_DOWNLINK_ENABLED`, String(Boolean(channel.downlink)));
    setPref(prefs, `USERPREFS_CHANNEL_${index}_UPLINK_ENABLED`, String(Boolean(channel.uplink)));
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
      email: $("email").value,
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
    showBuild(result.build, result.downloadUrl);
    startPolling(result.build.token);
    setStatusKey("status.queued");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    $("submitBuild").disabled = false;
  }
}

function showBuild(build, downloadUrl = null) {
  state.lastBuild = build;
  if (downloadUrl) state.lastDownloadUrl = downloadUrl;
  $("result").hidden = false;
  $("buildStatus").textContent = build.status;
  $("buildToken").textContent = build.token;
  $("shareLink").textContent = `${location.origin}/?build=${build.token}`;

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
    syncAdvancedAvailability();
    loadTemplate().catch((error) => setStatus(error.message, true));
  });
  $("refreshVersions").addEventListener("click", () => loadVersions(true).catch((error) => setStatus(error.message, true)));
  $("customLoraEnabled").addEventListener("change", syncCustomLora);
  $("addChannel").addEventListener("click", () => {
    if (state.channels.length >= 3) return;
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
