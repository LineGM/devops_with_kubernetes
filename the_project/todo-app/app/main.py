"""Todo application with a persistent, time-based image cache."""

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


DEFAULT_PORT = 3000
DEFAULT_IMAGE_URL = "https://picsum.photos/1200"
DEFAULT_IMAGE_FILE = "/usr/src/app/files/image.jpg"
DEFAULT_CACHE_MAX_AGE_SECONDS = 600
MAX_IMAGE_BYTES = 20 * 1024 * 1024

TODO_PAGE = b"""<!doctype html>
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
      img {
        display: block;
        width: 100%;
        max-height: 760px;
        object-fit: cover;
        border-radius: 1rem;
        background: #e3e6eb;
        box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.14);
      }
      p { margin: 2rem 0 0; color: #666; font-size: 1.4rem; }
    </style>
  </head>
  <body>
    <main>
      <h1>Todo App</h1>
      <img src="/image" alt="A random landscape from Lorem Picsum">
      <p>DevOps with Kubernetes 2026</p>
    </main>
  </body>
</html>
"""


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


def configured_cache_max_age() -> int:
    """Read and validate the image cache lifetime from the environment."""
    raw_age = os.getenv(
        "IMAGE_CACHE_MAX_AGE_SECONDS", str(DEFAULT_CACHE_MAX_AGE_SECONDS)
    )

    try:
        max_age = int(raw_age)
    except ValueError as error:
        raise SystemExit(
            f"IMAGE_CACHE_MAX_AGE_SECONDS must be an integer, got {raw_age!r}"
        ) from error

    if max_age < 1:
        raise SystemExit("IMAGE_CACHE_MAX_AGE_SECONDS must be positive")

    return max_age


class ImageCache:
    """Cache a remotely downloaded image in a file for a configured duration."""

    def __init__(self, image_file: Path, source_url: str, max_age: int) -> None:
        self.image_file = image_file
        self.source_url = source_url
        self.max_age = max_age
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
            headers={"Accept": "image/*", "User-Agent": "todo-app/1.12"},
        )

        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                raise ValueError(f"Unexpected content type: {content_type}")

            image = response.read(MAX_IMAGE_BYTES + 1)

        if not image:
            raise ValueError("Downloaded image is empty")
        if len(image) > MAX_IMAGE_BYTES:
            raise ValueError("Downloaded image is too large")

        self.image_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self.image_file.with_name(f".{self.image_file.name}.tmp")
        temporary_file.write_bytes(image)
        temporary_file.replace(self.image_file)
        print(f"Cached a new image from {self.source_url}", flush=True)


class TodoRequestHandler(BaseHTTPRequestHandler):
    """Serve the Todo page and its cached image."""

    image_cache: ImageCache

    def do_GET(self) -> None:
        path = urlsplit(self.path).path

        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(TODO_PAGE)))
            self.end_headers()
            self.wfile.write(TODO_PAGE)
            return

        if path == "/image":
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
    port = configured_port()
    image_file = Path(os.getenv("IMAGE_CACHE_FILE", DEFAULT_IMAGE_FILE))
    image_url = os.getenv("IMAGE_URL", DEFAULT_IMAGE_URL)
    TodoRequestHandler.image_cache = ImageCache(
        image_file=image_file,
        source_url=image_url,
        max_age=configured_cache_max_age(),
    )

    server = ThreadingHTTPServer(("0.0.0.0", port), TodoRequestHandler)
    print(f"Server started in port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
