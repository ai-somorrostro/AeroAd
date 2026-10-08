#!/bin/bash
# create-tokens.sh — genera tokens de InfluxDB de mínimo privilegio y los guarda en .env.
#
#   - GRAFANA_INFLUXDB_TOKEN: solo lectura  (para Grafana)
#   - NODERED_INFLUXDB_TOKEN: solo escritura (para Node-RED)
#   - LOADER_INFLUXDB_TOKEN:  solo escritura (para el loader)
#
# Idempotente: si la variable ya tiene valor en .env no crea un token nuevo,
# y al guardar actualiza la línea existente en vez de duplicarla.
# Nunca imprime los valores de los tokens.
#
# Uso (con InfluxDB levantado y .env relleno: org, bucket y token admin):
#   ./scripts/create-tokens.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: no existe $ENV_FILE. Cópialo con: cp .env.example .env" >&2
  exit 1
fi

command -v influx >/dev/null || {
  echo "ERROR: falta el CLI 'influx' en el PATH." >&2
  exit 1
}

set -a
# shellcheck disable=SC1091
. "$ENV_FILE"
set +a

ORG="${INFLUXDB_INIT_ORG:?Falta INFLUXDB_INIT_ORG en .env}"
BUCKET="${INFLUXDB_INIT_BUCKET:?Falta INFLUXDB_INIT_BUCKET en .env}"
ADMIN_TOKEN="${INFLUXDB_ADMIN_TOKEN:?Falta INFLUXDB_ADMIN_TOKEN en .env}"
HOST_URL="${INFLUXDB_HOST_URL:-http://localhost:${INFLUXDB_PORT:-8086}}"

bucket_id() {
  influx bucket list --host "$HOST_URL" --org "$ORG" --token "$ADMIN_TOKEN" \
    --name "$1" --hide-headers 2>/dev/null | awk '{print $1}'
}

BUCKET_ID="$(bucket_id "$BUCKET")"
if [ -z "$BUCKET_ID" ]; then
  echo "ERROR: no existe el bucket '$BUCKET' en la organización '$ORG'." >&2
  exit 1
fi

create_token() { # $1: descripción, resto: flags de permiso de 'influx auth create'
  local description="$1"; shift
  influx auth create --host "$HOST_URL" --org "$ORG" --token "$ADMIN_TOKEN" \
    --description "$description" "$@" --hide-headers 2>/dev/null | awk '{print $3}'
}

save_token() { # $1: VAR, $2: valor (nunca se imprime)
  local var="$1" value="$2" tmp
  tmp="$(mktemp)"
  grep -v "^${var}=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$var" "$value" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
}

ensure_token() { # $1: VAR, $2: descripción, resto: flags de permiso
  local var="$1" description="$2"; shift 2
  local current
  current="$(grep "^${var}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
  if [ -n "${current:-}" ]; then
    echo "[tokens] $var ya tiene valor en .env, se omite."
    return 0
  fi
  local token
  token="$(create_token "$description" "$@")"
  if [ -z "$token" ]; then
    echo "ERROR: no se pudo crear el token para $var." >&2
    exit 1
  fi
  save_token "$var" "$token"
  echo "[tokens] $var generado y guardado en .env."
}

ensure_token GRAFANA_INFLUXDB_TOKEN "grafana-read (scripts/create-tokens.sh)" --read-bucket "$BUCKET_ID"
ensure_token NODERED_INFLUXDB_TOKEN "nodered-write (scripts/create-tokens.sh)" --write-bucket "$BUCKET_ID"
ensure_token LOADER_INFLUXDB_TOKEN "loader-write (scripts/create-tokens.sh)" --write-bucket "$BUCKET_ID"

echo "[tokens] Listo."
