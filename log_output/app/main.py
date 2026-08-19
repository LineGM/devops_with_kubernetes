"""Print one startup-generated UUID with a fresh UTC timestamp every five seconds."""

import time
import uuid
from datetime import datetime, timezone


def utc_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main() -> None:
    random_string = str(uuid.uuid4())

    while True:
        print(f"{utc_timestamp()}: {random_string}", flush=True)
        time.sleep(5)


if __name__ == "__main__":
    main()
