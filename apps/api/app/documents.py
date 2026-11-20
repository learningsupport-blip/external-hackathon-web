"""JSON list items stored on a hackathon or a query."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import object_session
from sqlalchemy.orm.attributes import flag_modified

_TIMES = {"published_at", "created_at", "last_verified_at", "updated_at"}


class Doc:
    def __init__(self, data: dict):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        value = self._data.get(name)
        if value is None:
            return None
        if name == "id" or name.endswith("_id"):
            return value if isinstance(value, UUID) else UUID(str(value))
        if name in _TIMES or name.endswith("_at"):
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(value)
        return value

    def __setattr__(self, name: str, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        self._data[name] = _plain(value)


def default_internal() -> dict:
    return {
        "internal_notes": None,
        "tracking_status": None,
        "administrative_comments": None,
        "verification_status": "unverified",
        "last_verified_at": None,
        "source_urls": None,
    }


def default_sections(sections) -> dict:
    return {section: "not_specified" for section in sections}


def items(owner, field: str) -> list[Doc]:
    raw = getattr(owner, field) or []
    docs = [Doc(item) for item in raw]
    if any("position" in item._data for item in docs):
        docs.sort(key=lambda item: item.position if item.position is not None else 0)
    return docs


def touch(owner, field: str) -> None:
    flag_modified(owner, field)
    _flush(owner)


def append_item(owner, field: str, data: dict) -> Doc:
    raw = list(getattr(owner, field) or [])
    payload = {key: _plain(value) for key, value in data.items()}
    payload["id"] = str(payload.get("id") or uuid4())
    raw.append(payload)
    setattr(owner, field, raw)
    flag_modified(owner, field)
    _flush(owner)
    return Doc(payload)


def drop_item(owner, field: str, row_id) -> None:
    target = str(row_id)
    kept = [item for item in (getattr(owner, field) or []) if str(item.get("id")) != target]
    setattr(owner, field, kept)
    flag_modified(owner, field)
    _flush(owner)


def _flush(owner) -> None:
    session = object_session(owner)
    if session is not None:
        session.flush()


def _plain(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value
