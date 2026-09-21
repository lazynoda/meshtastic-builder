#!/usr/bin/env bash
# Image build step only. Never runs at build-request time.
#
# This lives apart from build_firmware.sh on purpose. The prewarm layer costs
# about an hour and 8 GB, and Docker invalidates it whenever an earlier layer
# changes. build_firmware.sh changes whenever a patch, a phase banner or a
# failure marker changes, so it is copied in *after* this layer and a shell edit
# no longer throws the prewarm away. Keep this file boring: every edit here does
# cost a full rebuild.
#
# usage: prewarm-firmware <ref|latest> [platformio-env...]

set -euo pipefail

BASE_REPO="/opt/firmware"

cd "${BASE_REPO}"

ref="${1:-latest}"
shift || true
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
