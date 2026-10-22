# mcp-grafana Specification

## Purpose
Exponer las consultas de solo lectura sobre InfluxDB 2.x (Flux) y los metadatos de
Grafana a un cliente MCP orientado al usuario, mediante **una única instancia** que
hereda los permisos de una service account compartida de Grafana, aprovisionada de
forma reproducible con `docker compose up`.

## Requirements

### Requirement: Una única instancia MCP con la imagen oficial

El sistema SHALL ejecutar el servidor MCP como un único servicio (`mcp-grafana`)
usando la imagen oficial `grafana/mcp-grafana` con versión fijada, en transporte
`streamable-http` en el puerto `8000`, sin build propio. Los antiguos servicios
`mcp-direccion`, `mcp-analisis` y `mcp-it` NO SHALL existir.

#### Scenario: Arranque de la pila

- **WHEN** se ejecuta `docker compose up -d --build` con `.env` relleno
- **THEN** el contenedor `mcp-grafana` arranca y `/healthz` responde 200

#### Scenario: Sin instancias por rol

- **WHEN** se inspecciona `docker-compose.yml`
- **THEN** solo hay un servicio MCP y no se publican los puertos 8001 ni 8002

#### Scenario: Sin stub propio

- **WHEN** se lista `services/mcp/`
- **THEN** el directorio no existe (Dockerfile, requirements y `src/` eliminados)

### Requirement: Service account compartida

El sistema SHALL autenticar la instancia MCP con una única service account de
Grafana, de modo que todos los clientes que presenten el token de llamante compartido
tengan exactamente los mismos permisos. No hay herencia de permisos por rol ni
separación entre perfiles.

#### Scenario: Un solo token de Grafana

- **WHEN** se inspecciona el servicio `mcp-grafana`
- **THEN** referencia un único `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE`
  (`/shared/sa-mcp-token`) y un único `MCP_GRAFANA_SERVER_TOKEN`

#### Scenario: Permisos homogéneos

- **WHEN** dos clientes distintos se conectan con el mismo token de llamante
- **THEN** ambos ven los mismos dashboards y pueden ejecutar las mismas consultas,
  porque comparten la service account

### Requirement: Orden de arranque vía Grafana

El servicio MCP SHALL depender de `grafana` en estado healthy y del init de la
service account, y NO de `influxdb` directamente (el MCP accede a InfluxDB a través
del datasource de Grafana).

#### Scenario: Dependencias del servicio

- **WHEN** se inspecciona la definición de `mcp-grafana`
- **THEN** su `depends_on` incluye `grafana` con condición `service_healthy` y
  `grafana-sa-init` con `service_completed_successfully`, y no incluye `influxdb`

### Requirement: Aprovisionamiento automático de la service account

El sistema SHALL crear de forma idempotente una service account de Grafana
(`sa-mcp`) con su rol y un token, mediante un servicio efímero de init y un script en
`scripts/`, de modo que `docker compose up` baste sin pasos manuales en la UI.

#### Scenario: Primer arranque limpio

- **WHEN** se levanta la pila sin tokens previos y con credenciales admin de Grafana
  en `.env`
- **THEN** existe la service account `sa-mcp` y su token queda disponible en
  `/shared/sa-mcp-token` del volumen compartido

#### Scenario: Idempotencia

- **WHEN** se vuelve a levantar la pila con el token ya generado
- **THEN** no se crea una service account ni un token nuevos y el existente sigue
  siendo válido

#### Scenario: Limpieza del esquema antiguo

- **WHEN** el volumen `mcp-secrets` contiene ficheros de token de las tres instancias
  anteriores (`sa-direccion-token`, `sa-analisis-token`, `sa-it-token`)
- **THEN** el init los elimina y conserva únicamente el token de service account
  `sa-mcp` (los tokens de InfluxDB no se tocan)

### Requirement: Rol inicial de solo lectura

El sistema SHALL crear la service account con rol **Viewer** mientras el RBAC de
Grafana no esté disponible; el reparto fino de permisos (carpetas por rol y rol de
edición de IT) SHALL depender del RBAC que monte el equipo de Grafana y, si se
necesita, de volver a separar instancias o añadir un proxy autenticador.

#### Scenario: Cuenta en solo lectura

- **WHEN** se crea la service account en el arranque inicial
- **THEN** tiene rol Viewer y no puede escribir

### Requirement: Secretos fuera del repo

El sistema SHALL leer `GRAFANA_URL`, el token de la service account, el token de
llamante compartido y las credenciales admin de Grafana desde `.env`, con
placeholders sin valores reales en `.env.example`; el archivo `.env` nunca se
commitea.

#### Scenario: Sin secretos en git

- **WHEN** se revisa el contenido versionado
- **THEN** ningún fichero contiene tokens, contraseñas ni URLs con credenciales
  reales

### Requirement: Mínimo privilegio en herramientas

El sistema SHALL exponer solo consultas InfluxDB más `datasources` y dashboards en
lectura; las escrituras, las alertas y las consultas de panel SHALL estar
deshabilitadas en la instancia MCP.

#### Scenario: Consulta Flux permitida

- **WHEN** un cliente MCP autenticado pide una consulta Flux contra el datasource
  InfluxDB
- **THEN** el servidor la ejecuta y devuelve las filas

#### Scenario: Escritura rechazada

- **WHEN** un cliente MCP intenta crear o modificar un dashboard
- **THEN** la herramienta no está registrada o la operación es rechazada

### Requirement: Datasource InfluxDB con UID estable

El datasource InfluxDB provisionado en Grafana SHALL tener un UID explícito y fijado
para referenciarlo de forma estable desde el MCP y los scopes RBAC.

#### Scenario: UID presente

- **WHEN** se lee `services/grafana/provisioning/datasources/influxdb.yml`
- **THEN** contiene un campo `uid` con valor no vacío

### Requirement: Cliente de desarrollo (opencode)

El sistema SHALL declarar el MCP en la configuración de opencode (`opencode.json`,
sección `mcp`) con una única entrada `grafana`, solo para desarrollo y pruebas;
opencode NO es el consumidor final.

#### Scenario: Herramientas visibles en desarrollo

- **WHEN** opencode conecta a `mcp-grafana` con el token de llamante compartido
- **THEN** la lista de herramientas incluye la de consulta InfluxDB y no incluye
  herramientas de escritura ni de alertas

### Requirement: Documentación de conexión única y limitaciones

El sistema SHALL documentar en `README.md` cómo conectar un cliente MCP a la
instancia única (URL, puerto y token) y las limitaciones conocidas, incluido que el
agente puede equivocarse con las consultas Flux y que todos los clientes comparten
los permisos de la service account.

#### Scenario: Sección de conexión

- **WHEN** se lee el `README.md`
- **THEN** incluye una sección con URL, puerto y token de la instancia única, la
  migración desde las tres instancias y una sección de limitaciones
