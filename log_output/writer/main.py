"""Append one startup-generated UUID and fresh UTC timestamps to a shared file."""

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_LOG_FILE = "/usr/src/app/files/log.txt"


def utc_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main() -> None:
    random_string = str(uuid.uuid4())
    log_file = Path(os.getenv("LOG_FILE", DEFAULT_LOG_FILE))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = log_file.with_name(f".{log_file.name}.tmp")

    try:
        while True:
            line = f"{utc_timestamp()}: {random_string}"
            temporary_file.write_text(f"{line}\n", encoding="utf-8")
            temporary_file.replace(log_file)
            print(line, flush=True)
            time.sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
