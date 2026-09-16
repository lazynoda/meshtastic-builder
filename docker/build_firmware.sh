#!/usr/bin/env bash
set -euo pipefail

BASE_REPO="/opt/firmware"

if [[ "${1:-}" == "--prewarm" ]]; then
  shift
  cd "${BASE_REPO}"
  for env_name in "$@"; do
    echo "Prewarming PlatformIO dependencies for ${env_name}"
    pio pkg install -e "${env_name}" || true
    pio run -e "${env_name}" || true
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

cd "${WORK_DIR}"
# The image clones upstream at build time; fetch so tags newer than the image still resolve.
git fetch --tags --force origin || true
git checkout --force "${FIRMWARE_SHA}" || git checkout --force "${FIRMWARE_TAG}"
git submodule update --init --recursive

if [[ -f "${INPUT_DIR}/userprefs-ext.patch" ]]; then
  if ! git apply --verbose "${INPUT_DIR}/userprefs-ext.patch"; then
    echo "CODE_OPTIONS_PATCH_FAILED: esta version de firmware no admite las opciones de compilacion seleccionadas." >&2
    exit 3
  fi
fi

cp "${INPUT_DIR}/userPrefs.jsonc" ./userPrefs.jsonc

pio run -e "${PIO_ENV}"

mkdir -p "${OUTPUT_DIR}/files"
find ".pio/build/${PIO_ENV}" -maxdepth 1 -type f \
  \( -name "*.bin" -o -name "*.uf2" -o -name "*.hex" -o -name "*.elf" -o -name "*.map" \) \
  -exec cp {} "${OUTPUT_DIR}/files/" \;

cp "${INPUT_DIR}/userPrefs.jsonc" "${OUTPUT_DIR}/files/userPrefs.jsonc"
cp "${INPUT_DIR}/BUILD_INFO.txt" "${OUTPUT_DIR}/files/BUILD_INFO.txt"

{
  echo ""
  echo "builder_image_created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
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
