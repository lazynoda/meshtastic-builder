FROM debian:trixie

ARG MESHTASTIC_REPO=https://github.com/meshtastic/firmware.git
# Git ref the image is prewarmed against. "latest" resolves to the newest
# release tag at image build time; pass a tag to pin it.
ARG MESHTASTIC_REF=latest
ARG PREWARM_ENVS="heltec-v4 nrf52_promicro_diy_tcxo"
ARG PLATFORMIO_VERSION=6.1.19

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PLATFORMIO_CORE_DIR=/opt/platformio \
    PLATFORMIO_SETTING_ENABLE_TELEMETRY=No \
    PLATFORMIO_SETTING_CHECK_PLATFORMIO_INTERVAL=3650

RUN apt-get update && apt-get install --no-install-recommends -y \
      ca-certificates \
      curl \
      git \
      g++ \
      make \
      python3 \
      python3-pip \
      python3-venv \
      unzip \
      zip \
    # 6.2.0 ships tool-scons 4.11, which dropped SCons.Tool.FortranCommon and breaks
    # the pioarduino ESP32 link step. 6.1.19 builds both ESP32-S3 and nRF52 targets.
    && pip3 install --no-cache-dir "platformio==${PLATFORMIO_VERSION}" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip

# Full clone with tags and submodules so runtime builds of any supported tag
# resolve offline. build-firmware only fetches when the requested SHA is missing.
RUN git clone --recursive "${MESHTASTIC_REPO}" /opt/firmware \
    && cd /opt/firmware \
    && git fetch --tags --force \
    && mkdir -p /work/input /work/output

COPY docker/build_firmware.sh /usr/local/bin/build-firmware
RUN chmod +x /usr/local/bin/build-firmware \
    && /usr/local/bin/build-firmware --prewarm "${MESHTASTIC_REF}" ${PREWARM_ENVS} \
    # Provenance for BUILD_INFO.txt. Written in this layer on purpose: a cached
    # prewarm layer means identical content, so the original date stays honest.
    && date -u +%Y-%m-%dT%H:%M:%SZ > /etc/builder-image-created-at \
    && rm -rf \
      /opt/firmware/.pio/build \
      /opt/platformio/.cache/downloads \
      /opt/platformio/.cache/tmp \
      /root/.cache/pip \
      /tmp/*

WORKDIR /opt/firmware
ENTRYPOINT ["/usr/local/bin/build-firmware"]

# Nothing runs this image between builds, so `docker system prune -a` counts it
# as unused and deletes an hour of prewarming. Prune with
# `--filter "label!=keep"` to spare it. Kept last so adding it never invalidates
# the prewarm layer above.
LABEL keep="true"
