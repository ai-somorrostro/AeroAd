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
│   ├── loader/             # esqueleto: influxdb-client + heartbeat (pandas lo añadirá la ingesta real)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/main.py
├── data/                   # datasets (gitignorados salvo .gitkeep)
├── notebooks/              # parte SBD
├── docs/                   # parte MIA, capturas, organigrama de buckets
└── scripts/                          # create-tokens.sh (tokens InfluxDB); create-grafana-sa.sh (service accounts del MCP)
```

## Servicios

| Servicio  | Imagen / build         | Puerto (ejemplo, ver `.env`) | Estado |
|-----------|------------------------|------------------------------|--------|
| influxdb  | `influxdb:2.7`         | `8086`                       | Listo para levantar (`up -d influxdb`); rellenar a mano en `.env` usuario, contraseña, org, bucket y token |
| grafana   | `grafana/grafana:11.2.0` | `3000`                     | Datasource InfluxDB (Flux) provisionado con token de lectura; admin y puerto por `.env` |
| nodered   | build `./services/nodered` (`node-red:4.0.2` + contrib InfluxDB) | `1880` | Flow de prueba que escribe en Influx con el token de escritura; puerto y token por `.env` |
| loader    | `build: ./services/loader` | — (sin puerto)             | Esqueleto one-shot: heartbeat a Influx; ingesta real pendiente |
| mcp-direccion | `grafana/mcp-grafana:2.0.2` | `8000` | MCP oficial; rol **cúpula directiva** (Viewer), service account propia |
| mcp-analisis  | `grafana/mcp-grafana:2.0.2` | `8001` | MCP oficial; rol **análisis** (Viewer), service account propia |
| mcp-it        | `grafana/mcp-grafana:2.0.2` | `8002` | MCP oficial; rol **IT** (Viewer por ahora), service account propia |

Red propia `aeroadd` y volúmenes `influxdb-data`, `grafana-data`, `nodered-data`, `mcp-secrets` (tokens de las service accounts).

Nota: la imagen MCP se fija como `grafana/mcp-grafana:2.0.2` (sin `v`). En Docker Hub
el tag no lleva prefijo, aunque la release/tag de git correspondiente sí (`v2.0.2`).

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

Después levanta (o reinicia) el resto para que Grafana recoja su token, ya que el datasource se provisiona al arrancar:

```bash
docker compose up -d --build
# si Grafana ya estaba levantada:
docker compose restart grafana
```

## Cómo lanzarlo

```bash
docker compose config   # valida el compose (funciona con y sin .env, usa valores de ejemplo por defecto)
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose down     # detiene la pila
```

Nota: `loader` sigue siendo un esqueleto funcional (heartbeat); la ingesta real queda pendiente. Toda la pila arranca con valores de ejemplo.

### Verificar que todo responde

```bash
curl http://localhost:3000/api/health                          # Grafana
curl http://localhost:8000/healthz                             # MCP dirección
curl http://localhost:8001/healthz                             # MCP análisis
curl http://localhost:8002/healthz                             # MCP IT
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:1880/ # Node-RED
docker compose logs loader --tail 5                             # heartbeat a InfluxDB
```

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

## MCP de Grafana (una instancia por rol)

El MCP oficial `grafana/mcp-grafana` se levanta en **tres instancias**, una por rol.
Cada una se autentica con su propia **service account** de Grafana, de modo que el
agente hereda los permisos de ese rol y no puede suplantar a otro.

Las service accounts y sus tokens se crean solas al levantar la pila: el servicio
efímero `grafana-sa-init` ejecuta `scripts/create-grafana-sa.sh` (idempotente) y deja
un fichero de token por rol en el volumen `mcp-secrets`. Solo hay que rellenar en
`.env` el usuario/contraseña admin de Grafana y los **tokens de llamante** por rol
(no se generan solos: son la credencial con la que el cliente habla con cada MCP).

### Conectar un cliente MCP

| Rol | URL MCP | Puerto | Token de llamante (`.env`) |
|-----|---------|--------|----------------------------|
| Cúpula directiva | `http://localhost:8000/mcp` | 8000 | `MCP_GRAFANA_SERVER_TOKEN_DIRECCION` |
| Análisis | `http://localhost:8001/mcp` | 8001 | `MCP_GRAFANA_SERVER_TOKEN_ANALISIS` |
| IT | `http://localhost:8002/mcp` | 8002 | `MCP_GRAFANA_SERVER_TOKEN_IT` |

El cliente debe enviar `Authorization: Bearer <token de su rol>`. Los puertos son
configurables con `MCP_DIRECCION_PORT`, `MCP_ANALISIS_PORT` y `MCP_IT_PORT`.

`opencode.json` ya trae una entrada por rol (`grafana-direccion`, `grafana-analisis`,
`grafana-it`) para **desarrollo y pruebas**; no es el consumidor final. Los tokens
de llamante se leen de las variables de entorno de opencode.

Las herramientas habilitadas son solo las de consulta: InfluxDB (Flux), datasources y
dashboards en **lectura**; escrituras, alertas y consultas de panel están
deshabilitadas.

### Limitaciones

- El agente **puede equivocarse con las consultas Flux**: genera la query a partir de
  la petición en lenguaje natural y puede producir una consulta incorrecta o
  incompleta. Conviene revisar los resultados y, si hace falta, dar la query exacta.
- **Permisos**: las tres cuentas son `Viewer` (solo lectura) mientras el equipo de
  Grafana no tenga montado el RBAC fino por carpetas. El reparto de dashboards por rol
  y el rol de edición de IT llegarán con ese RBAC; hasta entonces IT tampoco edita.
- `down -v` borra el volumen `mcp-secrets`: en el siguiente `up` el init regenera los
  tokens automáticamente.

## Autores

[Ibai Bonilla](https://github.com/IbaiBo) \
[Sendoa Perez](https://github.com/Sendoa6) \
[Erlaitz Alonso](https://github.com/3rlaitz)
