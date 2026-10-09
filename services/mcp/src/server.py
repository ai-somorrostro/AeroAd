"""MCP AeroAdd (esqueleto listo para deploy).

HTTP mínimo con stdlib para que el servicio `mcp` arranque, responda en
el puerto 8000 y tenga healthcheck. Expone:
  GET /health -> {"status": "ok", "service": "mcp"}
  GET /       -> info del esqueleto (sin secretos).
El MCP real sobre InfluxDB lo implementarán los compañeros aquí mismo.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - firma de http.server
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "mcp"})
        elif self.path == "/":
            self._send_json(
                {
                    "service": "aeroadd-mcp",
                    "status": "skeleton",
                    "influxdb_url": os.getenv(
                        "INFLUXDB_URL", "http://influxdb:8086"
                    ),
                    "endpoints": ["/health"],
                }
            )
        else:
            self._send_json({"error": "not found"}, status=404)

    def log_message(self, *args: object) -> None:  # noqa: ANN002, ANN003
        # Log con flush inmediato para `docker compose logs`.
        print(f"[mcp] {' '.join(str(a) for a in args)}", flush=True)


def main() -> None:
    port = int(os.getenv("MCP_PORT", os.getenv("PORT", "8000")))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[mcp] Escuchando en 0.0.0.0:{port} (esqueleto).", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
