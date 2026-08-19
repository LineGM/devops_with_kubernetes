"""Create a Todo that points to a random Wikipedia article."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


class NoRedirectHandler(HTTPRedirectHandler):
    """Expose redirect responses instead of following them automatically."""

    def redirect_request(
        self,
        request: Request,
        file_pointer: object,
        code: int,
        message: str,
        headers: object,
        new_url: str,
    ) -> None:
        return None


def required_env(name: str) -> str:
    """Return a required non-empty environment variable."""
    value = os.getenv(name)
    if value is None or not value.strip():
        raise SystemExit(f"{name} environment variable is required")
    return value


def configured_int(name: str, *, minimum: int) -> int:
    """Read and validate a required integer environment variable."""
    raw_value = required_env(name)
    try:
        value = int(raw_value)
    except ValueError as error:
        raise SystemExit(f"{name} must be an integer, got {raw_value!r}") from error

    if value < minimum:
        raise SystemExit(f"{name} must be at least {minimum}")
    return value


def random_article_url(source_url: str, timeout: int) -> str:
    """Return the target URL from Wikipedia's random-page redirect."""
    request = Request(
        source_url,
        headers={"Accept": "text/html", "User-Agent": "todo-generator/2.9"},
    )
    opener = build_opener(NoRedirectHandler())

    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
            headers = response.headers
    except HTTPError as error:
        if error.code not in REDIRECT_STATUS_CODES:
            raise
        status = error.code
        headers = error.headers

    if status not in REDIRECT_STATUS_CODES:
        raise RuntimeError(f"Expected a redirect from Wikipedia, got HTTP {status}")

    location = headers.get("Location")
    if not location:
        raise RuntimeError("Wikipedia redirect did not include a Location header")
    return urljoin(source_url, location)


def create_reminder(
    source_url: str,
    prefix: str,
    max_length: int,
    attempts: int,
    timeout: int,
) -> str:
    """Find a random-article reminder that fits the Todo length limit."""
    for attempt in range(1, attempts + 1):
        article_url = random_article_url(source_url, timeout)
        reminder = f"{prefix}{article_url}"
        if len(reminder) <= max_length:
            return reminder
        print(
            f"Random article URL was too long on attempt {attempt}/{attempts}",
            flush=True,
        )
    raise RuntimeError(
        f"Could not find a reminder within {max_length} characters "
        f"after {attempts} attempts"
    )


def post_todo(todo_url: str, content: str, timeout: int) -> dict[str, object]:
    """Create the generated Todo through the backend HTTP API."""
    body = json.dumps({"content": content}).encode("utf-8")
    request = Request(
        todo_url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "todo-generator/2.9",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read()
            status = response.status
    except HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Todo backend returned HTTP {error.code}: {response_body}"
        ) from error

    if status != 201:
        raise RuntimeError(f"Todo backend returned unexpected HTTP {status}")

    payload = json.loads(response_body)
    if not isinstance(payload, dict):
        raise RuntimeError("Todo backend response was not a JSON object")
    return payload


def main() -> None:
    timeout = configured_int("HTTP_TIMEOUT_SECONDS", minimum=1)
    reminder = create_reminder(
        source_url=required_env("WIKIPEDIA_RANDOM_URL"),
        prefix=required_env("TODO_REMINDER_PREFIX"),
        max_length=configured_int("MAX_TODO_LENGTH", minimum=1),
        attempts=configured_int("MAX_RANDOM_ATTEMPTS", minimum=1),
        timeout=timeout,
    )
    todo = post_todo(required_env("TODO_BACKEND_URL"), reminder, timeout)
    print(
        f"Created Todo {todo.get('id')}: {todo.get('content', reminder)}",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as error:
        raise SystemExit(f"Todo generation failed: {error}") from error
