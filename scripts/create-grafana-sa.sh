#!/bin/sh
# create-grafana-sa.sh — crea la service account del MCP de Grafana y su token
# vía API, y los guarda en un fichero del volumen compartido.
#
# Idempotente: si el fichero ya tiene un token válido, no crea nada.
# Nunca imprime el valor del token.
#
# Variables (vienen del entorno del servicio grafana-sa-init):
#   GRAFANA_URL, GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD,
#   GRAFANA_SA_NAME (por defecto sa-mcp), GRAFANA_SA_ROLE (por defecto Viewer),
#   GRAFANA_SA_TOKEN_FILE (por defecto /shared/sa-mcp-token)
set -eu

: "${GRAFANA_URL:?Falta GRAFANA_URL}"
: "${GRAFANA_ADMIN_USER:?Falta GRAFANA_ADMIN_USER}"
: "${GRAFANA_ADMIN_PASSWORD:?Falta GRAFANA_ADMIN_PASSWORD}"

SA_NAME="${GRAFANA_SA_NAME:-sa-mcp}"
SA_ROLE="${GRAFANA_SA_ROLE:-Viewer}"
TOKEN_FILE="${GRAFANA_SA_TOKEN_FILE:-/shared/sa-mcp-token}"

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
  TOKEN_NAME="mcp-token-$SA_NAME" # único en la organización (Grafana exige unicidad org-wide)

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
  # Limpia tokens previos con el mismo nombre (p. ej. de un intento anterior que
  # falló después de crear el token) para que el POST no devuelva 400.
  OLD_IDS="$(api GET "/api/serviceaccounts/$SA_ID/tokens" \
    | tr '{' '\n' | grep "\"name\":\"$TOKEN_NAME\"" \
    | grep -o '"id":[0-9]*' | cut -d: -f2 || true)"
  for OLD_ID in $OLD_IDS; do
    api DELETE "/api/serviceaccounts/$SA_ID/tokens/$OLD_ID" >/dev/null \
      && echo "[sa-init] '$SA_NAME': token huérfano previo eliminado."
  done
  TOKEN="$(api POST "/api/serviceaccounts/$SA_ID/tokens" "{\"name\":\"$TOKEN_NAME\"}" \
    | grep -o '"key":"[^"]*"' | head -n1 | cut -d'"' -f4)"
  [ -n "$TOKEN" ] || { echo "[sa-init] ERROR: no se pudo generar el token de '$SA_NAME'." >&2; exit 1; }

  rm -f "$TOKEN_FILE"
  printf '%s' "$TOKEN" > "$TOKEN_FILE"
  chmod 444 "$TOKEN_FILE"
  echo "[sa-init] '$SA_NAME': token guardado en $TOKEN_FILE."
}

ensure_sa "$SA_NAME" "$TOKEN_FILE"

# Limpia los ficheros del esquema antiguo de tres MCP. No borra las service
# accounts de Grafana (se pueden eliminar a mano desde la UI si se desea).
for OLD_FILE in /shared/sa-direccion-token /shared/sa-analisis-token /shared/sa-it-token; do
  [ "$OLD_FILE" = "$TOKEN_FILE" ] && continue
  if [ -e "$OLD_FILE" ]; then
    rm -f "$OLD_FILE"
    echo "[sa-init] token obsoleto eliminado: $OLD_FILE"
  fi
done
