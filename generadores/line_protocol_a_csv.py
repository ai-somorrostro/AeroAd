#!/usr/bin/env python3
"""Convierte el volcado line protocol de generador_v3.py a CSV.

El generador escribe "captaciones,..." con claves que contienen espacios sin
escapar (OS del sistema, Pais de origen, Rango de edad), por lo que no se puede
usar un parser generico de line protocol. Este conversor conoce el orden y las
claves exactas del generador.

Limitacion conocida: el line protocol omite el timestamp cuando la hora es
invalida, asi que no se puede distinguir entre "" y "fecha_incorrecta".
Por defecto se marca como "fecha_incorrecta"; ambas se rechazan igual en el
loader y en el notebook.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

COLUMNAS = [
    "Hora de la captación",
    "MAC",
    "Fabricante",
    "Nombre",
    "OS del sistema",
    "Idioma del OS",
    "Rango de edad",
    "Email",
    "Pais de origen",
]

TAG_KEYS = ["Fabricante", "OS del sistema", "Idioma del OS", "Pais de origen", "MAC"]
FIELD_KEYS = ["Nombre", "Rango de edad", "Email"]


def _consumir_tag(s: str) -> tuple[str, str]:
    """Devuelve (valor, resto) hasta el siguiente ',' o espacio sin escapar."""
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c in ", ":
            return s[:i], s[i:]
        i += 1
    return s, ""


def _desescapar_tag(valor: str) -> str:
    salida: list[str] = []
    i = 0
    while i < len(valor):
        if valor[i] == "\\" and i + 1 < len(valor):
            salida.append(valor[i + 1])
            i += 2
        else:
            salida.append(valor[i])
            i += 1
    return "".join(salida)


def _consumir_field(s: str) -> tuple[str, str]:
    """Consume un field entrecomillado y devuelve (valor, resto)."""
    if not s.startswith('"'):
        raise ValueError(f"field no entrecomillado: {s[:40]!r}")
    salida: list[str] = []
    i = 1
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            salida.append(s[i + 1])
            i += 2
            continue
        if c == '"':
            return "".join(salida), s[i + 1 :]
        salida.append(c)
        i += 1
    raise ValueError("field sin comilla de cierre")


def _parsear_linea(linea: str, tz: ZoneInfo, hora_invalida: str) -> dict[str, str]:
    if not linea.startswith("captaciones"):
        raise ValueError("la linea no empieza por 'captaciones'")
    resto = linea[len("captaciones") :]
    registro = {c: "" for c in COLUMNAS}

    if resto.startswith(","):
        resto = resto[1:]
        for clave in TAG_KEYS:
            prefijo = clave + "="
            if not resto.startswith(prefijo):
                continue
            valor, resto = _consumir_tag(resto[len(prefijo) :])
            registro[clave] = _desescapar_tag(valor)
            if resto.startswith(","):
                resto = resto[1:]
            elif resto.startswith(" "):
                resto = resto[1:]
                break
            elif not resto:
                break

    if resto.startswith(" "):
        resto = resto[1:]

    for clave in FIELD_KEYS:
        prefijo = clave + "="
        if not resto.startswith(prefijo):
            continue
        valor, resto = _consumir_field(resto[len(prefijo) :])
        registro[clave] = valor
        if resto.startswith(","):
            resto = resto[1:]
        elif resto.startswith(" "):
            resto = resto[1:]
            break
        elif not resto:
            break

    ts_txt = resto.strip()
    if ts_txt and ts_txt.isdigit():
        dt = datetime.fromtimestamp(int(ts_txt) / 1_000_000_000, tz=tz)
        registro["Hora de la captación"] = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        registro["Hora de la captación"] = hora_invalida

    return registro


def convertir(entrada: Path, salida: Path, tz: str, hora_invalida: str) -> int:
    zona = ZoneInfo(tz)
    filas = 0
    with entrada.open(encoding="utf-8") as fin, salida.open(
        "w", encoding="utf-8-sig", newline=""
    ) as fout:
        writer = csv.DictWriter(fout, fieldnames=COLUMNAS, lineterminator="\n")
        writer.writeheader()
        for num, linea in enumerate(fin, 1):
            linea = linea.rstrip("\n")
            if not linea:
                continue
            try:
                writer.writerow(_parsear_linea(linea, zona, hora_invalida))
            except Exception as exc:  # noqa: BLE001 - contexto de linea
                raise ValueError(f"linea {num}: {exc}") from exc
            filas += 1
    return filas


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convierte line protocol de generador_v3.py a CSV."
    )
    parser.add_argument(
        "entrada",
        nargs="?",
        default="captaciones_junio_2026_v3.txt",
        help="fichero line protocol (por defecto el que genera generador_v3.py)",
    )
    parser.add_argument(
        "salida",
        nargs="?",
        default="captaciones_junio_2026.csv",
        help="CSV de salida",
    )
    parser.add_argument(
        "--tz",
        default="Europe/Madrid",
        help="zona horaria con la que se genero el line protocol",
    )
    parser.add_argument(
        "--hora-invalida",
        default="fecha_incorrecta",
        help='valor para filas sin timestamp (por defecto "fecha_incorrecta")',
    )
    args = parser.parse_args()

    filas = convertir(Path(args.entrada), Path(args.salida), args.tz, args.hora_invalida)
    print(f"Convertidas {filas:,} filas -> {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
