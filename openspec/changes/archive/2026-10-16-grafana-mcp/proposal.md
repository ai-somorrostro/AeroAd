# Proposal

## Why

El servicio `mcp` actual es un stub HTTP en Python con stdlib que no expone ninguna
capacidad real sobre los datos. La imagen oficial `grafana/mcp-grafana` ya ofrece un
servidor MCP con herramienta de consulta InfluxDB (Flux) que se autentica a través
del datasource provisionado en Grafana, eliminando código propio que mantener.

El cliente del reto tiene tres perfiles con permisos distintos en Grafana:

- **Cúpula directiva**: ve todos los dashboards, sin editar.
- **Análisis**: ve solo algunos dashboards, sin editar.
- **IT**: ve y edita todo.

El agente MCP debe **heredar los permisos del rol** con el que se invoca: un usuario
de "análisis" no debe poder ver ni tocar lo que no le corresponde aunque lo pida por
prompt. Por eso cada rol se sirve desde una instancia MCP autenticada con su propia
service account de Grafana.

## What Changes

- Se sustituye el stub por la imagen oficial `grafana/mcp-grafana` (versión fijada,
  nunca `latest`) en transporte `streamable-http`, sin build propio.
- Se levantan **tres instancias** del mismo servidor, una por rol (`mcp-direccion`,
  `mcp-analisis`, `mcp-it`), en puertos distintos; cada una usa su propia service
  account y su propio token de llamante. Se descarta una única instancia con cambio
  de token por petición (ver `design.md`).
- Nuevo servicio efímero de init en compose + script idempotente en `scripts/` que
  crea **tres service accounts** (`sa-direccion`, `sa-analisis`, `sa-it`) y un token
  por cada una vía API de Grafana.
- Los tokens viajan al MCP por el volumen compartido `mcp-secrets`, con un fichero
  por rol vía `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE`; `GRAFANA_URL`, las credenciales
  admin y los tokens de llamante por `.env` (placeholders en `.env.example`, sin
  valores reales en el repo).
- Estado inicial: las tres service accounts con rol **Viewer** (solo lectura). El
  ajuste fino por carpeta y RBAC queda como **dependencia externa** del equipo de
  Grafana.
- `depends_on` de cada MCP pasa a `grafana` (healthy) y al init; se quita la
  dependencia directa de `influxdb` (el MCP habla con InfluxDB vía Grafana).
- Tools mínimas: `influxdb`, `datasources` y dashboards en lectura;
  `--disable-write`, `--enable-query`, `--disable-alerting`; `runpanelquery` queda
  desactivado.
- Se elimina `services/mcp/` (Dockerfile, requirements, `src/`).
- Healthcheck de cada instancia contra `/healthz`.
- UID explícito en el datasource InfluxDB provisionado (**posible conflicto con
  `feature/compose-grafana`** si toca el mismo fichero).
- OpenCode se configura para desarrollo y pruebas; **no** es el consumidor final.
- `README.md`: sección de conexión por rol (URL, puerto y token de cada uno) y
  sección de limitaciones (el agente puede equivocarse con las consultas Flux).
- `.gitignore`: `__pycache__/` y `*.pyc`.
- `AGENTS.md`: la rama principal es `master`, no `main`.

## Capabilities

### New Capabilities

- `mcp-grafana`: servidor MCP oficial de Grafana como servicio de la pila, con una
  instancia por rol que hereda los permisos de su service account (consulta Flux de
  solo lectura contra InfluxDB 2.x vía datasource, con aprovisionamiento automático
  de las service accounts y sus tokens).

### Modified Capabilities

- (vacío: no hay specs previas que modificar)

## Impact

- Afecta a `docker-compose.yml` (tres servicios MCP + init efímero, volumen
  compartido), `services/mcp/` (eliminado), `scripts/` (script ampliado a tres
  cuentas), `.env.example`, `.gitignore`, `AGENTS.md`, `opencode.json`, `README.md`.
- Requiere Grafana >= 9.0 (usamos 11.2.0) y regenerar los tokens si se recrea el
  volumen compartido con `down -v`.
- Depende del RBAC de Grafana que monta el equipo: hasta entonces las tres cuentas
  son Viewer y el rol de edición de IT no está afinado.
- **BREAKING**: desaparece el endpoint `/health` del stub en `:8000`; los puertos
  `:8000`/`:8001`/`:8002` pasan a exponer el protocolo MCP por HTTP. Cualquier
  consumidor del stub debe migrar.
