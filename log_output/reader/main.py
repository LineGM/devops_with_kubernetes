"""Serve the contents of the shared Log output file over HTTP."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_PORT = 3000
DEFAULT_LOG_FILE = "/usr/src/app/files/log.txt"


def configured_port() -> int:
    """Read and validate the HTTP port from the environment."""
    raw_port = os.getenv("PORT", str(DEFAULT_PORT))

    try:
        port = int(raw_port)
    except ValueError as error:
        raise SystemExit(f"PORT must be an integer, got {raw_port!r}") from error

    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535")

    return port


class LogRequestHandler(BaseHTTPRequestHandler):
    """Return the contents of the file written by the companion container."""

    log_file = Path(DEFAULT_LOG_FILE)

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/":
            self.send_error(404, "Not Found")
            return

        try:
            body = self.log_file.read_bytes()
        except FileNotFoundError:
            body = b"Log output is not available yet.\n"

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
    LogRequestHandler.log_file = Path(os.getenv("LOG_FILE", DEFAULT_LOG_FILE))
    server = ThreadingHTTPServer(("0.0.0.0", port), LogRequestHandler)
    print(f"Server started in port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
