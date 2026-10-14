#!/bin/sh
# create-grafana-sa.sh — crea las service accounts de Grafana (una por rol) y sus
# tokens vía API, y los guarda en ficheros del volumen compartido.
#
# Idempotente: para cada rol, si el fichero ya tiene un token válido, no crea nada.
# Nunca imprime el valor de los tokens.
#
# Variables (vienen del entorno del servicio grafana-sa-init):
#   GRAFANA_URL, GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD, GRAFANA_SA_ROLE,
#   GRAFANA_SA_DIRECCION_NAME, GRAFANA_SA_DIRECCION_TOKEN_FILE,
#   GRAFANA_SA_ANALISIS_NAME,  GRAFANA_SA_ANALISIS_TOKEN_FILE,
#   GRAFANA_SA_IT_NAME,        GRAFANA_SA_IT_TOKEN_FILE
set -eu

: "${GRAFANA_URL:?Falta GRAFANA_URL}"
: "${GRAFANA_ADMIN_USER:?Falta GRAFANA_ADMIN_USER}"
: "${GRAFANA_ADMIN_PASSWORD:?Falta GRAFANA_ADMIN_PASSWORD}"
SA_ROLE="${GRAFANA_SA_ROLE:-Viewer}"

api() { # $1: método, $2: path, $3 (opcional): cuerpo JSON
  if [ $# -ge 3 ]; then
    curl -fsS -u "$GRAFANA_ADMIN_USER:$GRAFANA_ADMIN_PASSWORD" \
      -H 'Content-Type: application/json' \
      -X "$1" --data "$3" "$GRAFANA_URL$2"
  else
    curl -fsS -u "$GRAFANA_ADMIN_USER:$GRAFANA_ADMIN_PASSWORD" \
      -X "$1" "$GRAFANA_URL$2"
  fi
}

token_valid() { # $1: token — 200 en /api/user significa válido
  curl -fsS -o /dev/null -H "Authorization: Bearer $1" "$GRAFANA_URL/api/user"
}

ensure_sa() { # $1: nombre de la SA, $2: fichero de token
  SA_NAME="$1"
  TOKEN_FILE="$2"

  if [ -s "$TOKEN_FILE" ] && token_valid "$(cat "$TOKEN_FILE")" 2>/dev/null; then
    echo "[sa-init] '$SA_NAME': token existente válido, nada que hacer."
    return 0
  fi

  SA_ID="$(api GET "/api/serviceaccounts/search?query=$SA_NAME" \
    | tr '{' '\n' | grep "\"name\":\"$SA_NAME\"" | head -n1 \
    | grep -o '"id":[0-9]*' | head -n1 | cut -d: -f2 || true)"

  if [ -z "${SA_ID:-}" ]; then
    echo "[sa-init] creando service account '$SA_NAME' (rol $SA_ROLE)..."
    SA_ID="$(api POST /api/serviceaccounts \
      "{\"name\":\"$SA_NAME\",\"role\":\"$SA_ROLE\",\"isDisabled\":false}" \
      | grep -o '"id":[0-9]*' | head -n1 | cut -d: -f2)"
    [ -n "$SA_ID" ] || { echo "[sa-init] ERROR: no se pudo crear '$SA_NAME'." >&2; exit 1; }
  else
    echo "[sa-init] service account '$SA_NAME' ya existe (id $SA_ID)."
  fi

  echo "[sa-init] '$SA_NAME': generando token..."
  TOKEN="$(api POST "/api/serviceaccounts/$SA_ID/tokens" '{"name":"mcp-token"}' \
    | grep -o '"key":"[^"]*"' | head -n1 | cut -d'"' -f4)"
  [ -n "$TOKEN" ] || { echo "[sa-init] ERROR: no se pudo generar el token de '$SA_NAME'." >&2; exit 1; }

  rm -f "$TOKEN_FILE"
  printf '%s' "$TOKEN" > "$TOKEN_FILE"
  chmod 444 "$TOKEN_FILE"
  echo "[sa-init] '$SA_NAME': token guardado en $TOKEN_FILE."
}

ensure_sa "${GRAFANA_SA_DIRECCION_NAME:-sa-direccion}" "${GRAFANA_SA_DIRECCION_TOKEN_FILE:-/shared/sa-direccion-token}"
ensure_sa "${GRAFANA_SA_ANALISIS_NAME:-sa-analisis}" "${GRAFANA_SA_ANALISIS_TOKEN_FILE:-/shared/sa-analisis-token}"
ensure_sa "${GRAFANA_SA_IT_NAME:-sa-it}" "${GRAFANA_SA_IT_TOKEN_FILE:-/shared/sa-it-token}"
