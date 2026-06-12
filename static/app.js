const state = {
  currentBuildToken: null,
  pollTimer: null,
  templateKeys: new Set(),
  channels: [],
  statusIsError: false,
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

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function setStatus(message, isError = false) {
  const el = $("statusText");
  el.textContent = message;
  el.style.color = isError ? "var(--danger)" : "var(--muted)";
  state.statusIsError = isError;
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

async function loadDevices() {
  const { devices } = await fetchJson("/api/devices");
  $("deviceId").innerHTML = devices
    .map((device) => `<option value="${escapeHtml(device.id)}">${escapeHtml(device.label)}</option>`)
    .join("");
}

async function loadVersions(forceRefresh = false) {
  setStatus(forceRefresh ? "Actualizando tags..." : "Cargando tags...");
  const { versions } = await fetchJson(`/api/firmware-versions${forceRefresh ? "?refresh=1" : ""}`);
  if (!versions.length) {
    throw new Error("No hay versiones soportadas en cache.");
  }
  $("firmwareTag").innerHTML = versions
    .map((version) => `<option value="${escapeHtml(version.tag)}">${escapeHtml(version.tag)}</option>`)
    .join("");
  await loadTemplate();
  setStatus("Listo.");
}

async function loadTemplate() {
  const tag = $("firmwareTag").value;
  if (!tag) return;
  const response = await fetch(`/api/prefs-template?tag=${encodeURIComponent(tag)}`);
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.error || "No se pudo cargar userPrefs.jsonc.");
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
    <div class="channelRow" data-index="${index}">
      <label>
        Nombre
        <input data-field="name" type="text" value="${escapeHtml(channel.name)}" autocomplete="off" required>
      </label>
      <label>
        Clave (base64)
        <input data-field="psk" type="text" value="${escapeHtml(channel.psk)}" autocomplete="off" placeholder="AQ==">
      </label>
      <label>
        Precision
        <input data-field="precision" type="number" min="0" max="32" value="${escapeHtml(channel.precision)}">
      </label>
      <label class="toggleCell">
        <input data-field="downlink" type="checkbox" ${channel.downlink ? "checked" : ""}>
        Downlink
      </label>
      <label class="toggleCell">
        <input data-field="uplink" type="checkbox" ${channel.uplink ? "checked" : ""}>
        Uplink
      </label>
      <button class="removeChannel" type="button" data-action="remove" ${state.channels.length === 1 ? "disabled" : ""}>Quitar</button>
    </div>
  `).join("");
  $("addChannel").disabled = state.channels.length >= 3;
  updatePrefsPreview();
}

function syncChannelFromInput(input) {
  const row = input.closest(".channelRow");
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
    const suffix = expectedLength === null ? "valido" : `valido de ${expectedLength} bytes`;
    throw new Error(`${label} debe estar en base64 ${suffix}.`);
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
    throw new Error("El nombre corto no puede superar 4 bytes.");
  }
}

function validateChannel(channel, index) {
  const label = `La clave del canal ${index + 1}`;
  const precision = Number(channel.precision);
  if (!channel.name.trim()) {
    throw new Error(`El canal ${index + 1} necesita nombre.`);
  }
  if (!Number.isInteger(precision) || precision < 0 || precision > 32) {
    throw new Error(`La precision del canal ${index + 1} debe estar entre 0 y 32.`);
  }
  return {
    name: channel.name.trim(),
    pskBytes: base64ToBytes(channel.psk, label),
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

  const adminKey = base64ToBytes($("adminKey").value, "La clave de administracion remota", 32);
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

function updatePrefsPreview() {
  try {
    const prefs = buildPrefs();
    $("prefsJsonc").value = `${JSON.stringify(prefs, null, 2)}\n`;
    if (state.statusIsError) {
      setStatus("Listo.");
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
    setStatus("Creando peticion...");
    const payload = {
      email: $("email").value,
      deviceId: $("deviceId").value,
      firmwareTag: $("firmwareTag").value,
      prefsJsonc: $("prefsJsonc").value,
    };
    const result = await fetchJson("/api/builds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showBuild(result.build, result.downloadUrl);
    startPolling(result.build.token);
    setStatus("Peticion en cola.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    $("submitBuild").disabled = false;
  }
}

function showBuild(build, downloadUrl = null) {
  $("result").hidden = false;
  $("buildStatus").textContent = build.status;
  $("buildToken").textContent = build.token;
  const link = $("downloadLink");
  if (build.status === "succeeded") {
    link.textContent = "Descargar ZIP";
    link.href = downloadUrl || `/download/${build.token}`;
  } else if (build.status === "failed") {
    link.textContent = build.error || "La compilacion fallo";
    link.removeAttribute("href");
  } else {
    link.textContent = "Disponible al finalizar";
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

function bindEvents() {
  $("buildForm").addEventListener("submit", submitBuild);
  $("firmwareTag").addEventListener("change", () => loadTemplate().catch((error) => setStatus(error.message, true)));
  $("refreshVersions").addEventListener("click", () => loadVersions(true).catch((error) => setStatus(error.message, true)));
  $("addChannel").addEventListener("click", () => {
    if (state.channels.length >= 3) return;
    state.channels.push({ ...defaultChannel(), name: `Canal ${state.channels.length + 1}`, uplink: false });
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
    state.channels.splice(Number(button.closest(".channelRow").dataset.index), 1);
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
}

populateStaticSelects();
bindEvents();
state.channels = [defaultChannel()];
renderChannels();
Promise.all([loadDevices(), loadVersions(false)]).catch((error) => setStatus(error.message, true));
