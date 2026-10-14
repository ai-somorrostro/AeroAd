# Tasks

## 1. Servicios MCP por rol + init de las service accounts

- [x] 1.1 Reescribir el servicio `mcp` de `docker-compose.yml` como **tres servicios** (`mcp-direccion`, `mcp-analisis`, `mcp-it`): `image: grafana/mcp-grafana:2.0.2` (nunca `latest`), comando `-t streamable-http --address 0.0.0.0:8000`, `GRAFANA_URL`, su `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE` (`/shared/sa-direccion-token`, `/shared/sa-analisis-token`, `/shared/sa-it-token`) y su `MCP_GRAFANA_SERVER_TOKEN_*`; puertos host configurables `MCP_DIRECCION_PORT`/`MCP_ANALISIS_PORT`/`MCP_IT_PORT` (por defecto 8000/8001/8002); flags `--enabled-tools influxdb --disable-write --enable-query --disable-alerting`; `depends_on: {grafana: healthy, sa-init: completed}`; healthcheck bash/`/dev/tcp` contra `/healthz`; verificar con `docker compose config` y que ningún otro servicio choca en esos puertos
- [x] 1.2 Ampliar `scripts/create-grafana-sa.sh` para crear de forma idempotente las **tres** service accounts (`sa-direccion`, `sa-analisis`, `sa-it`, rol Viewer) y sus tokens vía API, reutilizar los válidos y escribir un fichero por rol en el volumen compartido con `chmod 444` sin imprimir valores; verificar con `sh -n` y `docker compose config`
- [x] 1.3 Definir/ajustar el servicio efímero `grafana-sa-init` en compose con el volumen `mcp-secrets` (imagen `curlimages/curl` fijada, script montado `:ro`); verificar con `docker compose config`
- [x] 1.4 Eliminar `services/mcp/` (incluido el `.pyc` huérfano) y ampliar `.env.example` con `GRAFANA_URL`, nombres de las SAs, tokens de llamante por rol, puertos (`MCP_DIRECCION_PORT`/`MCP_ANALISIS_PORT`/`MCP_IT_PORT` con 8000/8001/8002) y ruta del `_FILE` como placeholders; verificar que `git status` no muestra restos del stub y que no hay valores reales

## 2. Datasource con UID + higiene del repo

- [x] 2.1 Fijar `uid:` explícito en `services/grafana/provisioning/datasources/influxdb.yml` y verificar el YAML con `python3 -c "yaml.safe_load(...)"` (nota: posible conflicto con `feature/compose-grafana` al fusionar)
- [x] 2.2 Añadir `__pycache__/` y `*.pyc` al `.gitignore` y corregir `AGENTS.md` (`master` en vez de `main`); verificar con `git check-ignore` sobre un path `__pycache__` de ejemplo

## 3. Cliente de desarrollo (opencode)

- [ ] 3.1 Configurar `opencode.json` (sección `mcp`) con una entrada por instancia/rol apuntando por HTTP a su puerto y su token de llamante, solo para desarrollo y pruebas; verificar que opencode lista la tool de consulta InfluxDB y excluye escritura y alertas

## 4. Documentación y verificación extremo a extremo

- [x] 4.1 Añadir al `README.md` la sección de **conexión de un cliente MCP por rol** (URL, puerto y token de cada uno) y la de **limitaciones** (el agente puede equivocarse con las consultas Flux); actualizar el árbol/tabla de servicios; verificar el render de las secciones añadidas
- [ ] 4.2 Levantar la pila (`up -d`), verificar `/healthz` en los tres puertos, ejecutar una consulta Flux por instancia e informar qué funciona y qué no; verificar que ningún token puede escribir y que un rol no accede a recursos fuera de su rol

## Dependencias externas

- RBAC fino de Grafana (carpetas por rol y rol de edición de IT): lo monta el equipo de Grafana. Hasta entonces las tres cuentas son Viewer.
