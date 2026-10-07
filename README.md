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
│   ├── influxdb/           # scripts de init (buckets, tokens)
│   ├── grafana/
│   │   └── provisioning/   # datasources, dashboards, usuarios/orgs
│   ├── nodered/
│   │   ├── Dockerfile
│   │   ├── settings.js
│   │   └── flows.json
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
└── scripts/                # up.sh, down.sh, reset.sh
```

## Requisitos previos

- Docker
- Docker Compose
- Git

## Cómo lanzarlo

TODO: se completará cuando exista el compose.

## Autores

TODO
