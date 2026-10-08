# AeroAdd

Proyecto de Big Data + IA para ingesta, visualización y análisis de datos.

## Estructura del repositorio

```text
AeroAdd/
├── docker-compose.yml                # Pila base: InfluxDB, Grafana, Node-RED, loader y MCP
├── .env.example                      # Plantilla de variables (copiar a .env y rellenar a mano)
├── .gitignore
├── README.md
├── AGENTS.md
├── services/
│   ├── influxdb/                     # TODO: configuración de InfluxDB
│   ├── grafana/
│   │   └── provisioning/             # TODO: aprovisionamiento de Grafana
│   ├── nodered/                      # TODO: flujos de Node-RED
│   ├── loader/
│   │   └── src/                      # TODO: loader en Python+pandas
│   └── mcp/
│       └── src/                      # TODO: servicio MCP
├── data/                             # Datos locales de ejemplo (no versionar contenido, ver .gitignore)
├── notebooks/                        # TODO: notebooks de análisis
├── docs/                             # TODO: documentación del proyecto
└── scripts/                          # TODO: scripts auxiliares
```

## Servicios

| Servicio  | Imagen / build         | Puerto (ejemplo, ver `.env`) | Estado |
|-----------|------------------------|------------------------------|--------|
| influxdb  | `influxdb:2.7`         | `8086`                       | Base definida, pendiente de configuración (org, bucket, token) |
| grafana   | `grafana/grafana:11.2.0` | `3000`                     | Base definida, pendiente de aprovisionamiento |
| nodered   | `nodered/node-red:4.0.2` | `1880`                     | Base definida, pendiente de flujos |
| loader    | `build: ./services/loader` | — (sin puerto)             | Pendiente de Dockerfile e implementación |
| mcp       | `build: ./services/mcp`    | `8000` (ejemplo)           | Pendiente de Dockerfile e implementación |

Red propia `aeroadd` y volúmenes `influxdb-data`, `grafana-data`, `nodered-data`.

## Requisitos previos

- Docker
- Docker Compose (v2, plugin `docker compose`)
- Git

## Configuración

1. Copiar la plantilla de entorno:
   ```bash
   cp .env.example .env
   ```
2. Rellenar a mano en `.env` los valores marcados con TODO: usuarios, contraseñas, organización, bucket, token, URLs y puertos. El archivo `.env` no se sube al repositorio.

## Cómo lanzarlo

```bash
docker compose config   # valida el compose (funciona con y sin .env, usa valores de ejemplo por defecto)
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose down     # detiene la pila
```

Nota: `loader` y `mcp` aún no tienen `Dockerfile`, así que `up --build` fallará en esos dos servicios hasta que se implementen. El resto de la pila (InfluxDB, Grafana, Node-RED) arranca con valores de ejemplo.

## Autores

@IbaiBo \
@Sendoa6 \
@3rlaitz
