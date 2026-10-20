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
│   ├── loader/             # one-shot: carga el histórico del CSV (pandas/influxdb-client) + heartbeat
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/main.py
├── data/                   # datasets (gitignorados salvo .gitkeep)
├── notebooks/              # parte SBD
├── docs/                   # parte MIA, capturas, organigrama de buckets
├── BDA/ImporCsvPandas/     # CSV históricos (captaciones junio, rechazadas, dataset integrado)
├── generadores/            # generadores sintéticos (500K captaciones, ventas)
└── scripts/                          # setup-env.sh (genera .env con credenciales aleatorias); create-influx-tokens.sh (tokens InfluxDB, se ejecuta dentro del contenedor influx-tokens-init); create-grafana-sa.sh (service accounts del MCP)
```

## Servicios

| Servicio  | Imagen / build         | Puerto (ejemplo, ver `.env`) | Estado |
|-----------|------------------------|------------------------------|--------|
| influxdb  | `influxdb:2.7`         | `8086`                       | Se inicializa solo en el arranque (usuario, contraseña, org, bucket y tokens via `docker compose up -d --build`); credenciales en `.env` (las genera `scripts/setup-env.sh`) |
| grafana   | `grafana/grafana:11.2.0` | `3000`                     | Datasource InfluxDB (Flux) provisionado con token de lectura; admin y puerto por `.env` |
| nodered   | build `./services/nodered` (`node-red:4.0.2` + contrib InfluxDB) | `1880` | 5 flows: simulador WiFi → `captaciones_tiemporeal`, Open-Meteo → `contexto_madrid`, llegadas Barajas (AeroDataBox/RapidAPI) → `contexto_madrid`, simulador ventas → `captaciones_tiemporeal`, smoke test. El token de escritura lo exporta el entrypoint leyendo el volumen `mcp-secrets`; la API de vuelos necesita además `RAPIDAPI_KEY` (ver Configuración) |
| loader    | `build: ./services/loader` | — (sin puerto)             | One-shot: carga el histórico del CSV de junio (~461K filas) en `captaciones_julio` y escribe un heartbeat; su token de escritura lo lee del volumen `mcp-secrets` |
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

(La imagen del loader ya lleva `pandas` e `influxdb-client`, no hace falta instalar nada más en el equipo.)

## Configuración

**Forma recomendada (sin escribir ninguna credencial a mano):**

```bash
./scripts/setup-env.sh   # genera .env con contraseñas y tokens aleatorios (chmod 600)
```

- Si no existe `.env`, lo crea desde `.env.example`; si ya existe, **solo rellena
  las variables vacías o con placeholder** (`CAMBIAME`/`CHANGEME`), nunca pisa tus valores.
- Genera aleatorios para: `INFLUXDB_INIT_PASSWORD`, `INFLUXDB_ADMIN_TOKEN`,
  `GRAFANA_ADMIN_PASSWORD` y los tokens de llamante del MCP
  (`MCP_GRAFANA_SERVER_TOKEN_*`).
- Pide la `RAPIDAPI_KEY` una sola vez por teclado (o Enter para dejarla vacía:
  el pipeline de llegadas queda inactivo, el resto de la pila funciona).
- No imprime ninguna credencial por pantalla; el fichero queda local
  (chmod 600) y nunca se sube al repositorio.

Alternativa manual:

1. Copiar la plantilla de entorno:
   ```bash
   cp .env.example .env
   ```
2. Rellenar en `.env` lo que cambie en tu despliegue local: usuarios, contraseñas,
   organización, token admin de InfluxDB, puertos y la `RAPIDAPI_KEY` del pipeline de
   llegadas. El archivo `.env` no se sube al repositorio.
3. **Importante en Windows/WSL**: `.env` y los scripts `.sh` deben tener finales de línea **LF**, no CRLF. Un CRLF en `services/influxdb/init/01-create-buckets.sh` impide arrancar InfluxDB (ver Resolución de problemas). Conversión rápida:
   ```bash
   sed -i 's/\r$//' .env services/influxdb/init/*.sh scripts/*.sh
   ```

**No hay que rellenar tokens de servicio a mano**: al levantar la pila, los
contenedores de inicialización los crean y los comparten por el volumen
`mcp-secrets` (ver más abajo).

### Clave de la API de vuelos (AeroDataBox / RapidAPI)

El flow de llegadas a Barajas la lee de la **variable de entorno del contenedor**:

- Con `scripts/setup-env.sh`: la pide una sola vez por teclado y la deja en
  `RAPIDAPI_KEY` de `.env`; el compose se la inyecta a Node-RED
  (`RAPIDAPI_KEY=${RAPIDAPI_KEY:-}`).
- Con `.env` a mano: escribe `RAPIDAPI_KEY=<tu clave>` (sin comillas) y levanta/reinicia.

Sin clave válida ese pipeline no trae horarios; el resto de flows siguen funcionando.
No subir claves reales al repositorio (el fichero `BDA/ApikeyFlights.txt` fue retirado
por seguridad): la clave va solo en `.env`, que está gitignorado.

### Tokens de InfluxDB (mínimo privilegio)

Los genera automáticamente el efímero `influx-tokens-init` al levantar la pila, con
el token admin de `.env` (`INFLUXDB_ADMIN_TOKEN`). Es idempotente y:

- Crea los buckets de `INFLUXDB_EXTRA_BUCKETS` vía `01-create-buckets.sh` y el
  script `scripts/create-influx-tokens.sh` deja un fichero por token en el volumen
  `mcp-secrets`: uno con **solo lectura** de los buckets de los dashboards
  (`GRAFANA_READ_BUCKETS`), y otros de **solo escritura** para Node-RED
  (`NODERED_WRITE_BUCKETS`) y el loader (`LOADER_WRITE_BUCKETS`).
- Si cambia la lista de buckets, regenera los tokens con los permisos actualizados
  y borra los obsoletos.

Los servicios leen sus tokens de esos ficheros: Grafana lo aprovisiona con
`$__file{...}` al arrancar, Node-RED lo exporta su entrypoint (`services/nodered/
aeroadd-entrypoint.sh`) y el loader lo lee en Python (`INFLUXDB_TOKEN_FILE`).
No hace falta pegar nada en `LOADER_INFLUXDB_TOKEN` ni en variables similares.

Ojo: `down -v` borra los datos y el volumen de secretos, pero **no hay que hacer
nada**: en el siguiente `up` todo se re-crea (tokens incluidos). Único caso
manual: si rellenas el fallback `LOADER_INFLUXDB_TOKEN` a mano, bórralo tras un
`down -v` (quedaría inválido y el script automático lo respetaría).

## Cómo lanzarlo

```bash
docker compose config   # valida el compose (funciona con y sin .env, usa valores de ejemplo por defecto)
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose down     # detiene la pila
```

Nota: el `loader` carga el histórico de captaciones (CSV de `BDA/ImporCsvPandas`,
montado en `/data`) en el bucket `captaciones_julio` y escribe un heartbeat.
Toda la pila arranca con valores de ejemplo.

### Carga histórica (CSV de junio → InfluxDB)

Se hace sola al levantar: el `loader` es un servicio one-shot que lee
`BDA/ImporCsvPandas/captaciones_junio_2026.csv` (~461K filas), lo limpia igual que el
notebook del equipo y lo sube al bucket `captaciones_julio` en lotes. Tarda unos
minutos; al terminar sale del contenedor con código 0.

Para repetirla sin re-crear la pila:

```bash
docker compose run --rm loader   # re-escribe los mismos puntos (idempotente)
```

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
./scripts/setup-env.sh                 # crea .env con todas las credenciales, si aún no existe
docker compose up -d influxdb influx-tokens-init
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

Los writes a InfluxDB se hacen por HTTP (line protocol) con el token de escritura que el entrypoint exporta desde el volumen `mcp-secrets`. Si un flow falla por credenciales, el error sale en `docker compose logs nodered`.

### Consultar InfluxDB a mano

```bash
set -a && source .env && set +a
docker exec aeroadd-influxdb influx bucket list --token "$INFLUXDB_ADMIN_TOKEN" --org "$INFLUXDB_INIT_ORG"
docker exec aeroadd-influxdb influx query --token "$INFLUXDB_ADMIN_TOKEN" --org "$INFLUXDB_INIT_ORG" \
  'from(bucket:"captaciones_tiemporeal") |> range(start:-1h) |> limit(n:5)'
```

## Resolución de problemas

- **InfluxDB en bucle `unhealthy` (`failed to exec ... 01-create-buckets.sh: No such file or directory`)**: el script tiene finales CRLF; el kernel del contenedor no encuentra el intérprete `/bin/bash\r`. Pasar a LF (`sed -i 's/\r$//'`) y levantar de cero: `docker compose down -v && docker compose up -d`.
- **`401 Unauthorized` en Grafana o Node-RED**: no debería pasar salvo que borres el volumen `mcp-secrets` sin recrear los init. Los tokens se regeneran solos en el siguiente `docker compose up -d`; si el problema persiste, `docker compose down -v && docker compose up -d --build` (re-carga el histórico incluido).
- **NoData con datos existentes**: casi siempre es el rango de tiempo del dashboard (ver tabla de arriba) o el filtro de variable (`tipo_tienda`).
- **`type conflict: float != int` en un panel Flux**: algún campo entero se compara con un literal decimal (`== 1.0`) o se mezcla con floats en un `if/else`. Envolver el campo con `float(v: ...)` en la query del panel.

## MCP de Grafana (una instancia por rol)

El MCP oficial `grafana/mcp-grafana` se levanta en **tres instancias**, una por rol.
Cada una se autentica con su propia **service account** de Grafana, de modo que el
agente hereda los permisos de ese rol y no puede suplantar a otro.

Las service accounts y sus tokens se crean solas al levantar la pila: el servicio
efímero `grafana-sa-init` ejecuta `scripts/create-grafana-sa.sh` (idempotente) y deja
un fichero de token por rol en el volumen `mcp-secrets`. En `.env` solo hay que
poner el usuario/contraseña admin de Grafana y los **tokens de llamante** por rol
(no se generan solos: son la credencial con la que el cliente habla con cada MCP;
`scripts/setup-env.sh` los genera automáticamente si están vacíos o como
`CHANGEME`).

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
