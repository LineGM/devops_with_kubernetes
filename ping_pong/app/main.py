"""HTTP server exposing Ping-pong responses and its in-memory counter."""

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


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


class PingPongRequestHandler(BaseHTTPRequestHandler):
    """Respond to /pingpong and expose the counter at /pings."""

    counter = 0
    counter_lock = threading.Lock()

    @classmethod
    def next_response(cls) -> bytes:
        """Return the current counter and increment it atomically."""
        with cls.counter_lock:
            value = cls.counter
            cls.counter += 1
        return f"pong {value}\n".encode()

    @classmethod
    def current_count(cls) -> bytes:
        """Return the counter without incrementing it."""
        with cls.counter_lock:
            value = cls.counter
        return f"{value}\n".encode()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path

        if path == "/pingpong":
            self.send_text(self.next_response())
            return

        if path == "/pings":
            self.send_text(self.current_count())
            return

        self.send_error(404, "Not Found")

    def send_text(self, body: bytes) -> None:
        """Send a successful plain-text response."""
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
