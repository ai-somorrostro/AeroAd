"""Loader AeroAdd (one-shot listo para deploy).

Servicio que se ejecuta al levantar la pila (`docker compose up -d --build`):

  1. Lee el token de escritura de mínimo privilegio (INFLUXDB_TOKEN_FILE,
     generado por influx-tokens-init) y verifica la conexión con InfluxDB.
  2. Carga el histórico de captaciones (CSV montado en /data, por defecto
     captaciones_junio_2026.csv) en el bucket captaciones_julio. La lógica de
     limpieza/normalización replica BDA/ImporCsvPandas/carga_historico_AeroAdd.ipynb
     y scripts/load-captaciones.py.
  3. Escribe un heartbeat de despliegue.

Es idempotente en efecto: reejecutarlo reescribe los mismos puntos (una fila
con la misma hora y tags genera un punto nuevo con +1 ns, ver abajo).
Nunca rompe el deploy: si falta configuración real avisa por log y sale
con 0 para que `docker compose up` no marque error.
"""

import os
import sys
import time

import pandas as pd

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError as exc:
    print(f"[loader] ERROR: dependencias no instaladas: {exc}", flush=True)
    sys.exit(1)

CSV = os.getenv("LOADER_CSV", "/data/captaciones_junio_2026.csv")
MEASUREMENT = "captaciones"
ZONA_HORARIA = os.getenv("LOADER_TZ", "Europe/Madrid")  # las horas del CSV son locales
TAMANO_LOTE = 10_000
TAGS = ["fabricante", "os", "idioma", "pais", "rango_edad"]

FABRICANTES = {"Apple", "Samsung", "Intel", "Lenovo", "HP", "Dell", "ASUS",
               "Xiaomi", "Huawei", "Google", "Sony", "Acer", "Microsoft",
               "Motorola"}
SISTEMAS = {"Android", "iOS", "Windows 11", "Windows 10", "macOS"}
IDIOMAS = {"es-ES", "en-GB", "en-US", "fr-FR", "de-DE", "it-IT", "pt-PT",
           "nl-NL", "pl-PL", "ca-ES", "sv-SE", "es-MX"}
PAISES = {"ES", "GB", "FR", "DE", "IT", "PT", "US", "NL", "IE", "BE", "SE",
          "DK", "PL", "CH", "AT", "MX"}
RE_MAC = r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$"
RE_EMAIL = (r"^[a-z0-9]+\.[a-z0-9]+@"
            r"(?:gmail\.com|hotmail\.com|outlook\.com|yahoo\.com|icloud\.com|proton\.me)$")
RE_NOMBRE = r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)+$"


def _is_placeholder(value: str) -> bool:
    return (not value) or value == "CAMBIAME" or value.startswith("CAMBIAME-")


def _resolver_token() -> str:
    """Token de escritura del loader: fichero del volumen (automático) o .env."""
    token_file = os.getenv("INFLUXDB_TOKEN_FILE", "/shared/influx-loader-token")
    if os.path.exists(token_file):
        with open(token_file, encoding="utf-8") as f:
            token = f.read().strip()
        if token:
            print(f"[loader] token leído de {token_file}.", flush=True)
            return token
    token = os.getenv("INFLUXDB_TOKEN", "")
    if token and not _is_placeholder(token):
        print("[loader] token leído de la variable INFLUXDB_TOKEN.", flush=True)
    return token


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve el DataFrame limpio con la hora (UTC) como índice."""
    df = df.copy()
    df.columns = ["hora", "mac", "fabricante", "nombre", "os", "idioma",
                  "edad", "email", "pais"]
    df = df.fillna("").astype(str).apply(lambda c: c.str.strip())
    df = df[~df.duplicated(keep="first")]
    hora = pd.to_datetime(df["hora"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    edad = pd.to_numeric(df["edad"], errors="coerce")
    ok = (hora.notna()
          & df["mac"].str.match(RE_MAC)
          & df["fabricante"].isin(FABRICANTES)
          & df["nombre"].str.match(RE_NOMBRE)
          & df["os"].isin(SISTEMAS)
          & df["idioma"].isin(IDIOMAS)
          & edad.between(15, 85) & (edad % 1 == 0)
          & df["email"].str.match(RE_EMAIL)
          & df["pais"].isin(PAISES))
    limpio = df[ok].copy()
    limpio["hora"] = hora[ok]
    limpio["edad"] = edad[ok].astype(int)
    limpio["rango_edad"] = pd.cut(
        limpio["edad"],
        bins=[14, 24, 34, 44, 54, 64, 85],
        labels=["15-24", "25-34", "35-44", "45-54", "55-64", "65-85"],
    ).astype(str)
    limpio["hora"] = (limpio["hora"]
                      .dt.tz_localize(ZONA_HORARIA, ambiguous="NaT", nonexistent="NaT")
                      .dt.tz_convert("UTC"))
    limpio = limpio.dropna(subset=["hora"])
    # Evitar sobrescrituras: +1 ns por cada repetición de (hora + tags)
    limpio["_n"] = limpio.groupby(["hora"] + TAGS).cumcount()
    limpio["hora"] = limpio["hora"] + pd.to_timedelta(limpio["_n"], unit="ns")
    limpio = (limpio.drop(columns="_n").sort_values("hora").set_index("hora"))
    return limpio


def cargar_historico(client, org: str, bucket: str) -> int:
    """Carga el CSV del histórico en el bucket. Devuelve el número de filas."""
    if not os.path.exists(CSV):
        print(
            f"[loader] AVISO: CSV del histórico no encontrado en '{CSV}'. "
            "No se carga nada (monta ./BDA/ImporCsvPandas:/data:ro).",
            flush=True,
        )
        return 0

    print(f"[loader] leyendo CSV {CSV}...", flush=True)
    limpio = limpiar(pd.read_csv(CSV, encoding="utf-8-sig"))
    print(
        f"[loader] filas válidas: {len(limpio):,} "
        f"rango: {limpio.index.min()} -> {limpio.index.max()}",
        flush=True,
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)
    # Escritura por lotes: evita peticiones gigantes con todo el histórico.
    for i in range(0, len(limpio), TAMANO_LOTE):
        lote = limpio.iloc[i:i + TAMANO_LOTE]
        write_api.write(bucket=bucket, org=org, record=lote,
                        data_frame_measurement_name=MEASUREMENT,
                        data_frame_tag_columns=TAGS)
        print(f"[loader] subidas {min(i + TAMANO_LOTE, len(limpio)):,} / {len(limpio):,}",
              flush=True)
    write_api.close()
    print("[loader] carga del histórico completada.", flush=True)
    return len(limpio)


def main() -> int:
    url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    org = os.getenv("INFLUXDB_ORG", "")
    bucket = os.getenv("INFLUXDB_BUCKET", "")
    token = _resolver_token()

    if _is_placeholder(token) or _is_placeholder(bucket) or _is_placeholder(org):
        print(
            "[loader] Configuración de ejemplo detectada "
            "(org/bucket/token sin rellenar). Nada que cargar, salgo OK. "
            "Rellena .env; los tokens los genera el contenedor influx-tokens-init.",
            flush=True,
        )
        return 0

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with InfluxDBClient(url=url, token=token, org=org, timeout=60_000) as client:
                if not client.ping():
                    raise RuntimeError("ping a InfluxDB devolvió False")
                filas = cargar_historico(client, org, bucket)
                point = (
                    Point("deploy_heartbeat")
                    .field("ok", 1)
                    .field("historico_cargado", int(filas > 0))
                    .tag("service", "loader")
                )
                client.write_api(write_options=SYNCHRONOUS).write(
                    bucket=bucket, org=org, record=point
                )
            print(
                f"[loader] Histórico {'cargado' if filas else 'no disponible'} "
                f"y heartbeat escritos en bucket '{bucket}' ({url}).",
                flush=True,
            )
            return 0
        except Exception as exc:  # noqa: BLE001 - log y reintento
            last_error = exc
            print(
                f"[loader] Intento {attempt}/3 fallido: {exc}. Reintento en 5s...",
                flush=True,
            )
            time.sleep(5)

    print(
        f"[loader] ERROR: no se pudo completar la carga tras 3 intentos: {last_error}",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
