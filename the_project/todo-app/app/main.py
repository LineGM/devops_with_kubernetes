"""Todo application with a persistent, time-based image cache."""

import html
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


TODO_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Todo App</title>
    <style>
      * { box-sizing: border-box; }
      body {
        margin: 0;
        color: #292929;
        background: #f7f8fa;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      main {
        width: min(92vw, 900px);
        margin: 0 auto;
        padding: 3rem 0;
        text-align: center;
      }
      h1 { margin: 0 0 2rem; font-size: clamp(2.5rem, 7vw, 4rem); }
      .hero-image {
        display: block;
        width: min(100%, 600px);
        aspect-ratio: 1;
        margin: 0 auto;
        object-fit: cover;
        border-radius: 1rem;
        background: #e3e6eb;
        box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.14);
      }
      .todo-form {
        display: flex;
        gap: 0.75rem;
        margin: 3rem 0;
      }
      .todo-form input {
        min-width: 0;
        flex: 1;
        padding: 0.9rem 1rem;
        border: 2px solid #45ad55;
        border-radius: 0.5rem;
        font: inherit;
        font-size: 1.1rem;
      }
      .todo-form input:focus {
        outline: 3px solid rgba(69, 173, 85, 0.22);
        outline-offset: 1px;
      }
      .todo-form button {
        padding: 0.9rem 1.5rem;
        border: 0;
        border-radius: 0.5rem;
        color: white;
        background: #45ad55;
        font: inherit;
        font-size: 1.1rem;
        font-weight: 700;
        cursor: pointer;
      }
      .todo-form button:hover { background: #338c41; }
      .todo-form button:disabled { cursor: wait; opacity: 0.65; }
      .form-status {
        min-height: 1.5rem;
        margin: -2rem 0 2rem;
        color: #a12222;
      }
      .todos h2 { font-size: 2rem; }
      .todo-list {
        display: grid;
        gap: 0.75rem;
        margin: 1.5rem 0 0;
        padding: 0;
        list-style: none;
      }
      .todo-list li {
        padding: 1rem 1.25rem;
        border-left: 0.4rem solid #45ad55;
        border-radius: 0.35rem;
        background: white;
        box-shadow: 0 0.25rem 0.8rem rgba(0, 0, 0, 0.08);
        text-align: left;
        font-size: 1.1rem;
      }
      footer { margin: 2.5rem 0 0; color: #666; font-size: 1.1rem; }
      @media (max-width: 560px) {
        .todo-form { flex-direction: column; }
        .todo-form button { width: 100%; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Todo App</h1>
      <img class="hero-image" src="__IMAGE_PATH__" alt="A random landscape from Lorem Picsum">

      <form class="todo-form" id="todo-form">
        <input
          id="todo-input"
          type="text"
          name="todo"
          maxlength="__MAX_TODO_LENGTH__"
          placeholder="Enter a new todo (max __MAX_TODO_LENGTH__ characters)"
          aria-label="New todo"
          required
        >
        <button type="submit">Send</button>
      </form>
      <p class="form-status" id="form-status" role="status"></p>

      <section class="todos" aria-labelledby="todos-title">
        <h2 id="todos-title">Todos</h2>
        <ul class="todo-list" id="todo-list"><li>Loading todos...</li></ul>
      </section>

      <footer>DevOps with Kubernetes 2026</footer>
    </main>
    <script>
      const form = document.querySelector("#todo-form");
      const input = document.querySelector("#todo-input");
      const list = document.querySelector("#todo-list");
      const status = document.querySelector("#form-status");
      const button = form.querySelector("button");
      const todoApiUrl = __TODO_API_URL__;
      const maxTodoLength = __MAX_TODO_LENGTH__;

      function showTodos(todos) {
        list.replaceChildren();
        for (const todo of todos) {
          const item = document.createElement("li");
          item.textContent = todo.content;
          list.append(item);
        }
      }

      async function loadTodos() {
        try {
          const response = await fetch(todoApiUrl);
          if (!response.ok) throw new Error("Could not load todos");
          const todos = await response.json();
          if (!Array.isArray(todos)) throw new Error("Invalid todo response");
          showTodos(todos);
        } catch (error) {
          status.textContent = error.message;
        }
      }

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const content = input.value.trim();

        if (!content || content.length > maxTodoLength) {
          status.textContent = `Todo must contain between 1 and ${maxTodoLength} characters.`;
          return;
        }

        button.disabled = true;
        status.textContent = "";
        try {
          const response = await fetch(todoApiUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content }),
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || "Could not create todo");
          input.value = "";
          await loadTodos();
        } catch (error) {
          status.textContent = error.message;
        } finally {
          button.disabled = false;
        }
      });

      loadTodos();
    </script>
  </body>
</html>
"""


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


def configured_page(
    image_path: str, todo_api_url: str, max_todo_length: int
) -> bytes:
    """Render deployment configuration into the browser page."""
    return (
        TODO_PAGE_TEMPLATE.replace(
            "__IMAGE_PATH__", html.escape(image_path, quote=True)
        )
        .replace("__TODO_API_URL__", json.dumps(todo_api_url))
        .replace("__MAX_TODO_LENGTH__", str(max_todo_length))
        .encode("utf-8")
    )


class ImageCache:
    """Cache a remotely downloaded image in a file for a configured duration."""

    def __init__(
        self,
        image_file: Path,
        source_url: str,
        max_age: int,
        max_bytes: int,
        download_timeout: int,
    ) -> None:
        self.image_file = image_file
        self.source_url = source_url
        self.max_age = max_age
        self.max_bytes = max_bytes
        self.download_timeout = download_timeout
        self.lock = threading.Lock()

    def is_fresh(self) -> bool:
        """Return whether the cached file exists and is younger than max_age."""
        try:
            age = time.time() - self.image_file.stat().st_mtime
        except FileNotFoundError:
            return False
        return age < self.max_age

    def read(self) -> bytes:
        """Return a cached image, refreshing an expired file when possible."""
        with self.lock:
            if self.is_fresh():
                return self.image_file.read_bytes()

            had_stale_image = self.image_file.is_file()
            try:
                self.download()
            except (OSError, URLError, ValueError) as error:
                if not had_stale_image:
                    raise
                print(f"Image refresh failed; serving stale cache: {error}", flush=True)

            return self.image_file.read_bytes()

    def download(self) -> None:
        """Download a new image and atomically replace the cached file."""
        separator = "&" if "?" in self.source_url else "?"
        request_url = f"{self.source_url}{separator}cache_bust={time.time_ns()}"
        request = Request(
            request_url,
            headers={"Accept": "image/*", "User-Agent": "todo-app/2.6"},
        )

        with urlopen(request, timeout=self.download_timeout) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                raise ValueError(f"Unexpected content type: {content_type}")

            image = response.read(self.max_bytes + 1)

        if not image:
            raise ValueError("Downloaded image is empty")
        if len(image) > self.max_bytes:
            raise ValueError("Downloaded image is too large")

        self.image_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self.image_file.with_name(f".{self.image_file.name}.tmp")
        temporary_file.write_bytes(image)
        temporary_file.replace(self.image_file)
        print(f"Cached a new image from {self.source_url}", flush=True)


class TodoRequestHandler(BaseHTTPRequestHandler):
    """Serve the Todo page and its cached image."""

    image_cache: ImageCache
    app_path: str
    image_path: str
    todo_page: bytes

    def do_GET(self) -> None:
        path = urlsplit(self.path).path

        if path == self.app_path:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(self.todo_page)))
            self.end_headers()
            self.wfile.write(self.todo_page)
            return

        if path == self.image_path:
            self.serve_image()
            return

        self.send_error(404, "Not Found")

    def serve_image(self) -> None:
        """Return the current cached image or a temporary error response."""
        try:
            image = self.image_cache.read()
        except (OSError, URLError, ValueError) as error:
            print(f"Image is unavailable: {error}", flush=True)
            self.send_error(503, "Image is temporarily unavailable")
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(image)))
        self.end_headers()
        self.wfile.write(image)

    def log_message(self, format: str, *args: object) -> None:
        """Write request logs to stdout so Kubernetes can collect them."""
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> None:
    host = required_env("HOST")
    port = configured_int("PORT", minimum=1, maximum=65535)
    image_file = Path(required_env("IMAGE_CACHE_FILE"))
    image_url = required_env("IMAGE_URL")
    max_todo_length = configured_int("MAX_TODO_LENGTH", minimum=1)
    TodoRequestHandler.app_path = required_env("APP_PATH")
    TodoRequestHandler.image_path = required_env("IMAGE_PATH")
    TodoRequestHandler.todo_page = configured_page(
        image_path=TodoRequestHandler.image_path,
        todo_api_url=required_env("TODO_API_URL"),
        max_todo_length=max_todo_length,
    )
    TodoRequestHandler.image_cache = ImageCache(
        image_file=image_file,
        source_url=image_url,
        max_age=configured_int("IMAGE_CACHE_MAX_AGE_SECONDS", minimum=1),
        max_bytes=configured_int("IMAGE_MAX_BYTES", minimum=1),
        download_timeout=configured_int("IMAGE_DOWNLOAD_TIMEOUT_SECONDS", minimum=1),
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
