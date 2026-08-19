"""Log and serve one startup-generated UUID with fresh UTC timestamps."""

import os
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


DEFAULT_PORT = 3000


def utc_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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


def emit_log_messages(random_string: str) -> None:
    """Write the current timestamp and startup UUID every five seconds."""
    while True:
        print(f"{utc_timestamp()}: {random_string}", flush=True)
        time.sleep(5)


class StatusRequestHandler(BaseHTTPRequestHandler):
    """Return the current timestamp and process-specific UUID."""

    random_string = ""

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/":
            self.send_error(404, "Not Found")
            return

        body = f"{utc_timestamp()}: {self.random_string}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Write request logs to stdout so Kubernetes can collect them."""
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> None:
    random_string = str(uuid.uuid4())
    port = configured_port()
    StatusRequestHandler.random_string = random_string
    server = ThreadingHTTPServer(("0.0.0.0", port), StatusRequestHandler)
    logger = threading.Thread(
        target=emit_log_messages,
        args=(random_string,),
        daemon=True,
        name="periodic-logger",
    )
    logger.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
