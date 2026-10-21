# AeroAdd

Proyecto de Big Data + IA para ingesta, visualización y análisis de datos del
aeropuerto de Madrid-Barajas: captaciones WiFi, ventas, meteorología y llegadas
de vuelos en InfluxDB, con dashboards en Grafana y flujos en Node-RED.

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
│   ├── nodered/                      # imagen propia + flows productivos (5 pestañas)
│   │   ├── Dockerfile                # base fijada + node-red-contrib-influxdb
│   │   ├── package.json              # dependencia del contrib (versión fijada)
│   │   └── flows.json                # simulador WiFi, API Open-Meteo, API llegadas Barajas, ventas, smoke test
│   ├── loader/             # esqueleto: influxdb-client + heartbeat (pandas lo añadirá la ingesta real)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/main.py
├── data/                   # datasets (gitignorados salvo .gitkeep)
├── notebooks/              # parte SBD
├── docs/                   # parte MIA, capturas, organigrama de buckets
├── BDA/ImporCsvPandas/     # CSV históricos (captaciones junio, rechazadas, dataset integrado)
├── generadores/            # generadores sintéticos (500K captaciones, ventas)
└── scripts/                          # create-tokens.sh (tokens InfluxDB); create-grafana-sa.sh (service accounts del MCP); load-captaciones.py (carga histórica del CSV a InfluxDB)
```

## Servicios

| Servicio  | Imagen / build         | Puerto (ejemplo, ver `.env`) | Estado |
|-----------|------------------------|------------------------------|--------|
| influxdb  | `influxdb:2.7`         | `8086`                       | Listo para levantar (`up -d influxdb`); rellenar a mano en `.env` usuario, contraseña, org, bucket y token |
| grafana   | `grafana/grafana:11.2.0` | `3000`                     | Datasource InfluxDB (Flux) provisionado con token de lectura; admin y puerto por `.env` |
| nodered   | build `./services/nodered` (`node-red:4.0.2` + contrib InfluxDB) | `1880` | 5 flows: simulador WiFi → `captaciones_tiemporeal`, Open-Meteo → `contexto_madrid`, llegadas Barajas (AeroDataBox/RapidAPI) → `contexto_madrid`, simulador ventas → `captaciones_tiemporeal`, smoke test. Token de escritura por `.env` (`NODERED_INFLUXDB_TOKEN`); la API de vuelos necesita además `RAPIDAPI_KEY` (ver Configuración) |
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
- Python 3.12 con `pandas` e `influxdb-client` (solo para la carga histórica del CSV):
  ```bash
  python3.12 -m pip install pandas influxdb-client
  ```

## Configuración

1. Copiar la plantilla de entorno:
   ```bash
   cp .env.example .env
   ```
2. Rellenar a mano en `.env` los valores marcados con TODO: usuarios, contraseñas, organización, bucket, token, URLs y puertos. El archivo `.env` no se sube al repositorio.
3. **Importante en Windows/WSL**: `.env` y los scripts `.sh` deben tener finales de línea **LF**, no CRLF. Un CRLF en `services/influxdb/init/01-create-buckets.sh` impide arrancar InfluxDB (ver Resolución de problemas). Conversión rápida:
   ```bash
   sed -i 's/\r$//' .env services/influxdb/init/*.sh scripts/*.sh
   ```

### Clave de la API de vuelos (AeroDataBox / RapidAPI)

El flow de llegadas a Barajas lee la clave de la **variable de entorno del contenedor**. Solo hay que ponerla en `.env`:

1. En `.env`: `RAPIDAPI_KEY=<tu clave>` (sin comillas).
2. Reconstruir Node-RED para que el contenedor reciba la variable:
   ```bash
   docker compose up -d --build nodered
   ```

La pestaña `3 · API llegadas a Barajas (AeroDataBox)` ya tiene `RAPIDAPI_KEY` configurada como referencia de entorno (`type: env`), así que no hace falta escribir la clave en la interfaz. Sin clave válida ese pipeline no trae horarios; el resto de flows siguen funcionando. No subir claves reales al repositorio: van solo en `.env` (gitignorado), nunca en ficheros del repo.

### Tokens de InfluxDB (mínimo privilegio)

Con InfluxDB levantado y `.env` relleno (org, bucket y token admin). **En una
instalación desde cero, deja vacías** `GRAFANA/NODERED/LOADER_INFLUXDB_TOKEN`
(así vienen en `.env.example`): el script es idempotente y omite las variables
que ya tienen valor, de modo que unos tokens copiados de otro InfluxDB quedarían
inválidos (401) sin avisar.

Opción A — con el CLI `influx` instalado en el equipo:

```bash
./scripts/create-tokens.sh
```

Opción B — sin instalar nada (usa el CLI dentro del contenedor):

```bash
set -a && source .env && set +a
docker exec aeroadd-influxdb influx auth create --org "$INFLUXDB_INIT_ORG" \
  --token "$INFLUXDB_ADMIN_TOKEN" --description "grafana-read" --read-buckets
docker exec aeroadd-influxdb influx auth create --org "$INFLUXDB_INIT_ORG" \
  --token "$INFLUXDB_ADMIN_TOKEN" --description "nodered-write" --write-buckets
docker exec aeroadd-influxdb influx auth create --org "$INFLUXDB_INIT_ORG" \
  --token "$INFLUXDB_ADMIN_TOKEN" --description "loader-write" --write-buckets
```

Pega cada token generado en su variable de `.env` (`GRAFANA/NODERED/LOADER_INFLUXDB_TOKEN`).

Después levanta (o reinicia) el resto para que Grafana recoja su token, ya que el datasource se provisiona al arrancar:

```bash
docker compose up -d --build
# si Grafana ya estaba levantada:
docker compose restart grafana
```

Ojo: `down -v` borra los datos de InfluxDB y con ellos los tokens generados. Tras un `down -v` hay que borrar las líneas `*_INFLUXDB_TOKEN` de `.env` (dejarlas vacías) y volver a ejecutar `create-tokens.sh`; si ya tienen valor el script las omite y quedan tokens inválidos (401).

## Cómo lanzarlo

```bash
docker compose config   # valida el compose (funciona con y sin .env, usa valores de ejemplo por defecto)
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose down     # detiene la pila
```

Nota: `loader` sigue siendo un esqueleto funcional (heartbeat); la ingesta real queda pendiente. Toda la pila arranca con valores de ejemplo.

### Carga histórica (CSV de junio → InfluxDB)

El dashboard de análisis de clientes necesita el histórico. Con la pila levantada:

```bash
set -a && source .env && set +a
INFLUX_TOKEN="$INFLUXDB_ADMIN_TOKEN" INFLUX_URL="http://localhost:8086" \
  INFLUXDB_INIT_ORG="$INFLUXDB_INIT_ORG" \
  python3.12 scripts/load-captaciones.py
```

Lee `BDA/ImporCsvPandas/captaciones_junio_2026.csv` (~500K filas), lo limpia igual que el notebook del equipo y lo sube al bucket `captaciones_julio` en lotes de 10.000. Tarda unos minutos; es idempotente (re-ejecutarlo reescribe los mismos puntos).

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

## Cómo se utiliza

### Accesos

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| Grafana | http://localhost:3000 | acceso anónimo como Viewer (sin login); admin `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` de `.env` |
| Node-RED | http://localhost:1880 | sin autenticación |
| InfluxDB | http://localhost:8086 | `INFLUXDB_INIT_USERNAME` / `INFLUXDB_INIT_PASSWORD` de `.env` |

### Dashboards (Grafana → carpeta AeroAdd)

| Dashboard | Bucket origen | Rango de tiempo a usar |
|-----------|---------------|------------------------|
| Análisis de clientes | `captaciones_julio` (histórico) | **junio 2026** (`2026-06-01 → 2026-07-01`) o *Last 90 days*; con el rango por defecto reciente sale NoData porque esos datos son de junio |
| Monitorización tiempo real | `captaciones_tiemporeal` | reciente (*Last 1–6 hours*); lo alimenta el simulador WiFi de Node-RED |
| Ventas aeropuerto | `captaciones_tiemporeal` + `contexto_madrid` | reciente; lo alimenta el simulador de ventas + Open-Meteo |
| Oportunidades publicitarias | `captaciones_tiemporeal` + `contexto_madrid` | reciente |

Los dashboards se provisionan solos desde `services/grafana/provisioning/dashboards/` y Grafana los recarga cada 10 s al modificar los JSON. Regla general ante un NoData: comprobar que el **rango del selector** cubre los datos (histórico = junio; simuladores = ahora).

### Node-RED

Cada pestaña es un pipeline independiente con su propio ritmo (inyectores `cada 3 h`, `cada 60 s`, etc.). Para forzar una ejecución inmediata sin esperar al temporizador: abrir el flow y pulsar el botón del nodo `inject`, o por API:

```bash
curl -X POST http://localhost:1880/inject/<id-del-nodo-inject>
```

Los writes a InfluxDB se hacen por HTTP (line protocol) con el token `NODERED_INFLUXDB_TOKEN`. Si un flow falla por credenciales, el error sale en `docker compose logs nodered`.

### Consultar InfluxDB a mano

```bash
set -a && source .env && set +a
docker exec aeroadd-influxdb influx bucket list --token "$INFLUXDB_ADMIN_TOKEN" --org "$INFLUXDB_INIT_ORG"
docker exec aeroadd-influxdb influx query --token "$INFLUXDB_ADMIN_TOKEN" --org "$INFLUXDB_INIT_ORG" \
  'from(bucket:"captaciones_tiemporeal") |> range(start:-1h) |> limit(n:5)'
```

## Resolución de problemas

- **InfluxDB en bucle `unhealthy` (`failed to exec ... 01-create-buckets.sh: No such file or directory`)**: el script tiene finales CRLF; el kernel del contenedor no encuentra el intérprete `/bin/bash\r`. Pasar a LF (`sed -i 's/\r$//'`) y levantar de cero: `docker compose down -v && docker compose up -d`.
- **`401 Unauthorized` en Grafana o Node-RED**: los tokens de `.env` no existen en ese InfluxDB (pasa siempre tras un `down -v`). Vaciar las líneas `GRAFANA/NODERED/LOADER_INFLUXDB_TOKEN`, ejecutar `./scripts/create-tokens.sh` y reiniciar (`docker compose up -d grafana nodered`).
- **NoData con datos existentes**: casi siempre es el rango de tiempo del dashboard (ver tabla de arriba) o el filtro de variable (`tipo_tienda`).
- **`type conflict: float != int` en un panel Flux**: algún campo entero se compara con un literal decimal (`== 1.0`) o se mezcla con floats en un `if/else`. Envolver el campo con `float(v: ...)` en la query del panel.

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
