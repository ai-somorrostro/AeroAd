#!/bin/sh
# aeroadd-entrypoint.sh — exporta el token de InfluxDB desde el fichero del
# volumen compartido (lo genera influx-tokens-init) antes de arrancar Node-RED.
# El flow usa env.get('INFLUXDB_TOKEN'), así que el token debe estar en el
# entorno del proceso cuando Node-RED sube.
set -e

TOKEN_FILE="${INFLUXDB_TOKEN_FILE:-/shared/influx-nodered-token}"
if [ -r "$TOKEN_FILE" ]; then
  export INFLUXDB_TOKEN="$(cat "$TOKEN_FILE")"
  echo "[nodered] token de InfluxDB cargado desde $TOKEN_FILE."
else
  # Sin token el resto de pipelines sigue funcionando; el que escribe a
  # InfluxDB fallará a la vista en el log con el 401 de InfluxDB.
  echo "[nodered] AVISO: no existe $TOKEN_FILE sin el token automático." >&2
  echo "[nodered] AVISO: usa INFLUXDB_TOKEN del entorno si lo tienes." >&2
  if [ -z "${INFLUXDB_TOKEN:-}" ]; then
    echo "[nodered] AVISO: el pipeline de InfluxDB no podrá escribir (sin token)." >&2
  fi
fi

exec ./entrypoint.sh "$@"
