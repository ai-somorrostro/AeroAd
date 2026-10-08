#!/bin/bash
# 01-create-buckets.sh — crea los buckets extra listados en INFLUXDB_EXTRA_BUCKETS.
# Idempotente: solo crea los buckets que aún no existen.
# TODO: rellenar INFLUXDB_EXTRA_BUCKETS en .env (nombres separados por comas).
set -euo pipefail

: "${INFLUXDB_EXTRA_BUCKETS:=}"

if [ -z "$INFLUXDB_EXTRA_BUCKETS" ]; then
  echo "[init] INFLUXDB_EXTRA_BUCKETS vacío: nada que crear."
  exit 0
fi

: "${DOCKER_INFLUXDB_INIT_ORG:?Falta DOCKER_INFLUXDB_INIT_ORG}"
: "${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN:?Falta DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}"

echo "[init] Buckets extra: $INFLUXDB_EXTRA_BUCKETS"
IFS=',' read -ra BUCKETS <<< "$INFLUXDB_EXTRA_BUCKETS"
for raw in "${BUCKETS[@]}"; do
  bucket="$(echo "$raw" | xargs)"
  [ -z "$bucket" ] && continue
  if influx bucket list \
      --org "$DOCKER_INFLUXDB_INIT_ORG" \
      --token "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" \
      --name "$bucket" --hide-headers 2>/dev/null | grep -q .; then
    echo "[init] bucket '$bucket' ya existe, se omite."
  else
    echo "[init] creando bucket '$bucket'..."
    influx bucket create \
      --org "$DOCKER_INFLUXDB_INIT_ORG" \
      --token "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" \
      --name "$bucket"
  fi
done
