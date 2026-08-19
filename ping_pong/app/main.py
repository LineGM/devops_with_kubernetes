"""HTTP server with a file-backed ping-pong request counter."""

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_PORT = 3000
DEFAULT_COUNTER_FILE = "/usr/src/app/files/ping-pong.txt"


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


class PingPongRequestHandler(BaseHTTPRequestHandler):
    """Respond to /pingpong and persist the successful request count."""

    counter_file = Path(DEFAULT_COUNTER_FILE)
    counter_lock = threading.Lock()

    @classmethod
    def next_response(cls) -> bytes:
        """Return the current counter and increment it atomically."""
        with cls.counter_lock:
            try:
                value = int(cls.counter_file.read_text(encoding="utf-8").strip())
            except (FileNotFoundError, ValueError):
                value = 0

            temporary_file = cls.counter_file.with_name(f".{cls.counter_file.name}.tmp")
            temporary_file.write_text(f"{value + 1}\n", encoding="utf-8")
            temporary_file.replace(cls.counter_file)
        return f"pong {value}\n".encode()

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/pingpong":
            self.send_error(404, "Not Found")
            return

        body = self.next_response()
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
    PingPongRequestHandler.counter_file = Path(
        os.getenv("COUNTER_FILE", DEFAULT_COUNTER_FILE)
    )
    PingPongRequestHandler.counter_file.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", port), PingPongRequestHandler)
    print(f"Server started in port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
