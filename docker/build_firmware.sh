#!/usr/bin/env bash
set -euo pipefail

BASE_REPO="/opt/firmware"

if [[ "${1:-}" == "--prewarm" ]]; then
  shift
  cd "${BASE_REPO}"
  ref="${1:-latest}"
  shift
  if [[ "${ref}" == "latest" ]]; then
    ref="$(git tag --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  fi
  echo "Prewarming against ${ref}"
  git checkout --force "${ref}"
  git submodule update --init --recursive
  for env_name in "$@"; do
    echo "Prewarming PlatformIO dependencies for ${env_name}"
    pio pkg install -e "${env_name}"
    # pio run pulls the lazily installed tools (esptool, nrfutil, mklittlefs) that
    # pkg install skips. The first ESP32 run can fail while pioarduino swaps
    # tool-scons under a running SCons (platform-espressif32#529); the second
    # run is stable. A compile failure must not sink the image.
    pio run -e "${env_name}" || pio run -e "${env_name}" || true
  done
  exit 0
fi

if [[ "$#" -ne 3 ]]; then
  echo "usage: build-firmware <firmware-tag> <firmware-sha> <platformio-env>" >&2
  exit 2
fi

FIRMWARE_TAG="$1"
FIRMWARE_SHA="$2"
PIO_ENV="$3"
WORK_DIR="${BASE_REPO}"
OUTPUT_DIR="/work/output"
INPUT_DIR="/work/input"

case "${PIO_ENV}" in
  *[!A-Za-z0-9._-]*)
    echo "Invalid PlatformIO environment: ${PIO_ENV}" >&2
    exit 2
    ;;
esac

# Print the basename of the first file matching any of the patterns, or nothing.
first_match() {
  local dir="$1"
  shift
  local pattern path
  for pattern in "$@"; do
    shopt -s nullglob
    for path in "${dir}"/${pattern}; do
      shopt -u nullglob
      basename "${path}"
      return 0
    done
    shopt -u nullglob
  done
}

# A short note in the ZIP, because the web flasher covers the common case but says
# nothing about the other files. The spiffs offset is read out of this build's own
# partition table rather than hardcoded: it differs per board.
write_flashing_notes() {
  local dir="$1"
  local factory update littlefs uf2 hex spiffs
  # nullglob, not ls: under `set -o pipefail` an ls that matches nothing fails
  # the whole command substitution and set -e takes the script down with it.
  factory=$(first_match "${dir}" "*.factory.bin")
  update=$(first_match "${dir}" "*-update.bin")
  littlefs=$(first_match "${dir}" "littlefs-*.bin" "spiffs-*.bin")
  uf2=$(first_match "${dir}" "*.uf2")
  hex=$(first_match "${dir}" "*.hex")

  {
    echo "Flashing this firmware"
    echo "======================"
    echo ""
    if [[ -n "${factory}" ]]; then
      spiffs=$(python3 - "${dir}/partitions.bin" <<'PY' 2>/dev/null || true
import struct, sys
raw = open(sys.argv[1], "rb").read()
for off in range(0, len(raw), 32):
    entry = raw[off:off + 32]
    if entry[:2] != b"\xaa\x50":
        break
    _, _, _, addr, _, label, _ = struct.unpack("<HBBII16sI", entry)
    if label.rstrip(b"\x00") in (b"spiffs", b"littlefs"):
        print(hex(addr))
        break
PY
)
      echo "Easiest: https://flasher.meshtastic.org"
      echo "  Pick your device, choose the custom firmware option and select this ZIP."
      echo "  That is an update and keeps the settings already on the node."
      echo ""
      echo "Full install with esptool, for a blank node or one that will not boot:"
      echo "  esptool erase-flash"
      echo "  esptool write-flash 0x0 ${factory}"
      [[ -n "${littlefs}" && -n "${spiffs}" ]] && echo "  esptool write-flash ${spiffs} ${littlefs}"
      echo ""
      echo "Files:"
      [[ -n "${update}" ]] && echo "  ${update}"
      echo "      app image only, written at 0x10000. This is what the web flasher uses."
      echo "  ${factory}"
      echo "      bootloader + partition table + app, written at 0x0."
      [[ -n "${littlefs}" ]] && echo "  ${littlefs}" && echo "      empty filesystem for the spiffs partition."
      echo "  bootloader.bin / partitions.bin"
      echo "      the pieces already inside the factory image, at 0x0 and 0x8000."
    else
      echo "This is an nRF52 board, so esptool is not involved."
      echo ""
      echo "Double-tap the reset button. The node appears as a USB drive."
      [[ -n "${uf2}" ]] && echo "Copy ${uf2} onto it. The node reboots on its own."
      echo ""
      echo "Files:"
      [[ -n "${uf2}" ]] && echo "  ${uf2}" && echo "      drag-and-drop image. This is the one you want."
      [[ -n "${hex}" ]] && echo "  ${hex}" && echo "      for a SWD or J-Link programmer."
    fi
    echo "  userPrefs.jsonc"
    echo "      the settings compiled into this build."
    echo "  BUILD_INFO.txt"
    echo "      firmware tag, commit and build metadata."
  } >"${dir}/FLASHING.txt"
}

cd "${WORK_DIR}"
# Only hit the network when the image does not already contain the requested commit.
if ! git cat-file -e "${FIRMWARE_SHA}^{commit}" 2>/dev/null; then
  git fetch --tags --force origin || true
fi
git checkout --force "${FIRMWARE_SHA}" || git checkout --force "${FIRMWARE_TAG}"
git submodule update --init --recursive

if [[ -f "${INPUT_DIR}/userprefs-ext.patch" ]]; then
  if ! git apply --verbose "${INPUT_DIR}/userprefs-ext.patch"; then
    echo "CODE_OPTIONS_PATCH_FAILED: esta version de firmware no admite las opciones de compilacion seleccionadas." >&2
    exit 3
  fi
fi

cp "${INPUT_DIR}/userPrefs.jsonc" ./userPrefs.jsonc

# Retry once: pioarduino may replace tool-scons mid-run on the first build of a
# platform version (platform-espressif32#529). A genuine compile error fails twice.
pio run -e "${PIO_ENV}" || pio run -e "${PIO_ENV}"

# Only what a flasher consumes. .elf and .map are dropped on purpose: they were
# 81% of the ZIP and nothing in bin/device-install.sh reads them, so they only
# matter for decoding a backtrace. Everything else stays, including the
# littlefs image: device-install.sh writes it to the spiffs partition after
# erase_flash, and it aborts if the file is missing.
mkdir -p "${OUTPUT_DIR}/files"
find ".pio/build/${PIO_ENV}" -maxdepth 1 -type f \
  \( -name "*.bin" -o -name "*.uf2" -o -name "*.hex" \) \
  -exec cp {} "${OUTPUT_DIR}/files/" \;

# flasher.meshtastic.org only reads a release manifest for firmware it hosts, so a
# ZIP the user picks themselves always takes the legacy path, which searches the
# archive for firmware-<target>-<version>-update.bin. Ship the app-only image
# under that name and the ZIP can be selected as-is. The factory image keeps its
# own name; the flasher's pattern deliberately excludes *-update.bin.
for app in "${OUTPUT_DIR}/files/"firmware-*.bin; do
  [[ -e "${app}" ]] || continue
  case "${app}" in
    *.factory.bin | *-update.bin) continue ;;
  esac
  # Only ESP32 builds emit a factory image, and only they have an app slot at
  # 0x10000. nRF52 ships a .uf2 and must not be touched. This has to be an if,
  # not a && chain: as the last statement in the loop it would return 1 on an
  # nRF52 build and set -e would kill the script.
  if [[ -e "${app%.bin}.factory.bin" ]]; then
    mv "${app}" "${app%.bin}-update.bin"
  fi
done

cp "${INPUT_DIR}/userPrefs.jsonc" "${OUTPUT_DIR}/files/userPrefs.jsonc"
cp "${INPUT_DIR}/BUILD_INFO.txt" "${OUTPUT_DIR}/files/BUILD_INFO.txt"
write_flashing_notes "${OUTPUT_DIR}/files"

{
  echo ""
  # When this firmware was compiled, not when the image was prewarmed: the
  # image stamp is written into the prewarm layer, so it only moves when the
  # prewarmed content itself is rebuilt.
  echo "built_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "builder_image_created_at=$(cat /etc/builder-image-created-at 2>/dev/null || echo unknown)"
  echo "actual_git_sha=$(git rev-parse HEAD)"
  echo "platformio_env=${PIO_ENV}"
  echo "platformio_version=$(pio --version)"
} >> "${OUTPUT_DIR}/files/BUILD_INFO.txt"

if [[ -z "$(find "${OUTPUT_DIR}/files" -type f ! -name BUILD_INFO.txt ! -name userPrefs.jsonc -print -quit)" ]]; then
  echo "Build completed but no firmware files were found for ${PIO_ENV}" >&2
  exit 1
fi

ZIP_NAME="meshtastic-${FIRMWARE_TAG}-${PIO_ENV}.zip"
(
  cd "${OUTPUT_DIR}/files"
  zip -r "${OUTPUT_DIR}/${ZIP_NAME}" .
)
