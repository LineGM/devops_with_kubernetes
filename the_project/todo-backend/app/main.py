"""In-memory HTTP API for the course Todo application."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


INITIAL_TODOS = (
    {"id": 1, "content": "Learn Kubernetes basics"},
    {"id": 2, "content": "Deploy the Todo App to the cluster"},
    {"id": 3, "content": "Configure persistent volumes"},
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


class TodoRequestHandler(BaseHTTPRequestHandler):
    """Expose the in-memory todo collection as a JSON API."""

    todos = [dict(todo) for todo in INITIAL_TODOS]
    next_id = len(todos) + 1
    todos_lock = threading.Lock()
    todos_path: str
    max_todo_length: int
    max_request_bytes: int

    def do_GET(self) -> None:
        if urlsplit(self.path).path != self.todos_path:
            self.send_json({"error": "Not found"}, status=404)
            return

        with self.todos_lock:
            todos = [dict(todo) for todo in self.todos]
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
            self.send_json({"error": "content must be a string"}, status=400)
            return

        content = content.strip()
        if not content:
            self.send_json({"error": "content cannot be empty"}, status=400)
            return
        if len(content) > self.max_todo_length:
            self.send_json(
                {
                    "error": (
                        f"content cannot exceed {self.max_todo_length} characters"
                    )
                },
                status=400,
            )
            return

        with self.todos_lock:
            todo = {"id": self.next_id, "content": content}
            type(self).next_id += 1
            self.todos.append(todo)

        print(f"Created todo {todo['id']}: {content}", flush=True)
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
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> None:
    host = required_env("HOST")
    port = configured_int("PORT", minimum=1, maximum=65535)
    TodoRequestHandler.todos_path = required_env("TODOS_PATH")
    TodoRequestHandler.max_todo_length = configured_int(
        "MAX_TODO_LENGTH", minimum=1
    )
    TodoRequestHandler.max_request_bytes = configured_int(
        "MAX_REQUEST_BYTES", minimum=1
    )
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
