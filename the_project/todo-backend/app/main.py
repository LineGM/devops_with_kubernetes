"""PostgreSQL-backed HTTP API for the course Todo application."""

import json
import os
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import psycopg
from psycopg import sql


INITIAL_TODOS = (
    "Learn Kubernetes basics",
    "Deploy the Todo App to the cluster",
    "Configure persistent volumes",
)


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


def log_todo_submission(
    content: object,
    *,
    status: str,
    reason: str,
    todo_id: int | None = None,
) -> None:
    """Write one structured event for every parsed Todo submission."""
    event = {
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        ),
        "event": "todo_submission",
        "status": status,
        "reason": reason,
        "content": content,
        "length": len(content) if isinstance(content, str) else None,
    }
    if todo_id is not None:
        event["todo_id"] = todo_id
    print(json.dumps(event, ensure_ascii=False, separators=(",", ":")), flush=True)


class TodoStore:
    """Persist and retrieve todos in PostgreSQL."""

    def __init__(
        self,
        connection_options: dict[str, object],
        max_todo_length: int,
    ) -> None:
        self.connection_options = connection_options
        self.max_todo_length = max_todo_length

    def initialize(self, retries: int, retry_delay: float) -> None:
        """Create and seed the table, retrying while PostgreSQL starts."""
        for attempt in range(1, retries + 1):
            try:
                with psycopg.connect(**self.connection_options) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            sql.SQL(
                                """
                                CREATE TABLE IF NOT EXISTS todos (
                                    id BIGSERIAL PRIMARY KEY,
                                    content TEXT NOT NULL CHECK (
                                        char_length(content) BETWEEN 1 AND {}
                                    )
                                )
                                """
                            ).format(sql.Literal(self.max_todo_length))
                        )
                        cursor.execute("SELECT EXISTS (SELECT 1 FROM todos)")
                        has_todos = bool(cursor.fetchone()[0])
                        if not has_todos:
                            cursor.executemany(
                                "INSERT INTO todos (content) VALUES (%s)",
                                ((content,) for content in INITIAL_TODOS),
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

    def list_todos(self) -> list[dict[str, object]]:
        """Return all todos ordered by their persistent IDs."""
        with psycopg.connect(**self.connection_options) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, content FROM todos ORDER BY id")
                rows = cursor.fetchall()
        return [{"id": int(row[0]), "content": str(row[1])} for row in rows]

    def create_todo(self, content: str) -> dict[str, object]:
        """Insert a todo and return its generated ID and content."""
        with psycopg.connect(**self.connection_options) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO todos (content) VALUES (%s) RETURNING id",
                    (content,),
                )
                row = cursor.fetchone()
        if row is None:
            raise RuntimeError("PostgreSQL did not return a todo ID")
        return {"id": int(row[0]), "content": content}


class TodoRequestHandler(BaseHTTPRequestHandler):
    """Expose the PostgreSQL todo collection as a JSON API."""

    todo_store: TodoStore
    todos_path: str
    max_todo_length: int
    max_request_bytes: int

    def do_GET(self) -> None:
        if urlsplit(self.path).path != self.todos_path:
            self.send_json({"error": "Not found"}, status=404)
            return

        try:
            todos = self.todo_store.list_todos()
        except psycopg.Error as error:
            print(f"Database operation failed: {error}", flush=True)
            self.send_json({"error": "Database is temporarily unavailable"}, status=503)
            return
        self.send_json(todos)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != self.todos_path:
            self.send_json({"error": "Not found"}, status=404)
            return

        payload = self.read_json_body()
        if payload is None:
            return

        content = payload.get("content")
        if not isinstance(content, str):
            log_todo_submission(
                content,
                status="rejected",
                reason="content_not_string",
            )
            self.send_json({"error": "content must be a string"}, status=400)
            return

        content = content.strip()
        if not content:
            log_todo_submission(content, status="rejected", reason="content_empty")
            self.send_json({"error": "content cannot be empty"}, status=400)
            return
        if len(content) > self.max_todo_length:
            log_todo_submission(content, status="rejected", reason="content_too_long")
            self.send_json(
                {
                    "error": (
                        f"content cannot exceed {self.max_todo_length} characters"
                    )
                },
                status=400,
            )
            return

        try:
            todo = self.todo_store.create_todo(content)
        except (psycopg.Error, RuntimeError) as error:
            print(f"Database operation failed: {error}", flush=True)
            log_todo_submission(
                content,
                status="rejected",
                reason="database_unavailable",
            )
            self.send_json({"error": "Database is temporarily unavailable"}, status=503)
            return

        log_todo_submission(
            content,
            status="accepted",
            reason="created",
            todo_id=int(todo["id"]),
        )
        self.send_json(todo, status=201)

    def read_json_body(self) -> dict[str, object] | None:
        """Read and validate a small JSON object from the request body."""
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            self.send_json({"error": "Content-Type must be application/json"}, status=415)
            return None

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json({"error": "Invalid Content-Length"}, status=400)
            return None

        if content_length < 1:
            self.send_json({"error": "Request body is required"}, status=400)
            return None
        if content_length > self.max_request_bytes:
            self.send_json({"error": "Request body is too large"}, status=413)
            return None

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json({"error": "Request body must be valid JSON"}, status=400)
            return None

        if not isinstance(payload, dict):
            self.send_json({"error": "Request body must be a JSON object"}, status=400)
            return None
        return payload

    def send_json(self, payload: object, status: int = 200) -> None:
        """Serialize and send a JSON response."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Write request logs to stdout so Kubernetes can collect them."""
        if self.headers.get("User-Agent", "").startswith("kube-probe/"):
            return
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> None:
    max_todo_length = configured_int("MAX_TODO_LENGTH", minimum=1)
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
    store = TodoStore(connection_options, max_todo_length)
    store.initialize(
        retries=configured_int("DB_CONNECT_RETRIES", minimum=1),
        retry_delay=configured_float("DB_CONNECT_RETRY_DELAY_SECONDS", minimum=0),
    )

    TodoRequestHandler.todo_store = store
    TodoRequestHandler.todos_path = required_env("TODOS_PATH")
    TodoRequestHandler.max_todo_length = max_todo_length
    TodoRequestHandler.max_request_bytes = configured_int(
        "MAX_REQUEST_BYTES", minimum=1
    )

    host = required_env("HOST")
    port = configured_int("PORT", minimum=1, maximum=65535)
    server = ThreadingHTTPServer((host, port), TodoRequestHandler)
    print(f"Server started in port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
