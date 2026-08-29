const DICT = {
  es: {
    "page.title": "Meshtastic Builder",
    "header.tagline": "Firmware Meshtastic a medida, sin editar JSON a mano",
    "header.refresh": "Actualizar tags",

    "step1.title": "Dispositivo y firmware",
    "step1.device": "Dispositivo",
    "step1.version": "Version de firmware",

    "step2.title": "Identidad del nodo",
    "step2.longName": "Nombre largo",
    "step2.shortName": "Nombre corto",

    "step3.title": "Radio LoRa",
    "step3.region": "Region LoRa",
    "step3.role": "Rol del dispositivo",
    "step3.preset": "Preset de modem",
    "step3.presetDisabled": "Desactivado: estas usando configuracion LoRa manual.",

    "step4.title": "Canales",
    "step4.hint": "Hasta tres canales escritos en el firmware.",
    "step4.add": "+ Canal",
    "channel.name": "Nombre",
    "channel.psk": "Clave (base64)",
    "channel.precision": "Precision",
    "channel.downlink": "Downlink",
    "channel.uplink": "Uplink",
    "channel.remove": "Quitar",
    "channel.defaultName": "Canal",

    "step5.title": "Servicios",
    "step5.tz": "Zona horaria (TZ POSIX)",
    "step5.tzPeninsula": "Peninsula",
    "step5.tzCanarias": "Canarias",
    "step5.mqttAddress": "Servidor MQTT",
    "step5.mqttEnabled": "Activar MQTT",
    "step5.adminKey": "Clave de administracion remota (base64)",

    "step6.title": "Opciones avanzadas",
    "step6.badge": "Experimental / parche de codigo",
    "step6.warning":
      "Estas opciones modifican el codigo fuente del firmware antes de compilar. No forman parte de userPrefs.jsonc y solo estan disponibles en versiones recientes. Usalas bajo tu responsabilidad.",
    "step6.unavailable": "No disponible para la version de firmware seleccionada.",
    "step6.okToMqtt": "Permitir reenvio a MQTT por defecto (ok_to_mqtt)",
    "step6.customLora": "Configuracion LoRa manual (desactiva el preset)",
    "step6.customLoraHint":
      "Comprueba que los parametros sean legales en tu region antes de emitir.",
    "step6.bandwidth": "Ancho de banda (kHz)",
    "step6.spreadFactor": "Spreading factor",
    "step6.codingRate": "Coding rate",
    "step6.channelNum": "Slot de frecuencia",
    "step6.channelNumHint": "0 = automatico segun la region",

    "step7.title": "Revisar y enviar",
    "step7.preview": "Ver userPrefs.jsonc generado",
    "step7.email": "Email de entrega",
    "step7.submit": "Enviar compilacion",

    "result.title": "Peticion creada",
    "result.status": "Estado",
    "result.token": "Token",
    "result.options": "Opciones avanzadas",
    "result.download": "Descarga",
    "result.share": "Guarda este enlace para volver mas tarde:",
    "result.pending": "Disponible al finalizar",
    "result.downloadZip": "Descargar ZIP",
    "result.failed": "La compilacion fallo",

    "status.loadingTags": "Cargando tags...",
    "status.refreshingTags": "Actualizando tags...",
    "status.ready": "Listo.",
    "status.creating": "Creando peticion...",
    "status.queued": "Peticion en cola.",
    "status.loadingBuild": "Cargando compilacion...",

    "error.noVersions": "No hay versiones soportadas en cache.",
    "error.template": "No se pudo cargar userPrefs.jsonc.",
    "error.shortName": "El nombre corto no puede superar 4 bytes.",
    "error.channelName": "El canal {n} necesita nombre.",
    "error.channelPrecision": "La precision del canal {n} debe estar entre 0 y 32.",
    "error.base64": "{label} debe estar en base64 valido.",
    "error.base64Length": "{label} debe estar en base64 valido de {bytes} bytes.",
    "label.channelKey": "La clave del canal {n}",
    "label.adminKey": "La clave de administracion remota",
  },
  en: {
    "page.title": "Meshtastic Builder",
    "header.tagline": "Custom Meshtastic firmware without hand-editing JSON",
    "header.refresh": "Refresh tags",

    "step1.title": "Device and firmware",
    "step1.device": "Device",
    "step1.version": "Firmware version",

    "step2.title": "Node identity",
    "step2.longName": "Long name",
    "step2.shortName": "Short name",

    "step3.title": "LoRa radio",
    "step3.region": "LoRa region",
    "step3.role": "Device role",
    "step3.preset": "Modem preset",
    "step3.presetDisabled": "Disabled: you are using a manual LoRa configuration.",

    "step4.title": "Channels",
    "step4.hint": "Up to three channels written into the firmware.",
    "step4.add": "+ Channel",
    "channel.name": "Name",
    "channel.psk": "Key (base64)",
    "channel.precision": "Precision",
    "channel.downlink": "Downlink",
    "channel.uplink": "Uplink",
    "channel.remove": "Remove",
    "channel.defaultName": "Channel",

    "step5.title": "Services",
    "step5.tz": "Time zone (POSIX TZ)",
    "step5.tzPeninsula": "Mainland Spain",
    "step5.tzCanarias": "Canary Islands",
    "step5.mqttAddress": "MQTT server",
    "step5.mqttEnabled": "Enable MQTT",
    "step5.adminKey": "Remote admin key (base64)",

    "step6.title": "Advanced options",
    "step6.badge": "Experimental / source patch",
    "step6.warning":
      "These options patch the firmware source before compiling. They are not part of userPrefs.jsonc and are only available on recent versions. Use at your own risk.",
    "step6.unavailable": "Not available for the selected firmware version.",
    "step6.okToMqtt": "Allow MQTT forwarding by default (ok_to_mqtt)",
    "step6.customLora": "Manual LoRa configuration (disables the preset)",
    "step6.customLoraHint": "Check that these parameters are legal in your region before transmitting.",
    "step6.bandwidth": "Bandwidth (kHz)",
    "step6.spreadFactor": "Spreading factor",
    "step6.codingRate": "Coding rate",
    "step6.channelNum": "Frequency slot",
    "step6.channelNumHint": "0 = automatic for the region",

    "step7.title": "Review and submit",
    "step7.preview": "Show generated userPrefs.jsonc",
    "step7.email": "Delivery email",
    "step7.submit": "Submit build",

    "result.title": "Request created",
    "result.status": "Status",
    "result.token": "Token",
    "result.options": "Advanced options",
    "result.download": "Download",
    "result.share": "Save this link to come back later:",
    "result.pending": "Available when finished",
    "result.downloadZip": "Download ZIP",
    "result.failed": "The build failed",

    "status.loadingTags": "Loading tags...",
    "status.refreshingTags": "Refreshing tags...",
    "status.ready": "Ready.",
    "status.creating": "Creating request...",
    "status.queued": "Request queued.",
    "status.loadingBuild": "Loading build...",

    "error.noVersions": "No supported versions in cache.",
    "error.template": "Could not load userPrefs.jsonc.",
    "error.shortName": "The short name cannot exceed 4 bytes.",
    "error.channelName": "Channel {n} needs a name.",
    "error.channelPrecision": "Channel {n} precision must be between 0 and 32.",
    "error.base64": "{label} must be valid base64.",
    "error.base64Length": "{label} must be valid base64 of {bytes} bytes.",
    "label.channelKey": "The channel {n} key",
    "label.adminKey": "The remote admin key",
  },
};

let lang = localStorage.getItem("mb-lang");
if (!DICT[lang]) {
  lang = (navigator.language || "es").toLowerCase().startsWith("es") ? "es" : "en";
}

function t(key, vars) {
  let text = DICT[lang][key] ?? DICT.es[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, value);
    }
  }
  return text;
}

function currentLang() {
  return lang;
}

function applyI18n() {
  document.documentElement.lang = lang;
  document.title = t("page.title");
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-placeholder]")) {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  }
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.classList.toggle("is-active", button.dataset.lang === lang);
  }
}

function setLang(next) {
  if (!DICT[next] || next === lang) return;
  lang = next;
  localStorage.setItem("mb-lang", lang);
  applyI18n();
  document.dispatchEvent(new CustomEvent("languagechange"));
}
