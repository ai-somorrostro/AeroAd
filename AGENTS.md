# AGENTS.md

Reglas para agentes trabajando en este repositorio:

- Respetar la estructura de carpetas existente; no crear carpetas nuevas sin que se pida.
- Nunca commitear secretos ni archivos `.env`; toda configuración va por variables de entorno y se documenta en `.env.example`.
- Commits atómicos con Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Nunca hacer push a `main` ni a `develop`; trabajar siempre en ramas `feature/*`.
- No dejar archivos temporales, binarios ni artefactos generados.
- Mantener los cambios al mínimo necesario para la tarea pedida.
