"""A minimal HTTP server for the course todo application."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEFAULT_PORT = 3000


def configured_port() -> int:
    """Read and validate the listening port from the environment."""
    raw_port = os.getenv("PORT", str(DEFAULT_PORT))

    try:
        port = int(raw_port)
    except ValueError as error:
        raise SystemExit(f"PORT must be an integer, got {raw_port!r}") from error

    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535")

    return port


class TodoRequestHandler(BaseHTTPRequestHandler):
    """Serve a placeholder page until the todo UI is implemented."""

    def do_GET(self) -> None:
        body = b"Todo app\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Write request logs to stdout so Kubernetes can collect them."""
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> None:
    port = configured_port()
    server = ThreadingHTTPServer(("0.0.0.0", port), TodoRequestHandler)
    print(f"Server started in port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
