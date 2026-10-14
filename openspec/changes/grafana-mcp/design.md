# Design

## Context

Ver `proposal.md` (Why) y `specs/mcp-grafana/spec.md` (requisitos).

**Consumidor**: el cliente del reto tiene tres roles con permisos distintos en
Grafana. El consumidor final es un **cliente MCP orientado al usuario** (el que use
el cliente), repartido por rol. **OpenCode se usa solo para desarrollo y pruebas** de
la integración; no es el consumidor final.

Estado actual: `mcp` es un build propio (`services/mcp/`: stub Python stdlib con
`GET /health` en `:8000`, sin dependencias); Grafana 11.2.0 con datasource InfluxDB
Flux provisionado pero sin `uid`; el token de lectura de InfluxDB ya se genera con
`scripts/create-tokens.sh`. Referencia oficial consultada: `grafana/mcp-grafana`
(v2.x, versión a fijar `v2.0.2`; imagen final `debian:bookworm-slim` +
`ca-certificates`, sin wget/curl, usuario no-root uid 1000, entrypoint por defecto SSE
en `0.0.0.0:8000`).

## Goals / Non-Goals

**Goals:**

- Sustituir el stub por el servidor oficial sin pasos manuales en la UI
  (`docker compose up` basta).
- Que cada rol herede exactamente los permisos de su service account de Grafana.
- Consultas Flux de solo lectura contra InfluxDB 2.x vía datasource de Grafana.
- Secretos solo en `.env` / volumen efímero, nunca en el repo.

**Non-Goals:**

- Implementar el RBAC fino de Grafana (dashboards por carpeta, roles de edición):
  depende del equipo de Grafana (dependencia externa).
- Dashboards de ejemplo, alertas y consultas de panel (deshabilitados).
- Escritura en InfluxDB o Grafana desde el MCP.
- Rotación automática de tokens (el `_FILE` la admite sin reinicio; queda para
  futuro).

## Decisions

### Una instancia MCP por rol (no un servidor que cambia de token por petición)

El README oficial documenta credenciales por petición en `streamable-http` vía
`X-Grafana-Service-Account-Token`, pero **solo junto con la selección de URL**
(`X-Grafana-URL`), deshabilitada por defecto y que exige `--allow-grafana-url-override`
+ allowlist. Ese mecanismo está pensado para un proxy autenticador y el propio README
advierte que "no autentica a los llamantes ni vincula tokens a destinos": un cliente
podría enviar el token de otro rol y suplantarlo. No sirve para que el agente herede
permisos de forma segura, así que se levantan **tres instancias** del mismo servidor:

| Servicio | Rol | Puerto host | Service account | Fichero de token | Token de llamante |
|---|---|---|---|---|---|
| `mcp-direccion` | cúpula directiva | `${MCP_DIRECCION_PORT:-8000}` | `sa-direccion` | `/shared/sa-direccion-token` | `MCP_GRAFANA_SERVER_TOKEN_DIRECCION` |
| `mcp-analisis` | análisis | `${MCP_ANALISIS_PORT:-8001}` | `sa-analisis` | `/shared/sa-analisis-token` | `MCP_GRAFANA_SERVER_TOKEN_ANALISIS` |
| `mcp-it` | IT | `${MCP_IT_PORT:-8002}` | `sa-it` | `/shared/sa-it-token` | `MCP_GRAFANA_SERVER_TOKEN_IT` |

Puertos por defecto confirmados: 8000 (dirección), 8001 (análisis), 8002 (IT);
configurables por variable. Comprobado que ningún otro servicio del compose ocupa
esos puertos en el host (`influxdb` 8086, `grafana` 3000, `nodered` 1880; `loader` y
`grafana-sa-init` no publican puertos).

Cada instancia fija `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE` a su fichero del volumen
compartido y su propio `MCP_GRAFANA_SERVER_TOKEN` como auth de llamante. El rol del
agente queda determinado por la instancia (y por el token que el cliente recibe para
su rol), no por lo que decida el LLM.

### Transporte `streamable-http` + token de llamante

El consumidor es un cliente MCP por HTTP, así que cada servicio sobreescribe el
entrypoint SSE con `-t streamable-http --address 0.0.0.0:8000` y exige
`Authorization: Bearer` vía su `MCP_GRAFANA_SERVER_TOKEN`. Sin ese token el servidor
arranca pero loguea error de seguridad. `stdio` se descarta: en compose es incómodo
(requiere stdin abierto) y no sirve a un consumidor HTTP.

### Token de cada service account por volumen compartido (opción A)

Servicio efímero `grafana-sa-init` (imagen `curlimages/curl` fijada + script
`scripts/create-grafana-sa.sh` montado `:ro`) que, esperando a Grafana healthy y con
`GRAFANA_ADMIN_*` de `.env`, crea las **tres service accounts** (`sa-direccion`,
`sa-analisis`, `sa-it`, rol Viewer) y sus tokens vía API, y los escribe en el volumen
con nombre `mcp-secrets` (un fichero por rol: `/shared/sa-direccion-token`,
`/shared/sa-analisis-token`, `/shared/sa-it-token`; `chmod 444` porque el MCP corre
como uid 1000 y el init como root). El `_FILE` se relee por request, así que rota sin
reinicio. Orden: cada MCP tiene
`depends_on = {grafana: healthy, sa-init: completed}`.
Descartados: `secrets:` de compose (exige el fichero antes del `up`; el token nace
durante el `up`) y bind a `./secrets/` en host (deja secretos en disco y hay que
gitignorarlo).

### Rol inicial Viewer y dependencia externa del RBAC

Las tres cuentas nacen con rol **Viewer** (solo lectura): cubre la consulta Flux y la
lectura de dashboards/datasources. El reparto fino (carpetas por rol, IT con edición)
se hará cuando el equipo tenga montado el RBAC de Grafana; hasta entonces IT también
es Viewer y **el rol de edición de IT se decide con ese RBAC**. Queda anotado como
dependencia externa, no como tarea de este change.

### Flags de herramientas

`--enabled-tools influxdb --disable-write --enable-query --disable-alerting`:
activa `query_influxdb`, quita escrituras, repesca la query (que `--disable-write`
quitaría) y apaga alertas. `runpanelquery` ya viene off por defecto. Quedan:
`query_influxdb`, datasources (list/get/health), dashboards en lectura, `user_info`,
deeplinks. Se aplica igual en las tres instancias.

### Healthcheck sin cliente HTTP

La imagen no trae wget/curl; `bash` sí existe en bookworm-slim:
`["CMD", "bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/8000 && printf
'GET /healthz HTTP/1.0\r\n\r\n' >&3 && head -c 12 <&3 | grep -q 200"]`.
Fallback: sin healthcheck (depends_on + restart bastan).

### UID explícito del datasource + higiene

Añadir `uid:` fijado en `influxdb.yml` (referencia estable para llamadas y scopes). A
la vez: `.gitignore` += `__pycache__/`, `*.pyc` (hay un `.pyc` huérfano en
`services/mcp/src/` que se va con el directorio) y `AGENTS.md`: `master` en vez de
`main`.

## Risks / Trade-offs

- [RBAC de Grafana no listo] → Mitigación: las tres cuentas son Viewer; el afinado
  llega con el RBAC del equipo (dependencia externa). Documentado en README.
- [Tres instancias = tres puertos y tres tokens] → Coste aceptado a cambio de una
  herencia de permisos clara y sin suplantación; se documenta la tabla de conexión.
- [El `_FILE` falta en el primer arranque] → Mitigación: orden por
  `depends_on: sa-init completed`; el servidor resuelve el fichero por request.
- [`down -v` borra `mcp-secrets`] → Mitigación: documentado; el init lo regenera en
  el siguiente `up` (idempotente, reutiliza si sigue válido).
- [Conflicto con `feature/compose-grafana` en `influxdb.yml`] → Mitigación: cambio de
  una línea; al fusionar gana el `uid` fijado aquí.
- [Tag Docker] → Mitigación: fijar `v2.0.2` (nunca `latest`) y confirmar que existe
  en el registro antes de implementar.

## Migration Plan

1. `up -d --build` con `.env` relleno (incluye los tres tokens de llamante generados a
   mano); el init crea las tres SAs y sus tokens.
2. Verificar `/healthz` en los tres puertos, herramientas listadas y una query Flux de
   prueba por instancia.
3. Rollback: revertir el change; el stub no se restaura (era esqueleto sin
   consumidores).

## Open Questions

- Tag exacto de la imagen a fijar (por defecto `v2.0.2`): confirmar disponibilidad en
  el registro al implementar.

Puertos y volumen ya confirmados: `mcp-direccion`:8000, `mcp-analisis`:8001,
`mcp-it`:8002 (variables `MCP_DIRECCION_PORT`/`MCP_ANALISIS_PORT`/`MCP_IT_PORT`,
con esos valores por defecto) y volumen `mcp-secrets` con `sa-direccion-token`,
`sa-analisis-token`, `sa-it-token`.
