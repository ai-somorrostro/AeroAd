#!/bin/sh
# setup-env.sh — genera el .env local con credenciales aleatorias, sin rellenar nada a mano.
#
#   Uso:  ./scripts/setup-env.sh
#
# Qué hace:
#   - Si no existe .env, lo crea a partir de .env.example.
#   - Genera con aleatoriedad criptográfica (openssl o /dev/urandom):
#       INFLUXDB_INIT_PASSWORD, INFLUXDB_ADMIN_TOKEN, GRAFANA_ADMIN_PASSWORD
#       y el token de llamante del MCP (MCP_GRAFANA_SERVER_TOKEN).
#   - Solo rellena variables vacías o placeholder (CAMBIAME/CHANGEME):
#     nunca pisa valores que ya hayas puesto tú.
#   - Pide la RAPIDAPI_KEY una sola vez (Enter para dejarla vacía; el
#     pipeline de llegadas queda inactivo sin ella, el resto funciona).
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

# ---- secretos automáticos ----
ensure_secret INFLUXDB_INIT_PASSWORD
ensure_secret INFLUXDB_ADMIN_TOKEN
ensure_secret GRAFANA_ADMIN_PASSWORD
ensure_secret MCP_GRAFANA_SERVER_TOKEN

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

echo "[setup-env] Listo. Siguiente paso (no hay ninguno más):"
echo "  docker compose up -d --build"
