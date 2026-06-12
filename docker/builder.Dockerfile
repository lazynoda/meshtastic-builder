FROM debian:trixie

ARG MESHTASTIC_REPO=https://github.com/meshtastic/firmware.git
ARG PREWARM_ENVS="tbeam heltec-mesh-node-t114"

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PLATFORMIO_CORE_DIR=/opt/platformio

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
    && pip3 install --no-cache-dir -U platformio \
    && git clone --recursive "${MESHTASTIC_REPO}" /opt/firmware \
    && cd /opt/firmware \
    && git fetch --tags --force \
    && mkdir -p /work/input /work/output \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY docker/build_firmware.sh /usr/local/bin/build-firmware
RUN chmod +x /usr/local/bin/build-firmware \
    && /usr/local/bin/build-firmware --prewarm ${PREWARM_ENVS} \
    && rm -rf \
      /opt/platformio/.cache/downloads \
      /opt/platformio/.cache/tmp \
      /root/.cache/pip \
      /tmp/*

WORKDIR /opt/firmware
ENTRYPOINT ["/usr/local/bin/build-firmware"]
