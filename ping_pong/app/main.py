"""HTTP server exposing Ping-pong responses backed by PostgreSQL."""

import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import psycopg


def required_env(name: str) -> str:
    """Return a required non-empty environment variable."""
    value = os.getenv(name)
    if value is None or not value.strip():
        raise SystemExit(f"{name} environment variable is required")
    return value


def configured_int(
    name: str, *, minimum: int, maximum: int | None = None
) -> int:
    """Read and validate a required integer environment variable."""
    raw_value = required_env(name)
    try:
        value = int(raw_value)
    except ValueError as error:
        raise SystemExit(f"{name} must be an integer, got {raw_value!r}") from error

    if value < minimum or maximum is not None and value > maximum:
        expected = f"at least {minimum}"
        if maximum is not None:
            expected = f"between {minimum} and {maximum}"
        raise SystemExit(f"{name} must be {expected}")
    return value


def configured_float(name: str, *, minimum: float) -> float:
    """Read and validate a required floating-point environment variable."""
    raw_value = required_env(name)
    try:
        value = float(raw_value)
    except ValueError as error:
        raise SystemExit(f"{name} must be a number, got {raw_value!r}") from error

    if value < minimum:
        raise SystemExit(f"{name} must be at least {minimum}")
    return value


class CounterStore:
    """Persist and atomically increment one counter in PostgreSQL."""

    def __init__(self, connection_options: dict[str, object]) -> None:
        self.connection_options = connection_options

    def initialize(self, retries: int, retry_delay: float) -> None:
        """Create the counter table, retrying while PostgreSQL starts."""
        for attempt in range(1, retries + 1):
            try:
                with psycopg.connect(**self.connection_options) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS ping_pong_counter (
                                id SMALLINT PRIMARY KEY,
                                value BIGINT NOT NULL CHECK (value >= 0)
                            )
                            """
                        )
                        cursor.execute(
                            """
                            INSERT INTO ping_pong_counter (id, value)
                            VALUES (1, 0)
                            ON CONFLICT (id) DO NOTHING
                            """
                        )
                return
            except psycopg.OperationalError as error:
                if attempt == retries:
                    raise SystemExit(
                        f"PostgreSQL unavailable after {retries} attempts: {error}"
                    ) from error
                print(
                    f"PostgreSQL is not ready (attempt {attempt}/{retries}); "
                    f"retrying in {retry_delay:g} seconds",
                    flush=True,
                )
                time.sleep(retry_delay)

    def increment(self) -> int:
        """Increment the counter and return its value before the update."""
        with psycopg.connect(**self.connection_options) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE ping_pong_counter
                    SET value = value + 1
                    WHERE id = 1
                    RETURNING value - 1
                    """
                )
                row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Ping-pong counter row is missing")
        return int(row[0])

    def current(self) -> int:
        """Return the counter without changing it."""
        with psycopg.connect(**self.connection_options) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT value FROM ping_pong_counter WHERE id = 1"
                )
                row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Ping-pong counter row is missing")
        return int(row[0])


class PingPongRequestHandler(BaseHTTPRequestHandler):
    """Respond to the configured public and internal counter endpoints."""

    counter_store: CounterStore
    ping_pong_path: str
    pings_path: str

    def do_GET(self) -> None:
        path = urlsplit(self.path).path

        try:
            if path == self.ping_pong_path:
                value = self.counter_store.increment()
                self.send_text(f"pong {value}\n".encode())
                return

            if path == self.pings_path:
                value = self.counter_store.current()
                self.send_text(f"{value}\n".encode())
                return
        except (psycopg.Error, RuntimeError) as error:
            print(f"Database operation failed: {error}", flush=True)
            self.send_error(503, "Database is temporarily unavailable")
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
    connection_options: dict[str, object] = {
        "host": required_env("DB_HOST"),
        "port": configured_int("DB_PORT", minimum=1, maximum=65535),
        "dbname": required_env("DB_NAME"),
        "user": required_env("DB_USER"),
        "password": required_env("DB_PASSWORD"),
        "connect_timeout": configured_int(
            "DB_CONNECT_TIMEOUT_SECONDS", minimum=1
        ),
    }
    store = CounterStore(connection_options)
    store.initialize(
        retries=configured_int("DB_CONNECT_RETRIES", minimum=1),
        retry_delay=configured_float("DB_CONNECT_RETRY_DELAY_SECONDS", minimum=0),
    )

    PingPongRequestHandler.counter_store = store
    PingPongRequestHandler.ping_pong_path = required_env("PING_PONG_PATH")
    PingPongRequestHandler.pings_path = required_env("PINGS_PATH")

    host = required_env("HOST")
    port = configured_int("PORT", minimum=1, maximum=65535)
    server = ThreadingHTTPServer((host, port), PingPongRequestHandler)
    print(f"Server started in port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
