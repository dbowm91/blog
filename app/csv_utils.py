import csv
import io
from typing import Iterator


SUBSCRIBER_CSV_HEADERS = ["email", "confirmed", "created_at", "expires_at"]


def _escape_csv_cell(value: str) -> str:
    """Escape CSV cell value to prevent formula injection."""
    if value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def generate_subscribers_csv(rows) -> Iterator[str]:
    """Generate CSV output for subscriber rows.

    Args:
        rows: Iterable of Subscriber objects with email, confirmed, created_at, expires_at attributes.

    Yields:
        CSV formatted strings suitable for streaming response.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(SUBSCRIBER_CSV_HEADERS)
    yield buffer.getvalue()
    buffer.truncate(0)
    buffer.seek(0)

    for subscriber in rows:
        writer.writerow(
            [
                _escape_csv_cell(subscriber.email),
                subscriber.confirmed,
                subscriber.created_at.isoformat() if subscriber.created_at else "",
                subscriber.expires_at.isoformat() if subscriber.expires_at else "",
            ]
        )
        yield buffer.getvalue()
        buffer.truncate(0)
        buffer.seek(0)
