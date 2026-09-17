const DICT = {
  es: {
    "page.title": "Meshtastic Builder",
    "header.tagline": "Firmware Meshtastic a medida, sin editar JSON a mano",
    "header.refresh": "Actualizar tags",
    "footer.trademark":
      "Meshtastic es una marca registrada de Meshtastic LLC. Este proyecto no esta afiliado ni respaldado por Meshtastic LLC, ni por ninguna de las marcas de los dispositivos listados. Es un proyecto hecho por aficion.",

    "step1.title": "Dispositivo y firmware",
    "step1.device": "Dispositivo",
    "step1.devicePlaceholder": "Busca un dispositivo",
    "step1.version": "Version de firmware",

    "step2.title": "Nodo",
    "step2.longName": "Nombre largo",
    "step2.shortName": "Nombre corto",

    "behaviour.title": "Dispositivo",
    "behaviour.hint": "Valores de fabrica aplicados en el primer arranque o tras un reset de fabrica.",
    "behaviour.rebroadcast": "Modo de retransmision",
    "behaviour.nodeInfoSecs": "Intervalo de node info (s)",
    "behaviour.nodeInfoHint": "Minimo 3600. Por defecto 259200 (72 h).",
    "behaviour.telemHint": "Vacio = telemetria desactivada.",
    "behaviour.deviceTelem": "Telemetria de dispositivo (s)",

    "step3.title": "Radio LoRa",
    "step3.region": "Region LoRa",
    "step3.role": "Rol del dispositivo",
    "step3.preset": "Preset de modem",
    "step3.presetDisabled": "Desactivado: estas usando configuracion LoRa manual.",
    "step3.txPower": "Potencia TX (dBm)",
    "step3.txPowerHint": "Vacio o 0 = maximo legal de la region.",
    "step3.mqttHead": "Puente MQTT",
    "step3.ignoreMqtt": "Ignorar paquetes que llegan por MQTT",
    "step3.ignoreMqttHint": "El nodo no reenvia a la malla lo que recibe del broker.",
    "step3.okToMqttHint": "Permite subir a MQTT los paquetes de este nodo.",

    "radios.title": "Bluetooth y WiFi",
    "radios.hint": "PIN de emparejamiento y red WiFi del nodo.",
    "radios.bluetoothHead": "Bluetooth",
    "radios.blePinEnabled": "Usar PIN de emparejamiento fijo",
    "radios.blePinHint": "Sin marcar, el firmware genera un PIN aleatorio en cada emparejamiento.",
    "radios.blePin": "PIN fijo (6 digitos)",
    "radios.wifiHead": "WiFi",
    "radios.wifiUnsupported": "El dispositivo seleccionado no tiene WiFi.",
    "radios.wifiEnabled": "Activar WiFi",
    "radios.wifiHint": "Solo en placas ESP32. Aumenta bastante el consumo.",
    "radios.wifiSsid": "Nombre de red (SSID)",
    "radios.wifiPsk": "Contrasena WiFi",
    "radios.wifiPskHint": "Se compila en el firmware en claro, igual que la de MQTT.",

    "extra.title": "Otros valores de configuracion",
    "extra.hint": "Cualquier clave de userPrefs.jsonc que no tenga control propio.",
    "extra.help": "Se validan igual que el resto: si el valor no encaja con la clave, la peticion se rechaza.",
    "extra.add": "+ Valor",
    "extra.key": "Clave",
    "extra.value": "Valor",
    "extra.choose": "Elige una clave",

    "position.title": "Posicion y GPS",
    "position.hint": "Modo de GPS, intervalos y posicion fija.",
    "position.gpsMode": "Modo de GPS",
    "position.gpsInterval": "Intervalo de GPS (s)",
    "position.broadcastInterval": "Intervalo de emision de posicion (s)",
    "position.broadcastHint": "Por defecto 259200 (72 h).",
    "position.smart": "Emision inteligente de posicion",
    "position.smartHint": "Emite al moverse en vez de a intervalo fijo.",
    "position.blockOnEvent": "Bloquear posicion en el canal de eventos",
    "position.blockOnEventHint": "No emite ni acepta posicion en canales con la clave del canal 0.",
    "position.fixedHead": "Posicion fija",
    "position.fixedEnabled": "Usar una posicion fija",
    "position.fixedHint": "Solo se aplica en el primer arranque o tras un reset de fabrica.",
    "position.lat": "Latitud",
    "position.lon": "Longitud",
    "position.alt": "Altitud (m)",

    "security.title": "Seguridad",
    "security.hint": "Claves de administracion remota y firma de paquetes.",

    "step4.title": "Canales",
    "step4.hint": "Hasta {max} canales escritos en el firmware.",
    "step4.add": "+ Canal",
    "channel.name": "Nombre",
    "channel.psk": "Clave (base64)",
    "channel.precision": "Precision",
    "channel.downlink": "Downlink",
    "channel.uplink": "Uplink",
    "channel.muted": "Silenciado",
    "channel.remove": "Quitar",
    "channel.reorder": "Arrastra para reordenar",
    "channel.precisionOff": "Sin posicion",
    "channel.precisionExact": "Exacta",
    "channel.defaultName": "Canal",

    "step5.tz": "Zona horaria (TZ POSIX)",
    "step5.tzPeninsula": "Peninsula y Baleares",
    "step5.tzCanarias": "Canarias",
    "step5.mqttHead": "MQTT",
    "mqtt.hint": "Servidor, credenciales y reenvio de paquetes.",
    "step5.mqttAddress": "Servidor MQTT",
    "step5.mqttEnabled": "Activar MQTT",
    "step5.mqttUsername": "Usuario MQTT",
    "step5.mqttPassword": "Contrasena MQTT",
    "step5.mqttPasswordHint": "Se compila en el firmware en claro. Usa credenciales dedicadas.",
    "step5.mqttRoot": "Topic raiz",
    "step5.mqttEncryption": "Cifrado de paquetes MQTT",
    "step5.mqttTls": "TLS",
    "step5.securityHead": "Seguridad",
    "step5.adminKey": "Clave de administracion remota (base64)",
    "step5.adminKey1": "Clave de administracion 2 (base64)",
    "step5.adminKey2": "Clave de administracion 3 (base64)",
    "step5.signaturePolicy": "Politica de firma de paquetes",
    "step5.isManaged": "Modo gestionado (bloquea la configuracion)",
    "step5.isManagedHint": "Requiere al menos una clave de administracion.",

    "step6.badge": "Parche de codigo",
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
    "step6.overrideFreq": "Frecuencia manual (MHz)",
    "step6.overrideFreqHint": "0 = usar la frecuencia de la region. Comprueba que sea legal donde estas.",

    "step7.title": "Revisar y solicitar",
    "step7.preview": "Ver userPrefs.jsonc generado",
    "preview.injected": "Opciones avanzadas, el servidor las inyecta al compilar:",
    "preview.defaults": "Valores por defecto de esta version de firmware",
    "step7.noEmail": "No se envia ningun email. Al enviar obtendras un enlace privado: guardalo.",
    "step7.submit": "Solicitar compilacion",
    "step7.ttl": "El ZIP se borra {days} dias despues de compilarse.",

    "result.title": "Peticion creada",
    "result.keep": "Guarda este enlace: es la unica forma de volver a tu compilacion.",
    "result.copy": "Copiar",
    "result.copied": "Enlace copiado.",
    "result.status": "Estado",
    "result.token": "Token",
    "result.options": "Opciones avanzadas",
    "result.download": "Descarga",
    "result.ttl": "El ZIP estara disponible durante {days} dias desde que termine la compilacion.",
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
    "error.maxBytes": "{label} no puede superar {bytes} bytes.",
    "error.mustBeText": "{label} no puede ser solo digitos ni parecer un numero: el firmware lo compilaria sin comillas.",
    "label.channelKey": "La clave del canal {n}",
    "label.adminKey": "La clave de administracion remota",
    "label.adminKey1": "La clave de administracion 2",
    "label.adminKey2": "La clave de administracion 3",
    "label.mqttAddress": "El servidor MQTT",
    "label.mqttUsername": "El usuario MQTT",
    "label.mqttPassword": "La contrasena MQTT",
    "label.mqttRoot": "El topic raiz MQTT",
    "label.wifiSsid": "El SSID WiFi",
    "label.wifiPsk": "La contrasena WiFi",
  },
  en: {
    "page.title": "Meshtastic Builder",
    "header.tagline": "Custom Meshtastic firmware without hand-editing JSON",
    "header.refresh": "Refresh tags",
    "footer.trademark":
      "Meshtastic is a registered trademark of Meshtastic LLC. This project is not affiliated with or endorsed by Meshtastic LLC, nor by any of the device brands listed. It is a hobby project.",

    "step1.title": "Device and firmware",
    "step1.device": "Device",
    "step1.devicePlaceholder": "Search for a device",
    "step1.version": "Firmware version",

    "step2.title": "Node",
    "step2.longName": "Long name",
    "step2.shortName": "Short name",

    "behaviour.title": "Device",
    "behaviour.hint": "Factory defaults applied on first boot or after a factory reset.",
    "behaviour.rebroadcast": "Rebroadcast mode",
    "behaviour.nodeInfoSecs": "Node info interval (s)",
    "behaviour.nodeInfoHint": "Minimum 3600. Defaults to 259200 (72 h).",
    "behaviour.telemHint": "Empty = telemetry disabled.",
    "behaviour.deviceTelem": "Device telemetry (s)",

    "step3.title": "LoRa radio",
    "step3.region": "LoRa region",
    "step3.role": "Device role",
    "step3.preset": "Modem preset",
    "step3.presetDisabled": "Disabled: you are using a manual LoRa configuration.",
    "step3.txPower": "TX power (dBm)",
    "step3.txPowerHint": "Empty or 0 = region legal maximum.",
    "step3.mqttHead": "MQTT bridge",
    "step3.ignoreMqtt": "Ignore packets arriving over MQTT",
    "step3.ignoreMqttHint": "The node does not repeat onto the mesh what it receives from the broker.",
    "step3.okToMqttHint": "Lets this node's packets be uploaded to MQTT.",

    "radios.title": "Bluetooth and WiFi",
    "radios.hint": "Pairing PIN and the node's WiFi network.",
    "radios.bluetoothHead": "Bluetooth",
    "radios.blePinEnabled": "Use a fixed pairing PIN",
    "radios.blePinHint": "Unchecked, the firmware generates a random PIN on each pairing.",
    "radios.blePin": "Fixed PIN (6 digits)",
    "radios.wifiHead": "WiFi",
    "radios.wifiUnsupported": "The selected device has no WiFi.",
    "radios.wifiEnabled": "Enable WiFi",
    "radios.wifiHint": "ESP32 boards only. Raises power draw noticeably.",
    "radios.wifiSsid": "Network name (SSID)",
    "radios.wifiPsk": "WiFi password",
    "radios.wifiPskHint": "Compiled into the firmware in clear text, like the MQTT one.",

    "extra.title": "Other config values",
    "extra.hint": "Any userPrefs.jsonc key without a control of its own.",
    "extra.help": "Validated like the rest: a value that does not match its key is rejected.",
    "extra.add": "+ Value",
    "extra.key": "Key",
    "extra.value": "Value",
    "extra.choose": "Pick a key",

    "position.title": "Position and GPS",
    "position.hint": "GPS mode, intervals and fixed position.",
    "position.gpsMode": "GPS mode",
    "position.gpsInterval": "GPS interval (s)",
    "position.broadcastInterval": "Position broadcast interval (s)",
    "position.broadcastHint": "Defaults to 259200 (72 h).",
    "position.smart": "Smart position broadcast",
    "position.smartHint": "Broadcasts on movement instead of on a fixed interval.",
    "position.blockOnEvent": "Block position on the event channel",
    "position.blockOnEventHint": "Neither sends nor accepts position on channels keyed like channel 0.",
    "position.fixedHead": "Fixed position",
    "position.fixedEnabled": "Use a fixed position",
    "position.fixedHint": "Applied only on first boot or after a factory reset.",
    "position.lat": "Latitude",
    "position.lon": "Longitude",
    "position.alt": "Altitude (m)",

    "security.title": "Security",
    "security.hint": "Remote admin keys and packet signing.",

    "step4.title": "Channels",
    "step4.hint": "Up to {max} channels written into the firmware.",
    "step4.add": "+ Channel",
    "channel.name": "Name",
    "channel.psk": "Key (base64)",
    "channel.precision": "Precision",
    "channel.downlink": "Downlink",
    "channel.uplink": "Uplink",
    "channel.muted": "Muted",
    "channel.remove": "Remove",
    "channel.reorder": "Drag to reorder",
    "channel.precisionOff": "No position",
    "channel.precisionExact": "Exact",
    "channel.defaultName": "Channel",

    "step5.tz": "Time zone (POSIX TZ)",
    "step5.tzPeninsula": "Peninsula and Balearic Islands",
    "step5.tzCanarias": "Canary Islands",
    "step5.mqttHead": "MQTT",
    "mqtt.hint": "Broker, credentials and packet forwarding.",
    "step5.mqttAddress": "MQTT server",
    "step5.mqttEnabled": "Enable MQTT",
    "step5.mqttUsername": "MQTT username",
    "step5.mqttPassword": "MQTT password",
    "step5.mqttPasswordHint": "Compiled into the firmware in clear text. Use dedicated credentials.",
    "step5.mqttRoot": "Root topic",
    "step5.mqttEncryption": "MQTT packet encryption",
    "step5.mqttTls": "TLS",
    "step5.securityHead": "Security",
    "step5.adminKey": "Remote admin key (base64)",
    "step5.adminKey1": "Admin key 2 (base64)",
    "step5.adminKey2": "Admin key 3 (base64)",
    "step5.signaturePolicy": "Packet signature policy",
    "step5.isManaged": "Managed mode (locks the configuration)",
    "step5.isManagedHint": "Requires at least one admin key.",

    "step6.badge": "Source patch",
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
    "step6.overrideFreq": "Manual frequency (MHz)",
    "step6.overrideFreqHint": "0 = use the region frequency. Check that it is legal where you are.",

    "step7.title": "Review and submit",
    "step7.preview": "Show generated userPrefs.jsonc",
    "preview.injected": "Advanced options, injected by the server at build time:",
    "preview.defaults": "Defaults from this firmware version",
    "step7.noEmail": "No email is sent. Submitting gives you a private link: keep it.",
    "step7.submit": "Request build",
    "step7.ttl": "The ZIP is deleted {days} days after it is built.",

    "result.title": "Request created",
    "result.keep": "Save this link: it is the only way back to your build.",
    "result.copy": "Copy",
    "result.copied": "Link copied.",
    "result.status": "Status",
    "result.token": "Token",
    "result.options": "Advanced options",
    "result.download": "Download",
    "result.ttl": "The ZIP stays available for {days} days after the build finishes.",
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
    "error.maxBytes": "{label} cannot exceed {bytes} bytes.",
    "error.mustBeText": "{label} cannot be only digits or look like a number: the firmware would compile it unquoted.",
    "label.channelKey": "The channel {n} key",
    "label.adminKey": "The remote admin key",
    "label.adminKey1": "Admin key 2",
    "label.adminKey2": "Admin key 3",
    "label.mqttAddress": "The MQTT server",
    "label.mqttUsername": "The MQTT username",
    "label.mqttPassword": "The MQTT password",
    "label.mqttRoot": "The MQTT root topic",
    "label.wifiSsid": "The WiFi SSID",
    "label.wifiPsk": "The WiFi password",
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
