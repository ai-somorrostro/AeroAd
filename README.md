# AeroAdd

Proyecto de Big Data + IA para ingesta, visualización y análisis de datos.

## Estructura del repositorio

```text
AeroAdd/
├── README.md
├── .gitignore
├── .env.example            # variables de ejemplo, SIN secretos reales
├── docker-compose.yml
├── AGENTS.md               # instrucciones para opencode
├── openspec/               # lo genera openspec
├── services/
│   ├── influxdb/           # init: 01-create-buckets.sh (buckets de INFLUXDB_EXTRA_BUCKETS)
│   ├── grafana/
│   │   └── provisioning/
│   │       └── datasources/influxdb.yml  # datasource InfluxDB (Flux) con token de lectura
│   ├── nodered/                      # imagen propia + flow de prueba
│   │   ├── Dockerfile                # base fijada + node-red-contrib-influxdb
│   │   ├── package.json              # dependencia del contrib (versión fijada)
│   │   └── flows.json                # punto de prueba a Influx (URL/org/token del entorno)
│   ├── loader/             # python + pandas
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/
│   └── mcp/                # servicio MCP
│       ├── Dockerfile
│       └── src/
├── data/                   # datasets (gitignorados salvo .gitkeep)
├── notebooks/              # parte SBD
├── docs/                   # parte MIA, capturas, organigrama de buckets
└── scripts/                          # create-tokens.sh (tokens InfluxDB); TODO: up.sh, down.sh, reset.sh
```

## Servicios

| Servicio  | Imagen / build         | Puerto (ejemplo, ver `.env`) | Estado |
|-----------|------------------------|------------------------------|--------|
| influxdb  | `influxdb:2.7`         | `8086`                       | Listo para levantar (`up -d influxdb`); rellenar a mano en `.env` usuario, contraseña, org, bucket y token |
| grafana   | `grafana/grafana:11.2.0` | `3000`                     | Datasource InfluxDB (Flux) provisionado con token de lectura; admin y puerto por `.env` |
| nodered   | build `./services/nodered` (`node-red:4.0.2` + contrib InfluxDB) | `1880` | Flow de prueba que escribe en Influx con el token de escritura; puerto y token por `.env` |
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

### Tokens de InfluxDB (mínimo privilegio)

Con InfluxDB levantado y `.env` relleno (org, bucket y token admin):

```bash
./scripts/create-tokens.sh
```

Genera un token de solo lectura para Grafana y dos de solo escritura (Node-RED y loader), y los guarda en `.env` sin duplicar líneas. Es idempotente: si la variable ya tiene valor, no crea otro token. Nunca muestra los valores por pantalla.

## Cómo lanzarlo

```bash
docker compose config   # valida el compose (funciona con y sin .env, usa valores de ejemplo por defecto)
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose down     # detiene la pila
```

Nota: `loader` y `mcp` aún no tienen `Dockerfile`, así que `up --build` fallará en esos dos servicios hasta que se implementen. El resto de la pila (InfluxDB, Grafana, Node-RED) arranca con valores de ejemplo.

El `flows.json` de Node-RED va horneado en su imagen: tras modificarlo hay que reconstruir con `docker compose up -d --build nodered`. Si el volumen `nodered-data` ya existía con un flow anterior, además hay que recrearlo (ojo: se pierden sus datos):

```bash
docker compose stop nodered && docker compose rm -f nodered
docker volume rm aeroadd_nodered-data
docker compose up -d nodered
```

Para levantar solo InfluxDB (ya listo):

```bash
cp .env.example .env   # si aún no existe; rellenar a mano usuario, contraseña, org, bucket y token
docker compose up -d influxdb
docker compose logs -f influxdb
```

## Autores

[Ibai Bonilla](https://github.com/IbaiBo) \
[Sendoa Perez](https://github.com/Sendoa6) \
[Erlaitz Alonso](https://github.com/3rlaitz)
