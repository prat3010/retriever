import base64
import json
from datetime import datetime, timezone
from uuid import UUID


def encode_cursor(dt: datetime, uuid_val: UUID) -> str:
    """Encode created_at datetime and uuid to a base64 string cursor."""
    payload = [dt.isoformat(), str(uuid_val)]
    json_bytes = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8")


def decode_cursor(cursor_str: str) -> tuple[datetime, UUID]:
    """Decode base64 string cursor to created_at datetime and uuid."""
    try:
        json_bytes = base64.urlsafe_b64decode(cursor_str.encode("utf-8"))
        payload = json.loads(json_bytes.decode("utf-8"))
        dt = datetime.fromisoformat(payload[0])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        uuid_val = UUID(payload[1])
        return dt, uuid_val
    except Exception as e:
        raise ValueError("Invalid cursor format") from e
