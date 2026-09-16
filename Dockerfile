FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MB_HOST=0.0.0.0 \
    MB_DATA_DIR=/data \
    MB_DB_PATH=/data/meshtastic-builder.sqlite \
    MB_ARTIFACT_DIR=/data/artifacts

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends docker-cli \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

EXPOSE 8080
CMD ["python", "-m", "meshtastic_builder.app"]
