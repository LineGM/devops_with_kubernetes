"""Serve Log output status enriched with the Ping-pong count over HTTP."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


DEFAULT_PORT = 3000
DEFAULT_LOG_FILE = "/usr/src/app/files/log.txt"
DEFAULT_PING_PONG_URL = "http://ping-pong-svc/pings"
DEFAULT_INFORMATION_FILE = "/usr/src/app/config/information.txt"


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
    """Return writer status and fetch the pong count from another Pod."""

    log_file = Path(DEFAULT_LOG_FILE)
    ping_pong_url = DEFAULT_PING_PONG_URL
    information_file = Path(DEFAULT_INFORMATION_FILE)
    message = ""

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/":
            self.send_error(404, "Not Found")
            return

        try:
            status = self.log_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            status = "Log output is not available yet"

        try:
            file_content = self.information_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            file_content = "Configuration file is not available"

        counter = self.fetch_ping_pong_count()
        body = (
            f"file content: {file_content}\n"
            f"env variable: MESSAGE={self.message}\n"
            f"{status}.\n"
            f"Ping / Pongs: {counter}\n"
        ).encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def fetch_ping_pong_count(self) -> int:
        """Fetch the current counter through the Ping-pong Kubernetes Service."""
        request = Request(
            self.ping_pong_url,
            headers={"Accept": "text/plain", "User-Agent": "log-output/2.1"},
        )

        try:
            with urlopen(request, timeout=5) as response:
                counter = int(response.read().decode("utf-8").strip())
            if counter < 0:
                raise ValueError("Ping-pong counter cannot be negative")
            return counter
        except (OSError, URLError, ValueError) as error:
            print(f"Could not fetch Ping-pong counter: {error}", flush=True)
            return 0

    def log_message(self, format: str, *args: object) -> None:
        """Write request logs to stdout so Kubernetes can collect them."""
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> None:
    port = configured_port()
    LogRequestHandler.log_file = Path(os.getenv("LOG_FILE", DEFAULT_LOG_FILE))
    LogRequestHandler.ping_pong_url = os.getenv(
        "PING_PONG_URL", DEFAULT_PING_PONG_URL
    )
    LogRequestHandler.information_file = Path(
        os.getenv("INFORMATION_FILE", DEFAULT_INFORMATION_FILE)
    )
    LogRequestHandler.message = os.getenv("MESSAGE", "")
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
