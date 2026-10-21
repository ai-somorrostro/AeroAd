#!/bin/sh
# setup-env.sh — genera el .env local con credenciales aleatorias y el CSV
# histórico si falta, sin rellenar nada a mano.
#
#   Uso:  ./scripts/setup-env.sh [--sin-historico]
#
# Qué hace:
#   - Si no existe .env, lo crea a partir de .env.example.
#   - Genera con aleatoriedad criptográfica (openssl o /dev/urandom):
#       INFLUXDB_INIT_PASSWORD, INFLUXDB_ADMIN_TOKEN, GRAFANA_ADMIN_PASSWORD
#       y los tokens de llamante del MCP (MCP_GRAFANA_SERVER_TOKEN_*).
#   - Solo rellena variables vacías o placeholder (CAMBIAME/CHANGEME):
#     nunca pisa valores que ya hayas puesto tú.
#   - Pide la RAPIDAPI_KEY una sola vez (Enter para dejarla vacía; el
#     pipeline de llegadas queda inactivo sin ella, el resto funciona).
#   - Genera el CSV histórico de junio si no existe (requiere Python 3) para
#     que el loader y el dashboard de clientes tengan datos desde el primer
#     arranque. Con --sin-historico se omite este paso.
#   - Nunca imprime el valor de las credenciales.
#   - Deja el .env con permisos 600 y escribe el fichero solo localmente
#     (.env está en .gitignore, jamás se sube al repositorio).
#
# Después de esto no hay ningún paso más: arranca con
#   docker compose up -d --build
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
TPL="$ROOT/.env.example"

GENERAR_HISTORICO=1
for arg in "$@"; do
  case "$arg" in
    --sin-historico|--skip-historico)
      GENERAR_HISTORICO=0
      ;;
    -h|--help)
      echo "Uso: $0 [--sin-historico]"
      echo "  --sin-historico  no genera el CSV histórico aunque falte"
      exit 0
      ;;
    *)
      echo "Opción desconocida: $arg" >&2
      echo "Uso: $0 [--sin-historico]" >&2
      exit 2
      ;;
  esac
done

# ---- aleatoriedad ----
rand() { # valor hex aleatorio (48 caracteres)
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  elif [ -c /dev/urandom ]; then
    head -c 24 /dev/urandom | base64 2>/dev/null | tr -d '=+/' | cut -c1-48
  else
    # último recurso (portable pero débil); mejor instalar openssl
    (ps 2>/dev/null || true; date +%s%N) | cksum | tr -cs '0-9' 'x' | head -c 48
  fi | tr -d '\r\n'
}

if ! command -v openssl >/dev/null 2>&1 && [ ! -c /dev/urandom ]; then
  echo "AVISO: ni openssl ni /dev/urandom disponibles; aleatoriedad débil." >&2
fi

# ---- plantilla ----
if [ ! -f "$ENV_FILE" ]; then
  cp "$TPL" "$ENV_FILE"
  echo "[setup-env] .env creado desde .env.example."
else
  echo "[setup-env] .env ya existe: solo relleno los vacíos o placeholder."
fi

# ---- utilidades ----
current_value() { # $1: nombre de variable
  grep "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true
}

set_var() { # $1: nombre, $2: valor — reescribe la línea (o la añade)
  var="$1"; val="$2"
  tmp="$(mktemp)"
  grep -v "^${var}=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$var" "$val" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

ensure_secret() { # $1: nombre — genera si vacío o placeholder
  var="$1"
  val="$(current_value "$var")"
  case "$val" in
    "" | CAMBIAME* | CHANGEME*)
      set_var "$var" "$(rand)"
      echo "[setup-env] $var generado (aleatorio)."
      ;;
    *)
      echo "[setup-env] $var ya tiene valor, se conserva."
      ;;
  esac
}

generar_historico() {
  csv="$ROOT/BDA/ImporCsvPandas/captaciones_junio_2026.csv"
  txt="$ROOT/generadores/captaciones_junio_2026_v3.txt"
  tmp_csv="${csv}.tmp.$$"

  if [ -s "$csv" ]; then
    echo "[setup-env] Histórico ya presente (${csv#"$ROOT"/}), no se regenera."
    return 0
  fi

  python_bin=""
  for candidato in python3 python; do
    if command -v "$candidato" >/dev/null 2>&1 \
        && "$candidato" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' >/dev/null 2>&1; then
      python_bin="$candidato"
      break
    fi
  done
  if [ -z "$python_bin" ]; then
    echo "[setup-env] ERROR: se necesita Python 3 para generar el CSV histórico." >&2
    echo "  Instálalo o usa '$0 --sin-historico' y genera el CSV a mano (ver README)." >&2
    return 1
  fi

  zona="$(current_value LOADER_TZ)"
  [ -n "$zona" ] || zona="Europe/Madrid"

  echo "[setup-env] CSV histórico no encontrado; generando 500K registros (tarda unos minutos)..."
  limpiar_historico() { rm -f "$txt" "$tmp_csv"; }
  trap limpiar_historico 0 1 2 15

  ( cd "$ROOT" && TZ="$zona" "$python_bin" generadores/generador_v3.py )
  "$python_bin" "$ROOT/generadores/line_protocol_a_csv.py" "$txt" "$tmp_csv"
  mv "$tmp_csv" "$csv"

  limpiar_historico
  trap - 0 1 2 15
  echo "[setup-env] Histórico generado en ${csv#"$ROOT"/}."
}

# ---- secretos automáticos ----
ensure_secret INFLUXDB_INIT_PASSWORD
ensure_secret INFLUXDB_ADMIN_TOKEN
ensure_secret GRAFANA_ADMIN_PASSWORD
ensure_secret MCP_GRAFANA_SERVER_TOKEN_DIRECCION
ensure_secret MCP_GRAFANA_SERVER_TOKEN_ANALISIS
ensure_secret MCP_GRAFANA_SERVER_TOKEN_IT

# ---- RAPIDAPI_KEY (una vez, por teclado; opcional) ----
if [ "$(current_value RAPIDAPI_KEY)" = "" ]; then
  if [ -t 0 ]; then
    printf '%s' "[setup-env] ¿Pegas tu RAPIDAPI_KEY de AeroDataBox ahora? (Enter para dejarla vacía) "
    read -r key
    key="$(printf '%s' "$key" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    case "$key" in
      "")
        echo "[setup-env] RAPIDAPI_KEY vacía: el pipeline de llegadas queda inactivo (el resto funciona)."
        ;;
      *)
        set_var RAPIDAPI_KEY "$key"
        echo "[setup-env] RAPIDAPI_KEY guardada."
        ;;
    esac
  else
    echo "[setup-env] RAPIDAPI_KEY vacía y no hay terminal interactivo; la puedes escribir a mano en .env."
  fi
else
  echo "[setup-env] RAPIDAPI_KEY ya tiene valor, se conserva."
fi

chmod 600 "$ENV_FILE"

# ---- histórico (CSV que consume el loader) ----
if [ "$GENERAR_HISTORICO" -eq 1 ]; then
  generar_historico
else
  echo "[setup-env] Generación del histórico omitida (--sin-historico)."
fi

echo "[setup-env] Listo. Siguiente paso:"
echo "  docker compose up -d --build"
