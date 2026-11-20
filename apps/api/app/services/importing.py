import html
import ipaddress
import json
import logging
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy.orm import Session

from app.catalog import all_categories
from app.config import Settings
from app.errors import AppError
from app.models import User
from app.schemas import (
    DIFFICULTIES,
    MODES,
    MILESTONE_TYPES,
    PARTICIPATION,
    RESOURCE_KINDS,
    DeliverableIn,
    FaqIn,
    HackathonCreate,
    HackathonUpdate,
    ImportDeliverable,
    ImportFaq,
    ImportJudging,
    ImportMilestone,
    ImportPrize,
    ImportProposal,
    ImportResource,
    ImportTrack,
    InternalUpdate,
    JudgingIn,
    MilestoneIn,
    PrizeIn,
    ResourceIn,
    TrackIn,
    _blank,
    _http_url,
    _timezone,
)
from app.security import slugify
from app.services import content, hackathons

logger = logging.getLogger(__name__)

MAX_BYTES = 1_000_000
MAX_EXTRA_PAGES = 8
PAGE_TIMEOUT = 15
MODEL_TIMEOUT = 60
TEXT_PER_PAGE = 12_000
TEXT_TOTAL = 48_000
SHELL_TEXT = 80
MAX_BRIEF_LINKS = 30
MAX_BRIEF_IMAGES = 20
JSONLD_CHARS = 4_000
LINK_HINTS = (
    "register",
    "schedule",
    "faq",
    "track",
    "prize",
    "rule",
    "eligib",
    "timeline",
    "about",
    "submission",
    "hackathon",
)
BRIEF_LINK_HINTS = ("register", "submit", "prize", "faq", "rule", "schedule")
TIMEZONE_ALIASES = {
    "utc": "UTC",
    "gmt": "GMT",
    "india standard time": "Asia/Kolkata",
    "ist": "Asia/Kolkata",
}
MODE_ALIASES = {
    "virtual": "online",
    "remote": "online",
    "in person": "offline",
    "on site": "offline",
    "onsite": "offline",
}
PARTICIPATION_ALIASES = {
    "solo": "individual",
    "teams": "team",
}
DATE_FIELDS = ("registration_opens_at", "registration_closes_at", "submission_deadline")
SCALAR_FIELDS = (
    ("name", "Name"),
    ("organiser", "Organiser"),
    ("short_description", "Short description"),
    ("description", "Description"),
    ("problem_statements", "Problem statements"),
    ("official_website", "Official website"),
    ("organiser_logo_url", "Organiser logo"),
    ("banner_url", "Banner"),
    ("difficulty", "Difficulty"),
    ("participation_type", "Participation"),
    ("min_team_size", "Minimum team size"),
    ("max_team_size", "Maximum team size"),
    ("eligibility", "Eligibility"),
    ("academic_year", "Academic year"),
    ("degree_requirements", "Degree requirements"),
    ("geographic_restrictions", "Geographic restrictions"),
    ("other_eligibility", "Other eligibility"),
    ("mode", "Mode"),
    ("venue", "Venue"),
    ("location", "Location"),
    ("event_duration", "Duration"),
    ("registration_url", "Registration URL"),
    ("registration_opens_at", "Registration opens"),
    ("registration_closes_at", "Registration closes"),
    ("registration_instructions", "Registration instructions"),
    ("submission_url", "Submission URL"),
    ("submission_deadline", "Submission deadline"),
    ("required_deliverables", "Required deliverables"),
    ("submission_instructions", "Submission instructions"),
    ("prize_pool", "Prize pool"),
    ("first_prize", "First prize"),
    ("second_prize", "Second prize"),
    ("third_prize", "Third prize"),
    ("special_awards", "Special awards"),
    ("certificates", "Certificates"),
    ("internships", "Internships"),
    ("other_rewards", "Other rewards"),
    ("preparation_guidelines", "Preparation"),
    ("timezone", "Timezone"),
)
LIST_FIELDS = (
    ("themes", "Themes"),
    ("technologies", "Technologies"),
    ("tags", "Tags"),
    ("categories", "Categories"),
    ("tracks", "Tracks"),
    ("deliverables", "Deliverables"),
    ("prizes", "Prizes"),
    ("judging", "Judging criteria"),
    ("milestones", "Milestones"),
    ("resources", "Resources"),
    ("faqs", "FAQs"),
)
TEXT_LIMITS = {
    "name": 200,
    "organiser": 200,
    "short_description": 400,
    "academic_year": 120,
    "venue": 300,
    "location": 300,
    "event_duration": 120,
    "prize_pool": 200,
    "first_prize": 200,
    "second_prize": 200,
    "third_prize": 200,
}
URL_FIELDS = ("organiser_logo_url", "official_website", "banner_url", "registration_url", "submission_url")
PLAIN_FIELDS = (
    "description",
    "problem_statements",
    "eligibility",
    "degree_requirements",
    "geographic_restrictions",
    "other_eligibility",
    "registration_instructions",
    "required_deliverables",
    "submission_instructions",
    "special_awards",
    "certificates",
    "internships",
    "other_rewards",
    "preparation_guidelines",
)


def assert_public_http_url(url: str) -> str:
    try:
        cleaned = _http_url(url)
    except ValueError as exc:
        raise AppError(422, "invalid_url", "Enter an http or https URL") from exc
    if cleaned is None:
        raise AppError(422, "invalid_url", "Enter an http or https URL")
    parsed = urlparse(cleaned)
    host = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not host:
        raise AppError(422, "invalid_url", "Enter an http or https URL")
    if host.lower() == "localhost" or host.lower().endswith(".local"):
        raise AppError(422, "blocked_url", "That address cannot be imported")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    for address in _addresses(host, port):
        if _blocked(address):
            raise AppError(422, "blocked_url", "That address cannot be imported")
    return cleaned


def extract_from_url(settings: Settings, url: str) -> tuple[ImportProposal, list[str], list[str]]:
    cleaned = assert_public_http_url(url)
    if not settings.gemini_api_key.strip():
        raise AppError(503, "import_unconfigured", "Add a Gemini API key before importing.")
    pages, facts, visible = _fetch_pages(cleaned)
    if not any(text for _, text in pages):
        raise AppError(422, "empty_page", "That page did not include readable text.")
    if _is_shell(visible, facts):
        raise AppError(
            422,
            "page_shell",
            "That page is built in the browser, so its details are not in the downloaded HTML.",
        )
    raw = _fill_from_facts(_ask_gemini(settings, pages), facts)
    if not raw.get("official_website"):
        raw["official_website"] = cleaned
    raw["source_urls"] = [page_url for page_url, _ in pages]
    proposal = _proposal_from_raw(raw)
    return proposal, [page_url for page_url, _ in pages], missing_labels(proposal)


def commit_import(db: Session, settings: Settings, actor: User, proposal: ImportProposal):
    proposal = _proposal_from_raw(proposal.model_dump(mode="json"))
    name = proposal.name.strip()
    organiser = proposal.organiser.strip()
    if len(name) < 2:
        raise AppError(422, "missing_name", "Enter the hackathon name before saving")
    if len(organiser) < 2:
        raise AppError(422, "missing_organiser", "Enter the organiser before saving")
    hackathon = hackathons.create_hackathon(
        db,
        settings,
        actor,
        HackathonCreate(
            name=name,
            organiser=organiser,
            short_description=_clip(proposal.short_description, 400),
            timezone=proposal.timezone,
        ),
    )
    payload = _scalar_update(db, proposal)
    if payload:
        hackathon = hackathons.update_hackathon(db, actor, hackathon, HackathonUpdate.model_validate(payload))
    sources = "\n".join(proposal.source_urls)
    if sources:
        hackathon = hackathons.update_internal(db, actor, hackathon, InternalUpdate(source_urls=sources))
    for index, track in enumerate(proposal.tracks):
        content.add_track(db, actor, hackathon, TrackIn(name=track.name[:200], requirements=track.requirements, position=index))
    for index, item in enumerate(proposal.deliverables):
        content.add_deliverable(
            db,
            actor,
            hackathon,
            DeliverableIn(title=item.title[:200], detail=item.detail, required=item.required, position=index),
        )
    for index, item in enumerate(proposal.prizes):
        content.add_prize(db, actor, hackathon, PrizeIn(label=item.label[:200], detail=item.detail, position=index))
    for index, item in enumerate(proposal.judging):
        content.add_judging(
            db,
            actor,
            hackathon,
            JudgingIn(title=item.title[:200], detail=item.detail, weight=item.weight, position=index),
        )
    for index, item in enumerate(proposal.milestones):
        hackathons.add_milestone(
            db,
            actor,
            hackathon,
            MilestoneIn(
                title=item.title[:200],
                description=item.description,
                type=item.type,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                visibility="public",
                position=index,
            ),
        )
    for index, item in enumerate(proposal.resources):
        hackathons.add_resource(
            db, actor, hackathon, ResourceIn(title=item.title[:200], url=item.url, kind=item.kind, position=index)
        )
    for index, item in enumerate(proposal.faqs):
        content.add_faq(db, actor, hackathon, FaqIn(question=item.question[:300], answer=item.answer, position=index))
    db.expire_all()
    return hackathons.get_hackathon(db, hackathon.id)


def missing_labels(proposal: ImportProposal) -> list[str]:
    data = proposal.model_dump()
    missing = [label for key, label in SCALAR_FIELDS if data.get(key) in (None, "")]
    missing.extend(label for key, label in LIST_FIELDS if not data.get(key))
    return missing


def _scalar_update(db: Session, proposal: ImportProposal) -> dict:
    payload: dict = {}
    data = proposal.model_dump(exclude_none=True)
    for field in HackathonUpdate.model_fields:
        if field in {"category_ids", "labels", "featured"}:
            continue
        value = data.get(field)
        if value in (None, ""):
            continue
        payload[field] = value
    category_ids = _match_categories(proposal.categories)
    if category_ids:
        payload["category_ids"] = category_ids
    labels = [
        *({"name": name, "kind": "theme"} for name in proposal.themes),
        *({"name": name, "kind": "technology"} for name in proposal.technologies),
        *({"name": name, "kind": "tag"} for name in proposal.tags),
    ]
    if labels:
        payload["labels"] = labels
    return payload


def _match_categories(names: list[str]) -> list:
    rows = all_categories()
    by_name = {row["name"].casefold(): row["id"] for row in rows}
    by_slug = {row["slug"].casefold(): row["id"] for row in rows}
    chosen = []
    for name in names:
        key = name.casefold()
        found = by_name.get(key) or by_slug.get(key) or by_slug.get(slugify(name))
        if found is not None and found not in chosen:
            chosen.append(found)
    return chosen


def _proposal_from_raw(raw: dict) -> ImportProposal:
    data = dict(raw or {})
    base = _base_url(data)
    data["timezone"] = _timezone_or_none(data.get("timezone"))
    for field in DATE_FIELDS:
        data[field] = _date_or_none(data.get(field), data.get("timezone"))
    data["difficulty"] = _choice(data.get("difficulty"), DIFFICULTIES)
    data["participation_type"] = _choice(data.get("participation_type"), PARTICIPATION, PARTICIPATION_ALIASES)
    data["mode"] = _choice(data.get("mode"), MODES, MODE_ALIASES)
    data["min_team_size"] = _bounded_int(data.get("min_team_size"), 1, 100)
    data["max_team_size"] = _bounded_int(data.get("max_team_size"), 1, 100)
    for field in URL_FIELDS:
        data[field] = _resolve_url(data.get(field), base)
    for field, limit in TEXT_LIMITS.items():
        if isinstance(data.get(field), str):
            data[field] = _clip(data[field], limit)
    for field in PLAIN_FIELDS:
        value = data.get(field)
        data[field] = _blank(value) if isinstance(value, str) or value is None else None
    data["name"] = _clip(str(data.get("name") or ""), 200) or ""
    data["organiser"] = _clip(str(data.get("organiser") or ""), 200) or ""
    data["themes"] = _names(data.get("themes"))
    data["technologies"] = _names(data.get("technologies"))
    data["tags"] = _names(data.get("tags"))
    data["categories"] = _names(data.get("categories"))
    data["tracks"] = _rows(data.get("tracks"), ImportTrack, "name")
    data["deliverables"] = _rows(data.get("deliverables"), ImportDeliverable, "title")
    data["prizes"] = _rows(data.get("prizes"), ImportPrize, "label")
    data["judging"] = _judging(data.get("judging"))
    data["milestones"] = _milestones(data.get("milestones"), data.get("timezone"))
    data["resources"] = _resources(data.get("resources"), base)
    data["faqs"] = _faqs(data.get("faqs"))
    data["source_urls"] = [item for item in _names(data.get("source_urls"), limit=1000) if _url_or_none(item)]
    return ImportProposal.model_validate(data)


def _fetch_pages(url: str) -> tuple[list[tuple[str, str]], dict, str]:
    pages: list[tuple[str, str]] = []
    fact_rows: list[dict] = []
    seen: set[str] = set()
    visible = ""
    with httpx.Client(timeout=PAGE_TIMEOUT, headers={"User-Agent": "HackHub import"}) as client:
        final, text, raw, facts = _read_page(client, url)
        seen.add(final)
        pages.append((final, text[:TEXT_PER_PAGE]))
        fact_rows.append(facts)
        visible = _visible_text(raw)
        for link in _candidate_links(final, raw):
            if len(pages) >= MAX_EXTRA_PAGES + 1 or link in seen:
                continue
            try:
                linked, linked_text, _, linked_facts = _read_page(client, link)
            except AppError:
                continue
            seen.add(linked)
            if linked_text:
                pages.append((linked, linked_text[:TEXT_PER_PAGE]))
                fact_rows.append(linked_facts)
    budget = TEXT_TOTAL
    trimmed: list[tuple[str, str]] = []
    for page_url, text in pages:
        if budget <= 0:
            break
        trimmed.append((page_url, text[:budget]))
        budget -= len(text[:budget])
    return trimmed, _merge_facts(fact_rows), visible


def _read_page(client: httpx.Client, url: str) -> tuple[str, str, str, dict]:
    current = assert_public_http_url(url)
    for _ in range(4):
        with client.stream("GET", current, follow_redirects=False) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise AppError(422, "unreadable_page", "The official page could not be read.")
                current = assert_public_http_url(urljoin(current, location))
                continue
            if response.status_code >= 400:
                raise AppError(422, "unreadable_page", "The official page could not be read.")
            content_type = response.headers.get("content-type", "")
            body = _limited_body(response)
        if "html" not in content_type and "text" not in content_type:
            return current, "", "", {}
        raw = body.decode("utf-8", errors="ignore")
        document, facts = _page_document(current, raw)
        return current, document, raw, facts
    raise AppError(422, "unreadable_page", "The official page could not be read.")


def _limited_body(response: httpx.Response) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        room = MAX_BYTES - total
        if room <= 0:
            break
        chunks.append(chunk[:room])
        total += len(chunks[-1])
    return b"".join(chunks)


def _candidate_links(page_url: str, raw: str) -> list[str]:
    found: list[str] = []
    for href, text in _anchors(raw):
        joined = _absolute_http(page_url, href)
        if joined is None:
            continue
        parsed = urlparse(joined)
        if _host_key(parsed.hostname) != _host_key(urlparse(page_url).hostname):
            continue
        haystack = f"{parsed.path} {parsed.query} {text}".lower()
        if not any(hint in haystack for hint in LINK_HINTS):
            continue
        if joined not in found:
            found.append(joined)
        if len(found) >= MAX_EXTRA_PAGES:
            break
    return found


def _ask_gemini(settings: Settings, pages: list[tuple[str, str]]) -> dict:
    packed = "\n\n".join(f"URL: {page_url}\nTEXT: {text}" for page_url, text in pages if text)
    prompt = (
        "Extract public hackathon details for HackHub from the pages below. "
        "Use null when a fact is not stated. Do not invent dates, prizes, eligibility, results, winners, "
        "scores, participant lists, or judging outcomes. HackHub does not run this hackathon and cannot see private data. "
        "Return a date when the page states one. Include a timezone offset when the page states one. "
        "When the page names a timezone, return that timezone. Do not invent a timezone or an offset. "
        "When the page says virtual or remote, mode is online. When it says in-person or on-site, mode is offline. "
        "When it says solo, participation_type is individual. When it says teams, participation_type is team. "
        "mode is online, offline, or hybrid. difficulty is beginner, intermediate, or advanced. "
        "participation_type is individual, team, or both. "
        "milestone type is one of registration_opens, registration_closes, team_formation, idea_submission, "
        "prototype_submission, round_one, round_two, final_submission, grand_finale, results, workshop, meeting, other.\n\n"
        f"{packed}"
    )
    model = settings.gemini_model.strip() or "gemini-3.5-flash-lite"
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": _gemini_schema(),
            },
        },
        timeout=MODEL_TIMEOUT,
    )
    if response.status_code >= 400:
        raise _gemini_failure(response)
    try:
        text = _gemini_text(response.json())
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AppError(502, "import_failed", "The research service returned an unreadable result.") from exc
    if not isinstance(parsed, dict):
        raise AppError(502, "import_failed", "The research service returned an unreadable result.")
    return parsed


def _gemini_failure(response: httpx.Response) -> AppError:
    message = ""
    try:
        message = str(response.json().get("error", {}).get("message", ""))
    except ValueError:
        message = ""
    logger.info("Gemini extract failed: %s %s", response.status_code, message[:300])
    if "API key not valid" in message or "API_KEY_INVALID" in message:
        return AppError(
            502,
            "import_unconfigured",
            "The Gemini API key was rejected. Paste only the key from Google AI Studio, with nothing after it.",
        )
    return AppError(502, "import_failed", "The research service could not extract this page.")


def _gemini_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise ValueError("no candidates")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    texts = [part.get("text") for part in parts if isinstance(part, dict) and part.get("text") and not part.get("thought")]
    if not texts:
        raise ValueError("no text")
    return texts[-1]


def _gemini_schema() -> dict:
    text = {"type": ["string", "null"]}
    moment = {"type": ["string", "null"]}
    number = {"type": ["integer", "null"]}
    return {
        "type": "object",
        "properties": {
            "name": text,
            "organiser": text,
            "short_description": text,
            "description": text,
            "problem_statements": text,
            "official_website": text,
            "organiser_logo_url": text,
            "banner_url": text,
            "difficulty": text,
            "participation_type": text,
            "min_team_size": number,
            "max_team_size": number,
            "eligibility": text,
            "academic_year": text,
            "degree_requirements": text,
            "geographic_restrictions": text,
            "other_eligibility": text,
            "mode": text,
            "venue": text,
            "location": text,
            "event_duration": text,
            "registration_url": text,
            "registration_opens_at": moment,
            "registration_closes_at": moment,
            "registration_instructions": text,
            "submission_url": text,
            "submission_deadline": moment,
            "required_deliverables": text,
            "submission_instructions": text,
            "prize_pool": text,
            "first_prize": text,
            "second_prize": text,
            "third_prize": text,
            "special_awards": text,
            "certificates": text,
            "internships": text,
            "other_rewards": text,
            "preparation_guidelines": text,
            "timezone": text,
            "themes": {"type": "array", "items": {"type": "string"}},
            "technologies": {"type": "array", "items": {"type": "string"}},
            "tags": {"type": "array", "items": {"type": "string"}},
            "categories": {"type": "array", "items": {"type": "string"}},
            "tracks": {
                "type": "array",
                "items": {"type": "object", "properties": {"name": {"type": "string"}, "requirements": text}},
            },
            "deliverables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "detail": text, "required": {"type": "boolean"}},
                },
            },
            "prizes": {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string"}, "detail": text}}},
            "judging": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "detail": text, "weight": number},
                },
            },
            "milestones": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": text,
                        "type": {"type": "string"},
                        "starts_at": moment,
                        "ends_at": moment,
                    },
                },
            },
            "resources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "url": {"type": "string"}, "kind": {"type": "string"}},
                },
            },
            "faqs": {
                "type": "array",
                "items": {"type": "object", "properties": {"question": {"type": "string"}, "answer": {"type": "string"}}},
            },
        },
    }


def _page_document(page_url: str, raw: str) -> tuple[str, dict]:
    facts = _page_facts(page_url, raw)
    visible = _visible_text(raw)
    brief = _brief_text(facts)
    if len(brief) > TEXT_PER_PAGE:
        brief = brief[:TEXT_PER_PAGE]
    room = TEXT_PER_PAGE - len(brief)
    if brief and visible and room > 2:
        return f"{brief}\n\n{visible[: room - 2]}", facts
    return brief or visible[:TEXT_PER_PAGE], facts


def _page_facts(page_url: str, raw: str) -> dict:
    meta = _meta_map(raw)
    images = _images(page_url, raw)
    logo = next((image["url"] for image in images if _looks_like_logo(image)), None)
    event, jsonld_raw = _jsonld(page_url, raw)
    description = meta.get("description") or meta.get("og:description")
    visible = _visible_text(raw)
    return {
        "title": meta.get("og:title"),
        "description": description,
        "og_image": _absolute_http(page_url, meta.get("og:image")),
        "twitter_image": _absolute_http(page_url, meta.get("twitter:image")),
        "logo_url": logo,
        "images": images,
        "event": event,
        "jsonld_raw": jsonld_raw,
        "timezone": _named_timezone(visible, description or "", jsonld_raw),
        "links": _brief_links(page_url, raw),
    }


def _brief_text(facts: dict) -> str:
    lines = ["STRUCTURED FACTS FROM THE PAGE"]
    if facts.get("title"):
        lines.append(f"meta title: {facts['title']}")
    if facts.get("description"):
        lines.append(f"meta description: {facts['description']}")
    for label, key in (("banner image", "og_image"), ("banner image", "twitter_image"), ("organiser logo", "logo_url")):
        if facts.get(key):
            lines.append(f"{label}: {facts[key]}")
    for image in facts.get("images") or []:
        lines.append(
            f"image alt={image['alt']} class={image['class']} id={image['id']} url={image['url']}"
        )
    event = facts.get("event") or {}
    if any(event.values()):
        lines.append("json-ld event:")
        for key, value in event.items():
            if value:
                lines.append(f"  {key}: {value}")
    if facts.get("jsonld_raw"):
        lines.append("json-ld:")
        lines.append(facts["jsonld_raw"])
    if facts.get("timezone"):
        lines.append(f"named timezone: {facts['timezone']}")
    for link in facts.get("links") or []:
        lines.append(f"link: {link['text']} {link['url']}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _fill_from_facts(raw: dict, facts: dict) -> dict:
    data = dict(raw or {})
    event = facts.get("event") or {}

    def empty(key: str) -> bool:
        return data.get(key) in (None, "")

    if empty("name") and event.get("name"):
        data["name"] = event["name"]
    if empty("organiser") and event.get("organizer"):
        data["organiser"] = event["organizer"]
    stated_description = event.get("description") or facts.get("description")
    if empty("description") and stated_description:
        data["description"] = stated_description
    if empty("short_description") and (facts.get("description") or event.get("description")):
        data["short_description"] = facts.get("description") or event.get("description")
    if empty("location") and event.get("location"):
        data["location"] = event["location"]
    if empty("banner_url"):
        data["banner_url"] = facts.get("og_image") or facts.get("twitter_image") or event.get("image")
    if empty("organiser_logo_url") and facts.get("logo_url"):
        data["organiser_logo_url"] = facts["logo_url"]
    if empty("timezone") and facts.get("timezone"):
        data["timezone"] = facts["timezone"]
    if empty("registration_opens_at") and event.get("start_date"):
        data["registration_opens_at"] = event["start_date"]
    if empty("submission_deadline") and event.get("end_date"):
        data["submission_deadline"] = event["end_date"]
    return data


def _merge_facts(rows: list[dict]) -> dict:
    merged = {
        "title": None,
        "description": None,
        "og_image": None,
        "twitter_image": None,
        "logo_url": None,
        "images": [],
        "event": {},
        "jsonld_raw": "",
        "timezone": None,
        "links": [],
    }
    seen_images: set[str] = set()
    seen_links: set[str] = set()
    jsonld_parts: list[str] = []
    for row in rows:
        for key in ("title", "description", "og_image", "twitter_image", "logo_url", "timezone"):
            if not merged[key] and row.get(key):
                merged[key] = row[key]
        event = row.get("event") or {}
        for key, value in event.items():
            if value and not merged["event"].get(key):
                merged["event"][key] = value
        if row.get("jsonld_raw"):
            jsonld_parts.append(row["jsonld_raw"])
        for image in row.get("images") or []:
            if image["url"] not in seen_images:
                seen_images.add(image["url"])
                merged["images"].append(image)
        for link in row.get("links") or []:
            if link["url"] not in seen_links:
                seen_links.add(link["url"])
                merged["links"].append(link)
    merged["images"] = merged["images"][:MAX_BRIEF_IMAGES]
    merged["links"] = merged["links"][:MAX_BRIEF_LINKS]
    merged["jsonld_raw"] = "\n".join(jsonld_parts)[:JSONLD_CHARS]
    return merged


def _is_shell(visible: str, facts: dict) -> bool:
    if len(visible.strip()) >= SHELL_TEXT:
        return False
    event = facts.get("event") or {}
    return not any(
        (
            facts.get("description"),
            facts.get("og_image"),
            facts.get("twitter_image"),
            facts.get("logo_url"),
            facts.get("jsonld_raw"),
            event.get("name"),
            event.get("description"),
            event.get("start_date"),
        )
    )


def _visible_text(raw: str) -> str:
    without = re.sub(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>", " ", raw)
    without = re.sub(r"(?is)<[^>]+>", " ", without)
    return re.sub(r"\s+", " ", html.unescape(without)).strip()


def _meta_map(raw: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in re.finditer(r"(?is)<meta\b[^>]*>", raw):
        attrs = _attrs(match.group(0))
        key = (attrs.get("property") or attrs.get("name") or "").strip().lower()
        content = (attrs.get("content") or "").strip()
        if key and content and key not in found:
            found[key] = content
    return found


def _images(page_url: str, raw: str) -> list[dict]:
    images: list[dict] = []
    seen: set[str] = set()
    for match in re.finditer(r"(?is)<img\b[^>]*>", raw):
        attrs = _attrs(match.group(0))
        src = attrs.get("src") or _first_srcset(attrs.get("srcset"))
        url = _absolute_http(page_url, src)
        if url is None or url in seen:
            continue
        seen.add(url)
        images.append(
            {
                "url": url,
                "alt": attrs.get("alt") or "",
                "class": attrs.get("class") or "",
                "id": attrs.get("id") or "",
            }
        )
        if len(images) >= MAX_BRIEF_IMAGES:
            break
    return images


def _looks_like_logo(image: dict) -> bool:
    haystack = f"{image.get('alt', '')} {image.get('class', '')} {image.get('id', '')}".lower()
    return "logo" in haystack


def _jsonld(page_url: str, raw: str) -> tuple[dict, str]:
    blocks = [
        html.unescape(match.group(1)).strip()
        for match in re.finditer(
            r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
            raw,
        )
        if match.group(1).strip()
    ]
    event: dict = {}
    for block in blocks:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        node = _event_node(payload)
        if node is None:
            continue
        event = {
            "name": _text_value(node.get("name")),
            "description": _text_value(node.get("description")),
            "location": _place(node.get("location")),
            "organizer": _party(node.get("organizer") or node.get("organiser")),
            "image": _image_url(page_url, node.get("image")),
            "start_date": _text_value(node.get("startDate")),
            "end_date": _text_value(node.get("endDate")),
        }
        break
    return event, "\n".join(blocks)[:JSONLD_CHARS]


def _event_node(payload) -> dict | None:
    found: list[dict] = []
    seen: set[int] = set()

    def walk(node) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict) or id(node) in seen:
            return
        seen.add(id(node))
        if _is_event(node):
            found.append(node)
            return
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    walk(payload)
    return found[0] if found else None


def _is_event(node: dict) -> bool:
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    for item in kinds:
        if not isinstance(item, str):
            continue
        name = item.rsplit("/", 1)[-1].casefold()
        if name == "event" or name.endswith("event"):
            return True
    return False


def _text_value(value) -> str | None:
    if isinstance(value, str):
        cleaned = _visible_text(value)
        return cleaned or None
    if isinstance(value, dict):
        return _text_value(value.get("name") or value.get("@value"))
    return None


def _place(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = [part for part in (_place(item) for item in value) if part]
        return ", ".join(parts) or None
    if isinstance(value, dict):
        parts: list[str] = []
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            parts.append(name.strip())
        address = value.get("address")
        if isinstance(address, str) and address.strip() and address.strip() not in parts:
            parts.append(address.strip())
        elif isinstance(address, dict):
            bits = [
                address.get(key)
                for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")
            ]
            line = ", ".join(bit.strip() for bit in bits if isinstance(bit, str) and bit.strip())
            if line and line not in parts:
                parts.append(line)
        return ", ".join(parts) or None
    return None


def _party(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = [part for part in (_party(item) for item in value) if part]
        return ", ".join(parts) or None
    if isinstance(value, dict):
        return _text_value(value.get("name"))
    return None


def _image_url(page_url: str, value) -> str | None:
    if isinstance(value, str):
        return _absolute_http(page_url, value)
    if isinstance(value, list):
        for item in value:
            found = _image_url(page_url, item)
            if found:
                return found
    if isinstance(value, dict):
        return _image_url(page_url, value.get("url") or value.get("contentUrl"))
    return None


def _brief_links(page_url: str, raw: str) -> list[dict]:
    hinted: list[dict] = []
    same_host: list[dict] = []
    seen: set[str] = set()
    page_host = _host_key(urlparse(page_url).hostname)
    for href, text in _anchors(raw):
        url = _absolute_http(page_url, href)
        if url is None or url in seen:
            continue
        parsed = urlparse(url)
        haystack = f"{parsed.path} {parsed.query} {text}".lower()
        item = {"text": text, "url": url}
        if any(hint in haystack for hint in BRIEF_LINK_HINTS):
            seen.add(url)
            hinted.append(item)
        elif _host_key(parsed.hostname) == page_host:
            seen.add(url)
            same_host.append(item)
    return (hinted + same_host)[:MAX_BRIEF_LINKS]


def _anchors(raw: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for match in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", raw):
        href = _attrs(match.group(1)).get("href", "").strip()
        if not href or href.startswith("#"):
            continue
        rows.append((href, _visible_text(match.group(2))))
    return rows


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in re.finditer(r"""(?is)([:@\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", tag):
        value = match.group(2) if match.group(2) is not None else match.group(3)
        attrs[match.group(1).lower()] = html.unescape(value or "")
    return attrs


def _first_srcset(value: str | None) -> str | None:
    if not value:
        return None
    first = value.split(",")[0].strip().split()
    return first[0] if first else None


def _named_timezone(*chunks: str) -> str | None:
    blob = "\n".join(chunk for chunk in chunks if chunk)
    match = re.search(r"\b(India Standard Time|IST|UTC|GMT)\b", blob, flags=re.I)
    if match is None:
        return None
    return TIMEZONE_ALIASES[match.group(1).casefold()]


def _absolute_http(page_url: str, value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = html.unescape(value).strip()
    if not cleaned or cleaned.startswith(("data:", "javascript:", "mailto:")):
        return None
    if cleaned.startswith("//"):
        cleaned = f"https:{cleaned}"
    elif not cleaned.startswith(("http://", "https://")):
        cleaned = urljoin(page_url, cleaned)
    return _url_or_none(cleaned.split("#", 1)[0])


def _addresses(host: str, port: int) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        return [literal]
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            infos = pool.submit(socket.getaddrinfo, host, port, socket.AF_UNSPEC, socket.SOCK_STREAM).result(timeout=5)
    except (socket.gaierror, TimeoutError, OSError) as exc:
        raise AppError(422, "invalid_url", "That host could not be resolved") from exc
    return [ipaddress.ip_address(info[4][0]) for info in infos]


def _blocked(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _host_key(host: str | None) -> str:
    if not host:
        return ""
    lowered = host.lower()
    return lowered[4:] if lowered.startswith("www.") else lowered


def _clip(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    clipped = value.strip()
    if not clipped:
        return None
    return clipped[:limit]


def _names(value, limit: int = 80) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned and cleaned not in names:
            names.append(cleaned[:limit])
    return names


def _rows(value, model, required: str) -> list:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get(required) or "").strip()
        if not label:
            continue
        payload = {required: label[:200]}
        extra = "requirements" if required == "name" else "detail"
        if extra in model.model_fields:
            payload[extra] = _blank(item.get(extra)) if isinstance(item.get(extra), str) or item.get(extra) is None else None
        if required == "title" and "required" in model.model_fields:
            payload["required"] = bool(item.get("required", True))
        rows.append(model.model_validate(payload))
    return rows


def _judging(value) -> list[ImportJudging]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        rows.append(
            ImportJudging(title=title[:200], detail=_blank(item.get("detail")) if isinstance(item.get("detail"), str) or item.get("detail") is None else None, weight=_bounded_int(item.get("weight"), 0, 100))
        )
    return rows


def _milestones(value, timezone_name: str | None = None) -> list[ImportMilestone]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        raw_kind = item.get("type")
        kind = raw_kind.strip().casefold() if isinstance(raw_kind, str) else ""
        if kind not in MILESTONE_TYPES:
            kind = "other"
        start = _date_or_none(item.get("starts_at"), timezone_name)
        end = _date_or_none(item.get("ends_at"), timezone_name)
        if start and end and end < start:
            end = None
        description = item.get("description")
        rows.append(
            ImportMilestone(
                title=title[:200],
                description=_blank(description) if isinstance(description, str) or description is None else None,
                type=kind,
                starts_at=start,
                ends_at=end,
            )
        )
    return rows


def _resources(value, base: str | None = None) -> list[ImportResource]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = _resolve_url(item.get("url"), base)
        raw_kind = item.get("kind")
        kind = raw_kind.strip().casefold() if isinstance(raw_kind, str) else ""
        if kind not in RESOURCE_KINDS:
            kind = "other"
        if not title or url is None:
            continue
        rows.append(ImportResource(title=title[:200], url=url, kind=kind))
    return rows


def _faqs(value) -> list[ImportFaq]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if question and answer:
            rows.append(ImportFaq(question=question[:300], answer=answer))
    return rows


def _date_or_none(value, timezone_name: str | None = None):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        if not timezone_name:
            return None
        try:
            return parsed.replace(tzinfo=ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            return None
    return parsed


def _timezone_or_none(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = TIMEZONE_ALIASES.get(value.strip().casefold(), value.strip())
    try:
        return _timezone(cleaned)
    except ValueError:
        return None


def _choice(value, allowed: set[str], aliases: dict[str, str] | None = None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    phrase = re.sub(r"[\s_-]+", " ", value.strip().casefold())
    if aliases and phrase in aliases:
        return aliases[phrase]
    if phrase in allowed:
        return phrase
    return None


def _base_url(data: dict) -> str | None:
    candidates = [data.get("official_website")]
    sources = data.get("source_urls")
    if isinstance(sources, list):
        candidates.extend(sources)
    for item in candidates:
        if isinstance(item, str) and item.strip().startswith(("http://", "https://")):
            return item.strip()
    return None


def _resolve_url(value, base: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith("//"):
        cleaned = f"https:{cleaned}"
    elif base and not cleaned.startswith(("http://", "https://")):
        cleaned = urljoin(base, cleaned)
    return _url_or_none(cleaned)


def _bounded_int(value, low: int, high: int) -> int | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < low or number > high:
        return None
    return number


def _url_or_none(value) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return _http_url(value)
    except ValueError:
        return None
