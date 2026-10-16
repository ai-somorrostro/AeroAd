# mcp-grafana Specification

## Purpose
Exponer las consultas de solo lectura sobre InfluxDB 2.x (Flux) y los metadatos de
Grafana a un cliente MCP orientado al usuario, con una instancia por rol que hereda
los permisos de su service account de Grafana, aprovisionado de forma reproducible
con `docker compose up`.

## Requirements

### Requirement: Una instancia MCP por rol con la imagen oficial

El sistema SHALL ejecutar el servidor MCP como tres servicios (`mcp-direccion`,
`mcp-analisis`, `mcp-it`) usando la imagen oficial `grafana/mcp-grafana` con versión
fijada, en transporte `streamable-http` en puertos distintos, sin build propio.

#### Scenario: Arranque de la pila

- **WHEN** se ejecuta `docker compose up -d --build` con `.env` relleno
- **THEN** los tres contenedores arrancan y cada `/healthz` responde 200

#### Scenario: Sin stub propio

- **WHEN** se lista `services/mcp/`
- **THEN** el directorio no existe (Dockerfile, requirements y `src/` eliminados)

### Requirement: Herencia de permisos por rol

El sistema SHALL autenticar cada instancia MCP con la service account de su rol, de
modo que el agente solo pueda ver y hacer lo que ese rol permite en Grafana, sin
poder suplantar a otro rol.

#### Scenario: Rol sin permiso no escala

- **WHEN** un cliente del rol "análisis" pide por prompt un dashboard o una acción
  fuera de su rol
- **THEN** la operación se rechaza o no devuelve resultados, porque la instancia usa
  el token de su propia service account y no el de otro rol

#### Scenario: Instancia con su propio token

- **WHEN** se inspeccionan los tres servicios MCP
- **THEN** cada uno referencia un `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE` distinto
  (`sa-direccion-token`, `sa-analisis-token`, `sa-it-token`) y un token de llamante
  distinto, en un puerto host distinto (8000/8001/8002)

### Requirement: Orden de arranque vía Grafana

Los servicios MCP SHALL depender de `grafana` en estado healthy y del init de las
service accounts, y NO de `influxdb` directamente (el MCP accede a InfluxDB a través
del datasource de Grafana).

#### Scenario: Dependencias del servicio

- **WHEN** se inspecciona la definición de cada servicio MCP
- **THEN** su `depends_on` incluye `grafana` con condición `service_healthy` y
  `grafana-sa-init` con `service_completed_successfully`, y no incluye `influxdb`

### Requirement: Aprovisionamiento automático de las service accounts

El sistema SHALL crear de forma idempotente las service accounts de Grafana
(`sa-direccion`, `sa-analisis`, `sa-it`) con su rol y un token por cada una, mediante
un servicio efímero de init y un script en `scripts/`, de modo que
`docker compose up` baste sin pasos manuales en la UI.

#### Scenario: Primer arranque limpio

- **WHEN** se levanta la pila sin tokens previos y con credenciales admin de Grafana
  en `.env`
- **THEN** existen las tres service accounts y cada token queda disponible para su
  instancia MCP (un fichero por rol en el volumen compartido)

#### Scenario: Idempotencia

- **WHEN** se vuelve a levantar la pila con los tokens ya generados
- **THEN** no se crean service accounts ni tokens nuevos y los existentes siguen
  siendo válidos

### Requirement: Rol inicial de solo lectura

El sistema SHALL crear las tres service accounts con rol **Viewer** mientras el RBAC
de Grafana no esté disponible; el reparto fino de permisos (carpetas por rol y rol de
edición de IT) SHALL depender del RBAC que monte el equipo de Grafana.

#### Scenario: Cuentas en solo lectura

- **WHEN** se crean las service accounts en el arranque inicial
- **THEN** las tres tienen rol Viewer y ninguna puede escribir

### Requirement: Secretos fuera del repo

El sistema SHALL leer `GRAFANA_URL`, los tokens de las service accounts (uno por
rol), los tokens de llamante por rol y las credenciales admin de Grafana desde
`.env`, con placeholders sin valores reales en `.env.example`; el archivo `.env`
nunca se commitea.

#### Scenario: Sin secretos en git

- **WHEN** se revisa el contenido versionado
- **THEN** ningún fichero contiene tokens, contraseñas ni URLs con credenciales
  reales

### Requirement: Mínimo privilegio en herramientas

El sistema SHALL exponer solo consultas InfluxDB más `datasources` y dashboards en
lectura; las escrituras, las alertas y las consultas de panel SHALL estar
deshabilitadas en las tres instancias.

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
sección `mcp`) con una entrada por instancia/rol, solo para desarrollo y pruebas;
opencode NO es el consumidor final.

#### Scenario: Herramientas visibles en desarrollo

- **WHEN** opencode conecta a una instancia MCP con su token de llamante
- **THEN** la lista de herramientas incluye la de consulta InfluxDB y no incluye
  herramientas de escritura ni de alertas

### Requirement: Documentación de conexión por rol y limitaciones

El sistema SHALL documentar en `README.md` cómo conectar un cliente MCP a cada rol
(URL, puerto y token de cada uno) y las limitaciones conocidas, incluido que el
agente puede equivocarse con las consultas Flux.

#### Scenario: Sección de conexión

- **WHEN** se lee el `README.md`
- **THEN** incluye una sección con URL, puerto y token de cada rol, y una sección de
  limitaciones
