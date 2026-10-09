"""Loader AeroAdd (esqueleto listo para deploy).

Servicio one-shot: verifica la conexión con InfluxDB y escribe un punto
de heartbeat. Nunca rompe el deploy: si falta configuración real
(token/bucket de ejemplo) avisa por log y sale con 0 para que
`docker compose up` no marque error. La ingesta real la añadirán
los compañeros en este mismo servicio.
"""

import os
import sys
import time


def _is_placeholder(value: str) -> bool:
    return (not value) or value == "CAMBIAME" or value.startswith("CAMBIAME-")


def main() -> int:
    url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    org = os.getenv("INFLUXDB_ORG", "")
    bucket = os.getenv("INFLUXDB_BUCKET", "")
    token = os.getenv("INFLUXDB_TOKEN", "")

    if _is_placeholder(token) or _is_placeholder(bucket) or _is_placeholder(org):
        print(
            "[loader] Configuración de ejemplo detectada "
            "(org/bucket/token sin rellenar en .env). Nada que cargar, salgo OK. "
            "Rellena .env y genera tokens con scripts/create-tokens.sh "
            "cuando quieras ingesta real.",
            flush=True,
        )
        return 0

    try:
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError as exc:
        print(f"[loader] ERROR: dependencias no instaladas: {exc}", flush=True)
        return 1

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with InfluxDBClient(url=url, token=token, org=org) as client:
                if not client.ping():
                    raise RuntimeError("ping a InfluxDB devolvió False")
                point = (
                    Point("deploy_heartbeat")
                    .field("ok", 1)
                    .tag("service", "loader")
                )
                client.write_api(write_options=SYNCHRONOUS).write(
                    bucket=bucket, org=org, record=point
                )
            print(
                f"[loader] Heartbeat escrito en bucket '{bucket}' ({url}).",
                flush=True,
            )
            return 0
        except Exception as exc:  # noqa: BLE001 - esqueleto: log y reintento
            last_error = exc
            print(
                f"[loader] Intento {attempt}/3 fallido: {exc}. Reintento en 5s...",
                flush=True,
            )
            time.sleep(5)

    print(
        f"[loader] ERROR: no se pudo escribir el heartbeat tras 3 intentos: {last_error}",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
