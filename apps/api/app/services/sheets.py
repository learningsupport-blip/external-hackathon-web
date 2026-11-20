import os
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

import httpx

from app.config import Settings
from app.errors import AppError
from app.schemas import ImportProposal
from app.services.importing import _proposal_from_raw

SHEET_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SHEET_HEADER = (
    "ready",
    "status",
    "hackathon_id",
    "source_url",
    "name",
    "organiser",
    "short_description",
    "description",
    "problem_statements",
    "organiser_logo_url",
    "banner_url",
    "official_website",
    "difficulty",
    "participation_type",
    "min_team_size",
    "max_team_size",
    "eligibility",
    "academic_year",
    "degree_requirements",
    "geographic_restrictions",
    "other_eligibility",
    "mode",
    "venue",
    "location",
    "event_duration",
    "registration_url",
    "registration_opens_at",
    "registration_closes_at",
    "registration_instructions",
    "submission_url",
    "submission_deadline",
    "required_deliverables",
    "submission_instructions",
    "prize_pool",
    "first_prize",
    "second_prize",
    "third_prize",
    "special_awards",
    "certificates",
    "internships",
    "other_rewards",
    "preparation_guidelines",
    "timezone",
    "themes",
    "technologies",
    "tags",
    "categories",
    "tracks",
    "deliverables",
    "prizes",
    "judging",
    "milestones",
    "resources",
    "faqs",
)
COMMA_FIELDS = ("themes", "technologies", "tags", "categories")
DATE_FIELDS = ("registration_opens_at", "registration_closes_at", "submission_deadline")
TEXT_FIELDS = tuple(
    column
    for column in SHEET_HEADER
    if column
    not in {
        "ready",
        "status",
        "hackathon_id",
        "source_url",
        *COMMA_FIELDS,
        *DATE_FIELDS,
        "min_team_size",
        "max_team_size",
        "tracks",
        "deliverables",
        "prizes",
        "judging",
        "milestones",
        "resources",
        "faqs",
    }
)
_SHEET_ID = re.compile(r"[A-Za-z0-9_-]+")
_CLOCK = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?$")
_YES = {"yes", "true"}
_NO = {"no", "false"}


@dataclass
class SheetSkip:
    row: int
    reason: str


@dataclass
class ClassifiedSheet:
    ready: list[tuple[int, ImportProposal]]
    skipped: list[SheetSkip]


def sheet_status(settings: Settings) -> dict:
    sheet_id = settings.google_sheet_id.strip()
    path = settings.google_sheets_credentials.strip()
    if not sheet_id and not path:
        return {"connected": False, "url": None, "message": "The Google Sheet is not connected."}
    if not _SHEET_ID.fullmatch(sheet_id):
        return {"connected": False, "url": None, "message": "The Google Sheet id is not valid."}
    if not path or not os.path.isfile(path):
        return {"connected": False, "url": None, "message": "The Google service account file was not found."}
    return {"connected": True, "url": f"https://docs.google.com/spreadsheets/d/{sheet_id}", "message": None}


def sheet_connected(settings: Settings) -> bool:
    return bool(sheet_status(settings)["connected"])


def assert_sheet_id(value: str) -> str:
    cleaned = value.strip()
    if _SHEET_ID.fullmatch(cleaned) is None:
        raise AppError(422, "invalid_sheet", "The Google Sheet id is not valid.")
    return cleaned


def proposal_to_cells(proposal: ImportProposal, *, source_url: str) -> list[str]:
    data = proposal.model_dump()
    cells = {
        "ready": "",
        "status": "extracted",
        "hackathon_id": "",
        "source_url": source_url,
    }
    for field in TEXT_FIELDS:
        cells[field] = _text(data.get(field))
    for field in DATE_FIELDS:
        cells[field] = _text(data.get(field))
    for field in ("min_team_size", "max_team_size"):
        value = data.get(field)
        cells[field] = "" if value is None else str(value)
    for field in COMMA_FIELDS:
        cells[field] = ", ".join(item for item in data.get(field) or [] if item)
    cells["tracks"] = _lines(
        [_pair(item.get("name"), item.get("requirements")) for item in data.get("tracks") or []]
    )
    cells["deliverables"] = _lines(
        [
            _join(item.get("title"), item.get("detail"), "yes" if item.get("required", True) else "no")
            for item in data.get("deliverables") or []
        ]
    )
    cells["prizes"] = _lines([_pair(item.get("label"), item.get("detail")) for item in data.get("prizes") or []])
    cells["judging"] = _lines(
        [
            _join(item.get("title"), item.get("detail"))
            if item.get("weight") is None
            else _join(item.get("title"), item.get("detail"), str(item.get("weight")))
            for item in data.get("judging") or []
        ]
    )
    cells["milestones"] = _lines(
        [
            _join(
                item.get("title"),
                item.get("type"),
                _text(item.get("starts_at")),
                _text(item.get("ends_at")),
                item.get("description"),
            )
            for item in data.get("milestones") or []
        ]
    )
    cells["resources"] = _lines(
        [_join(item.get("title"), item.get("url"), item.get("kind")) for item in data.get("resources") or []]
    )
    cells["faqs"] = _lines([_pair(item.get("question"), item.get("answer")) for item in data.get("faqs") or []])
    return [cells[column] for column in SHEET_HEADER]


def cells_to_proposal(cells: list[str]) -> ImportProposal:
    return _proposal_from_raw(_raw_from_cells(cells))


def classify_sheet(rows: list[list[str]]) -> ClassifiedSheet:
    _require_header(rows)
    ready: list[tuple[int, ImportProposal]] = []
    skipped: list[SheetSkip] = []
    for row_number, cells in enumerate(rows[1:], start=2):
        record = _record(cells)
        if record["ready"].strip().casefold() != "yes":
            continue
        if _already_imported(record["hackathon_id"]):
            skipped.append(SheetSkip(row=row_number, reason="This row was already imported"))
            continue
        if len(record["name"].strip()) < 2 or len(record["organiser"].strip()) < 2:
            skipped.append(SheetSkip(row=row_number, reason="Enter the hackathon name and organiser"))
            continue
        ready.append((row_number, cells_to_proposal(cells)))
    return ClassifiedSheet(ready=ready, skipped=skipped)


def publish_extract(settings: Settings, proposal: ImportProposal, source_url: str) -> int:
    sheet_id = _require_connection(settings)
    title = _sheet_title(settings, sheet_id)
    table = _read_table(settings, sheet_id, title)
    if not table or not any(cell.strip() for cell in table[0]):
        _write_row(settings, sheet_id, title, 1, list(SHEET_HEADER))
        table = [list(SHEET_HEADER)]
    _require_header(table)
    cells = proposal_to_cells(proposal, source_url=source_url)
    for row_number, row in enumerate(table[1:], start=2):
        record = _record(row)
        if record["source_url"] == source_url and not record["hackathon_id"].strip():
            _write_row(settings, sheet_id, title, row_number, cells)
            return row_number
    _append_row(settings, sheet_id, title, cells)
    return len(table) + 1


def pull_ready(db, settings: Settings, actor) -> dict:
    from app.services.importing import commit_import

    sheet_id = _require_connection(settings)
    title = _sheet_title(settings, sheet_id)
    table = _read_table(settings, sheet_id, title)
    if not table:
        raise AppError(422, "sheet_header", "The sheet header does not match the HackHub columns.")
    classified = classify_sheet(table)
    created: list[str] = []
    skipped = list(classified.skipped)
    for row_number, proposal in classified.ready:
        try:
            hackathon = commit_import(db, settings, actor, proposal)
        except AppError as exc:
            skipped.append(SheetSkip(row=row_number, reason=exc.message))
            continue
        _write_range(
            settings,
            sheet_id,
            title,
            f"B{row_number}:C{row_number}",
            [["imported", str(hackathon.id)]],
        )
        created.append(str(hackathon.id))
    return {"created_ids": created, "skipped": skipped}


def _already_imported(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    try:
        UUID(text)
    except ValueError:
        return False
    return True


def _require_connection(settings: Settings) -> str:
    status = sheet_status(settings)
    if not status["connected"]:
        raise AppError(503, "sheet_unconfigured", status["message"])
    return assert_sheet_id(settings.google_sheet_id)


def _require_header(rows: list[list[str]]) -> None:
    if not rows:
        raise AppError(422, "sheet_header", "The sheet header does not match the HackHub columns.")
    header = tuple(cell.strip() for cell in rows[0])
    while header and not header[-1]:
        header = header[:-1]
    if header != SHEET_HEADER:
        raise AppError(422, "sheet_header", "The sheet header does not match the HackHub columns.")


def _raw_from_cells(cells: list[str]) -> dict:
    record = _record(cells)
    raw: dict = {field: record[field].strip() or None for field in (*TEXT_FIELDS, *DATE_FIELDS)}
    for field in DATE_FIELDS:
        raw[field] = _sheet_date(record[field])
    for field in ("min_team_size", "max_team_size"):
        text = record[field].strip()
        raw[field] = int(text) if text.isdigit() else text or None
    for field in COMMA_FIELDS:
        raw[field] = [item.strip() for item in record[field].split(",") if item.strip()]
    raw["tracks"] = [_track(line) for line in _item_lines(record["tracks"])]
    raw["deliverables"] = [_deliverable(line) for line in _item_lines(record["deliverables"])]
    raw["prizes"] = [_prize(line) for line in _item_lines(record["prizes"])]
    raw["judging"] = [_judging(line) for line in _item_lines(record["judging"])]
    raw["milestones"] = [_milestone(line) for line in _item_lines(record["milestones"])]
    raw["resources"] = [_resource(line) for line in _item_lines(record["resources"])]
    raw["faqs"] = [_faq(line) for line in _item_lines(record["faqs"])]
    source = record["source_url"].strip()
    raw["source_urls"] = [source] if source else []
    raw["name"] = record["name"]
    raw["organiser"] = record["organiser"]
    return raw


def _record(cells: list[str]) -> dict[str, str]:
    padded = list(cells) + [""] * max(0, len(SHEET_HEADER) - len(cells))
    return {column: str(padded[index] or "") for index, column in enumerate(SHEET_HEADER)}


def _sheet_date(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    match = _CLOCK.fullmatch(text)
    if match is None:
        return text
    seconds = match.group(3) or "00"
    return f"{match.group(1)}T{match.group(2)}:{seconds}"


def _item_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _parts(line: str) -> list[str]:
    return [part.strip() for part in line.split("|")]


def _track(line: str) -> dict:
    parts = _parts(line)
    return {"name": parts[0] if parts else "", "requirements": "|".join(parts[1:]).strip() or None}


def _deliverable(line: str) -> dict:
    parts = _parts(line)
    required = True
    detail_parts = parts[1:]
    if detail_parts and detail_parts[-1].casefold() in _YES | _NO:
        required = detail_parts[-1].casefold() in _YES
        detail_parts = detail_parts[:-1]
    return {"title": parts[0] if parts else "", "detail": "|".join(detail_parts).strip() or None, "required": required}


def _prize(line: str) -> dict:
    parts = _parts(line)
    return {"label": parts[0] if parts else "", "detail": "|".join(parts[1:]).strip() or None}


def _judging(line: str) -> dict:
    parts = _parts(line)
    weight = None
    detail_parts = parts[1:]
    if detail_parts and detail_parts[-1].isdigit():
        weight = int(detail_parts[-1])
        detail_parts = detail_parts[:-1]
    return {"title": parts[0] if parts else "", "detail": "|".join(detail_parts).strip() or None, "weight": weight}


def _milestone(line: str) -> dict:
    parts = _parts(line)
    while len(parts) < 5:
        parts.append("")
    if len(parts) > 5:
        parts = parts[:4] + ["|".join(parts[4:]).strip()]
    return {
        "title": parts[0],
        "type": parts[1] or None,
        "starts_at": _sheet_date(parts[2]),
        "ends_at": _sheet_date(parts[3]),
        "description": parts[4] or None,
    }


def _resource(line: str) -> dict:
    parts = _parts(line)
    while len(parts) < 3:
        parts.append("")
    if len(parts) > 3:
        parts = parts[:2] + ["|".join(parts[2:]).strip()]
    return {"title": parts[0], "url": parts[1], "kind": parts[2] or None}


def _faq(line: str) -> dict:
    parts = _parts(line)
    return {"question": parts[0] if parts else "", "answer": "|".join(parts[1:]).strip()}


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).replace("\n", " ").strip()


def _clean_part(value) -> str:
    return _text(value).replace("|", "/")


def _pair(left, right) -> str:
    return _join(left, right)


def _join(*parts) -> str:
    return " | ".join(_clean_part(part) for part in parts)


def _lines(rows: list[str]) -> str:
    return "\n".join(row for row in rows if row.strip(" |"))


def _token(settings: Settings) -> str:
    from google.auth.transport import Response
    from google.oauth2 import service_account

    class _TokenResponse(Response):
        def __init__(self, status: int, headers: dict, data: bytes) -> None:
            self._status = status
            self._headers = headers
            self._data = data

        @property
        def status(self) -> int:
            return self._status

        @property
        def headers(self) -> dict:
            return self._headers

        @property
        def data(self) -> bytes:
            return self._data

    path = settings.google_sheets_credentials.strip()
    try:
        credentials = service_account.Credentials.from_service_account_file(path, scopes=[SHEET_SCOPE])
    except (ValueError, OSError) as exc:
        raise AppError(503, "sheet_unconfigured", "The Google service account file could not be read.") from exc

    def request(url, method="GET", body=None, headers=None, timeout=None, **_kwargs):
        response = httpx.request(method, url, content=body, headers=headers, timeout=timeout or 30)
        return _TokenResponse(response.status_code, dict(response.headers), response.content)

    credentials.refresh(request)
    if not credentials.token:
        raise AppError(502, "sheet_failed", "Google did not return a token.")
    return credentials.token


def _sheet_title(settings: Settings, sheet_id: str) -> str:
    payload = _google(settings, "GET", f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=sheets.properties.title")
    sheets = payload.get("sheets") or []
    if not sheets:
        raise AppError(502, "sheet_failed", "The Google Sheet has no tabs.")
    title = ((sheets[0].get("properties") or {}).get("title")) or "Sheet1"
    return str(title)


def _read_table(settings: Settings, sheet_id: str, title: str) -> list[list[str]]:
    encoded = quote(_a1(title, f"A:{_column_letter(len(SHEET_HEADER))}"), safe="")
    payload = _google(settings, "GET", f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{encoded}")
    return [[str(cell) for cell in row] for row in payload.get("values") or []]


def _write_row(settings: Settings, sheet_id: str, title: str, row_number: int, cells: list[str]) -> None:
    end = _column_letter(len(SHEET_HEADER))
    _write_range(settings, sheet_id, title, f"A{row_number}:{end}{row_number}", [cells])


def _append_row(settings: Settings, sheet_id: str, title: str, cells: list[str]) -> None:
    end = _column_letter(len(SHEET_HEADER))
    encoded = quote(_a1(title, f"A:{end}"), safe="")
    _google(
        settings,
        "POST",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{encoded}:append"
        "?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
        {"majorDimension": "ROWS", "values": [cells]},
    )


def _write_range(settings: Settings, sheet_id: str, title: str, a1: str, values: list[list[str]]) -> None:
    encoded = quote(_a1(title, a1), safe="")
    _google(
        settings,
        "PUT",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{encoded}?valueInputOption=RAW",
        {"majorDimension": "ROWS", "values": values},
    )


def _google(settings: Settings, method: str, url: str, body: dict | None = None) -> dict:
    response = httpx.request(
        method,
        url,
        headers={"Authorization": f"Bearer {_token(settings)}"},
        json=body,
        timeout=30,
    )
    if response.status_code >= 400:
        raise AppError(502, "sheet_failed", "The Google Sheet could not be read or updated.")
    if not response.content:
        return {}
    payload = response.json()
    if not isinstance(payload, dict):
        raise AppError(502, "sheet_failed", "The Google Sheet could not be read or updated.")
    return payload


def _a1(title: str, cells: str) -> str:
    return f"'{title.replace(chr(39), chr(39) * 2)}'!{cells}"


def _column_letter(index: int) -> str:
    letters = ""
    number = index
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
