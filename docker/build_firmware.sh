#!/usr/bin/env bash
set -euo pipefail

BASE_REPO="/opt/firmware"

# Prewarming lives in docker/prewarm.sh, which the image runs in an earlier
# layer. Keeping it out of here is what lets this file be edited without
# rebuilding an hour of prewarmed PlatformIO packages.
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

# Every build log is read by someone hunting for the step that broke. Name the
# steps so they can be found by eye, and emit one machine-readable line when we
# already know what went wrong - the worker turns that into a user-facing reason
# instead of handing over four kilobytes of PlatformIO output.
phase() {
  echo "##### phase: $1 #####"
}

fail() {
  local code="$1" phase_name="$2" detail="$3"
  echo "MB_FAILURE code=${code} phase=${phase_name} detail=${detail}" >&2
  exit "${4:-1}"
}

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
phase "checkout ${FIRMWARE_TAG} (${FIRMWARE_SHA})"
# Only hit the network when the image does not already contain the requested commit.
if ! git cat-file -e "${FIRMWARE_SHA}^{commit}" 2>/dev/null; then
  git fetch --tags --force origin || true
fi
git checkout --force "${FIRMWARE_SHA}" || git checkout --force "${FIRMWARE_TAG}"
git submodule update --init --recursive

# Every patch the worker staged, in name order. The worker decides which ones a
# given firmware tag needs; this only applies what it was handed, and a patch
# that does not apply stops the build before pio run rather than silently
# compiling firmware without the change the user asked for.
phase "patches"
shopt -s nullglob
patches=("${INPUT_DIR}/patches"/*.patch)
shopt -u nullglob
if [[ ${#patches[@]} -eq 0 ]]; then
  echo "No firmware patches requested for this build."
fi
for patch in "${patches[@]}"; do
  patch_name="$(basename "${patch}")"
  echo "Applying ${patch_name}"
  if ! git apply --verbose "${patch}"; then
    fail patch_failed patches "${patch_name}" 3
  fi
done

phase "inputs"
if [[ ! -f "${INPUT_DIR}/userPrefs.jsonc" ]]; then
  fail infrastructure inputs "userPrefs.jsonc never reached the builder container."
fi
cp "${INPUT_DIR}/userPrefs.jsonc" ./userPrefs.jsonc
echo "userPrefs.jsonc in place ($(wc -c <./userPrefs.jsonc) bytes)"

phase "compile ${PIO_ENV}"
# Retry once: pioarduino may replace tool-scons mid-run on the first build of a
# platform version (platform-espressif32#529). A genuine compile error fails twice.
pio run -e "${PIO_ENV}" || pio run -e "${PIO_ENV}"

# Only what a flasher consumes. .elf and .map are dropped on purpose: they were
# 81% of the ZIP and nothing in bin/device-install.sh reads them, so they only
# matter for decoding a backtrace. Everything else stays, including the
# littlefs image: device-install.sh writes it to the spiffs partition after
# erase_flash, and it aborts if the file is missing.
phase "package"
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
  fail no_artifacts package "PlatformIO produced no firmware files for ${PIO_ENV}."
fi

ZIP_NAME="meshtastic-${FIRMWARE_TAG}-${PIO_ENV}.zip"
(
  cd "${OUTPUT_DIR}/files"
  zip -r "${OUTPUT_DIR}/${ZIP_NAME}" .
)
