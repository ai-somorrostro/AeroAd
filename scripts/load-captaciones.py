#!/usr/bin/env python3
"""Carga historica de BDA/ImporCsvPandas/captaciones_junio_2026.csv a InfluxDB.

Replica la logica del notebook del equipo
(BDA/ImporCsvPandas/carga_historico_AeroAdd.ipynb): limpieza, normalizacion
y subida por lotes. Adaptado a esta pila (org/bucket del .env).

Requiere: pip install pandas influxdb-client ; InfluxDB levantado.
Uso:
  INFLUX_TOKEN=$(grep '^INFLUXDB_ADMIN_TOKEN=' .env | cut -d= -f2-) \
    python3 scripts/load-captaciones.py
Variables (todas opcionales salvo INFLUX_TOKEN):
  INFLUX_URL (http://localhost:8086), INFLUX_ORG e INFLUX_BUCKET del .env,
  CSV (ruta al fichero).
Idempotente en efecto: reejecutarlo reescribe los mismos puntos.
"""
import os
import sys

import pandas as pd

CSV = os.environ.get("CSV", "BDA/ImporCsvPandas/captaciones_junio_2026.csv")
INFLUX_URL = os.environ.get("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUXDB_INIT_ORG", "ejemplo-org")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "captaciones_tiemporeal")
MEASUREMENT = "captaciones"
ZONA_HORARIA = "Europe/Madrid"  # las horas del CSV son hora local
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


def limpiar(df):
    """Devuelve el DataFrame limpio con la hora (UTC) como indice."""
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
    # Evitar sobrescrituras: +1 ns por cada repeticion de (hora + tags)
    limpio["_n"] = limpio.groupby(["hora"] + TAGS).cumcount()
    limpio["hora"] = limpio["hora"] + pd.to_timedelta(limpio["_n"], unit="ns")
    limpio = (limpio.drop(columns="_n").sort_values("hora").set_index("hora"))
    return limpio


def main():
    from influxdb_client import InfluxDBClient, WriteOptions

    if not INFLUX_TOKEN:
        sys.exit("Falta INFLUX_TOKEN (usa el INFLUXDB_ADMIN_TOKEN de tu .env)")
    print("Leyendo CSV...", flush=True)
    limpio = limpiar(pd.read_csv(CSV, encoding="utf-8-sig"))
    print(f"Originales -> listas: {len(limpio):,} "
          f"rango: {limpio.index.min()} -> {limpio.index.max()}", flush=True)
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN,
                        org=INFLUX_ORG, timeout=60_000) as client:
        write_api = client.write_api(write_options=WriteOptions(
            batch_size=TAMANO_LOTE, flush_interval=5_000))
        for i in range(0, len(limpio), TAMANO_LOTE):
            lote = limpio.iloc[i:i + TAMANO_LOTE]
            write_api.write(bucket=INFLUX_BUCKET, record=lote,
                            data_frame_measurement_name=MEASUREMENT,
                            data_frame_tag_columns=TAGS)
            print(f"  subidas {min(i + TAMANO_LOTE, len(limpio)):,} / {len(limpio):,}",
                  flush=True)
        write_api.close()
    print("Carga completada.", flush=True)


if __name__ == "__main__":
    main()
