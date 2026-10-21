#!/bin/sh
# create-influx-tokens.sh — crea los tokens de InfluxDB de mínimo privilegio
# (uno por servicio cliente) y los deja como ficheros en el volumen compartido
# mcp-secrets. Se ejecuta dentro del contenedor efímero influx-tokens-init.
#
#   - Espera a que el API de InfluxDB responda.
#   - La descripción de cada autorización codifica los buckets concedidos
#     (p. ej. "aeroadd-grafana-read-captaciones_julio+captaciones_tiemporeal").
#     Así el script es idempotente y, si cambia la lista de buckets, los tokens
#     obsoletos del mismo servicio se eliminan y se crean con los permisos nuevos.
#   - Los ficheros del volumen se reescriben si faltan o difieren (p. ej. si se
#     renueva el volumen mcp-secrets).
#   - Nunca imprime el valor de los tokens.
#
# Permisos por servicio (mínimo privilegio, buckets configurables por .env):
#       grafana:  lectura   de GRAFANA_READ_BUCKETS
#       nodered:  escritura de NODERED_WRITE_BUCKETS
#       loader:   escritura de LOADER_WRITE_BUCKETS
#
# Variables (vienen del servicio del compose):
#   INFLUXDB_URL, INFLUXDB_INIT_ORG, INFLUXDB_ADMIN_TOKEN,
#   GRAFANA_READ_BUCKETS, NODERED_WRITE_BUCKETS, LOADER_WRITE_BUCKETS, SECRETS_DIR
set -eu

HOST_URL="${INFLUXDB_URL:-http://influxdb:8086}"
ORG="${INFLUXDB_INIT_ORG:?Falta INFLUXDB_INIT_ORG}"
ADMIN_TOKEN="${INFLUXDB_ADMIN_TOKEN:?Falta INFLUXDB_ADMIN_TOKEN}"
SECRETS_DIR="${SECRETS_DIR:-/shared}"

GRAFANA_READ_BUCKETS="${GRAFANA_READ_BUCKETS:-captaciones_julio,captaciones_tiemporeal,contexto_madrid}"
NODERED_WRITE_BUCKETS="${NODERED_WRITE_BUCKETS:-captaciones_tiemporeal,contexto_madrid}"
LOADER_WRITE_BUCKETS="${LOADER_WRITE_BUCKETS:-captaciones_julio}"

# Descripciones del script manual antiguo scripts/create-tokens.sh (solo el
# bucket inicial): si quedan en la instancia se borran para no dejar tokens
# con permisos erróneos.
LEGACY_DESCRIPTIONS="grafana-read nodered-write loader-write"

# ---- esperar a que el API responda (por si el healthcheck aún no ha dado verde) ----
n=0
until influx ping --host "$HOST_URL" >/dev/null 2>&1; do
  n=$((n + 1))
  if [ "$n" -ge 60 ]; then
    echo "[influx-tokens] ERROR: InfluxDB no responde tras 120 s." >&2
    exit 1
  fi
  sleep 2
done

# ---- utilidades ----
AUTH_LIST_CMD() {
  influx auth list --host "$HOST_URL" --org "$ORG" --token "$ADMIN_TOKEN" --hide-headers 2>/dev/null
}

bucket_id() { # $1: nombre del bucket → id (o vacío)
  influx bucket list --host "$HOST_URL" --org "$ORG" --token "$ADMIN_TOKEN" \
    --name "$1" --hide-headers 2>/dev/null | awk '{print $1}'
}

# La salida de influx auth list usa col1=id col2=descripción col3=token.
existing_token() { # $1: descripción completa del token a buscar
  AUTH_LIST_CMD | awk -v d="$1" '$2 == d {print $3}'
}

# delete_if_exists elimina autorizaciones por descripción exacta.
delete_if_exists() { # $1: descripción
  ids="$(AUTH_LIST_CMD | awk -v d="$1" '$2 == d {print $1}')"
  for id in $ids; do
    influx auth delete --host "$HOST_URL" --token "$ADMIN_TOKEN" \
      --id "$id" >/dev/null 2>&1 &&
      echo "[influx-tokens] token legacy '$1' eliminado."
  done
}

# delete_stale elimina autorizaciones de un servicio cuyo sufijo de buckets no
# coincide con el actual (col2 empieza por el mismo base pero difiere de full).
delete_stale() { # $1: base de descripción, $2: descripción completa esperada
  ids="$(AUTH_LIST_CMD | awk -v p="$1" -v full="$2" 'index($2, p) == 1 && $2 != full {print $1}')"
  for id in $ids; do
    influx auth delete --host "$HOST_URL" --token "$ADMIN_TOKEN" \
      --id "$id" >/dev/null 2>&1 &&
      echo "[influx-tokens] token obsoleto de '$1' eliminado."
  done
}

# save_token escribe el token en su fichero si difiere; nunca lo imprime.
save_token() { # $1: fichero, $2: token
  file="$1"
  if [ ! -s "$file" ] || [ "$(cat "$file")" != "$2" ]; then
    printf '%s' "$2" > "$file"
  fi
  chmod 444 "$file"
}

# bucket_flags imprime repetido `flag <id_bucket>` por cada nombre de la lista
# separada por comas; aborta el script si falta algún bucket.
# Uso: FLAGS="$(bucket_flags --write-bucket "b1,b2")"
bucket_flags() { # $1: flag (--read-bucket|--write-bucket), $2: lista de nombres
  flag="$1"
  echo "$2" | tr ',' '\n' | sed 's/^ *//; s/ *$//' | grep -v '^$' | while read -r bucket; do
    id="$(bucket_id "$bucket")"
    if [ -z "$id" ]; then
      echo "[influx-tokens] ERROR: no existe el bucket '$bucket'." >&2
      exit 1
    fi
    printf '%s %s ' "$flag" "$id"
  done
}

# ensure_token garantiza el token con el equivalente exacto de buckets y su
# fichero en el volumen compartido; limpia tokens obsoletos del mismo servicio.
# Uso: ensure_token <fichero> <base> <descripción completa> --write-bucket <id> [...]
ensure_token() { # $1: fichero destino, $2: base, $3: descripción completa, resto: flags de permiso
  file="$1"; base="$2"; desc="$3"; shift 3
  delete_stale "$base" "$desc"
  token="$(existing_token "$desc")"
  if [ -z "$token" ]; then
    token="$(influx auth create --host "$HOST_URL" --org "$ORG" --token "$ADMIN_TOKEN" \
      --description "$desc" "$@" --hide-headers 2>/dev/null | awk '{print $3}')"
  else
    echo "[influx-tokens] '$desc' ya existe: reutilizada."
  fi
  if [ -z "$token" ]; then
    echo "[influx-tokens] ERROR: no se pudo garantizar el token de '$desc'." >&2
    exit 1
  fi
  save_token "$file" "$token"
  echo "[influx-tokens] '$desc' garantizado y guardado en $file."
}

# descripción completa: <base>-<verbo>-<buckets con '+' en lugar de ','>
# (sin espacios: la columna 2 de influx auth list debe ser un solo campo).
for legacy in $LEGACY_DESCRIPTIONS; do
  delete_if_exists "$legacy"
done

GF_FLAGS="$(bucket_flags --read-bucket  "$GRAFANA_READ_BUCKETS")"
NR_FLAGS="$(bucket_flags --write-bucket "$NODERED_WRITE_BUCKETS")"
LD_FLAGS="$(bucket_flags --write-bucket "$LOADER_WRITE_BUCKETS")"

# El sufijo con la lista de buckets hace que el idempotente sea consciente de permisos.
ensure_token "$SECRETS_DIR/influx-grafana-token"  "aeroadd-grafana-" \
  "aeroadd-grafana-read-$(echo "$GRAFANA_READ_BUCKETS" | tr ',' '+')"     $GF_FLAGS
ensure_token "$SECRETS_DIR/influx-nodered-token" "aeroadd-nodered-" \
  "aeroadd-nodered-write-$(echo "$NODERED_WRITE_BUCKETS" | tr ',' '+')"   $NR_FLAGS
ensure_token "$SECRETS_DIR/influx-loader-token"  "aeroadd-loader-" \
  "aeroadd-loader-write-$(echo "$LOADER_WRITE_BUCKETS" | tr ',' '+')"     $LD_FLAGS

echo "[influx-tokens] Listo."
