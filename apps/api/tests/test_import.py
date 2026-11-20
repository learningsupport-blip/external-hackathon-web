import pytest

from datetime import timedelta

from app.errors import AppError
from app.services.importing import (
    _candidate_links,
    _fill_from_facts,
    _is_shell,
    _page_document,
    _proposal_from_raw,
    assert_public_http_url,
)
from tests.test_core import login


def test_import_rejects_local_and_private_urls():
    with pytest.raises(AppError) as local:
        assert_public_http_url("http://localhost/hack")
    assert local.value.code == "blocked_url"
    with pytest.raises(AppError):
        assert_public_http_url("http://127.0.0.1/hack")
    with pytest.raises(AppError):
        assert_public_http_url("http://10.1.2.3/hack")
    with pytest.raises(AppError) as scheme:
        assert_public_http_url("file:///tmp/hack")
    assert scheme.value.code == "invalid_url"


def test_import_saves_a_draft_and_drops_unknown_fields(client):
    login(client, "admin@hackhub.test")
    created = client.post(
        "/api/v1/admin/hackathons/import",
        json={
            "proposal": {
                "name": "River Open",
                "organiser": "River Org",
                "short_description": "Build beside the river.",
                "mode": "in-person",
                "submission_deadline": None,
                "official_website": "https://example.com/river",
                "categories": ["AI/ML", "Not a real category"],
                "tracks": [{"name": "Cleanup", "requirements": "A working prototype"}],
                "source_urls": ["https://example.com/river"],
            }
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["lifecycle"] == "draft"
    assert body["mode"] == "offline"
    assert body["submission_deadline"] is None
    assert body["tracks"][0]["name"] == "Cleanup"
    assert [item["slug"] for item in body["categories"]] == ["ai-ml"]
    assert body["internal"]["verification_status"] == "unverified"
    assert "https://example.com/river" in body["internal"]["source_urls"]

    hidden = client.get(f"/api/v1/hackathons/{body['slug']}")
    assert hidden.status_code == 404


SAMPLE_PAGE = """
<html><head>
<meta name="description" content="Build tools for the river.">
<meta property="og:image" content="//cdn.example.com/banner.jpg">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"River Hack","startDate":"2026-05-01T09:00:00+05:30","location":"Chennai","organizer":{"@type":"Organization","name":"River Org"}}
</script>
</head>
<body>
<img id="organiser-logo" src="/logo.png" alt="River Org logo">
<a href="/p/991">Prizes</a>
<p>Join the weekend build beside the river in Chennai.</p>
</body></html>
"""


def test_page_brief_keeps_stated_facts():
    page = "https://example.com/hack"
    document, facts = _page_document(page, SAMPLE_PAGE)
    assert "Build tools for the river." in document
    assert "2026-05-01T09:00:00+05:30" in document
    assert "https://example.com/logo.png" in document
    assert facts["logo_url"] == "https://example.com/logo.png"
    assert facts["og_image"] == "https://cdn.example.com/banner.jpg"
    assert _candidate_links(page, SAMPLE_PAGE) == ["https://example.com/p/991"]
    filled = _fill_from_facts({"banner_url": "https://example.com/keep.jpg", "name": ""}, facts)
    assert filled["banner_url"] == "https://example.com/keep.jpg"
    assert filled["name"] == "River Hack"
    assert filled["organiser_logo_url"] == "https://example.com/logo.png"
    assert filled["short_description"] == "Build tools for the river."
    assert _is_shell("Loading", {}) is True
    assert _is_shell("Loading", facts) is False


def test_stated_date_keeps_page_timezone_and_drops_a_bare_date():
    kept = _proposal_from_raw(
        {"timezone": "Asia/Kolkata", "registration_opens_at": "2026-04-01T09:00:00"}
    )
    assert kept.timezone == "Asia/Kolkata"
    assert kept.registration_opens_at is not None
    assert kept.registration_opens_at.utcoffset() == timedelta(hours=5, minutes=30)

    bare = _proposal_from_raw({"registration_opens_at": "2026-04-01T09:00:00"})
    assert bare.registration_opens_at is None
    assert bare.timezone is None


def test_date_only_jsonld_uses_a_timezone_the_page_names():
    raw = """
    <html><head>
    <script type="application/ld+json">
    {"@type":"Event","name":"River Hack","startDate":"2026-05-01T09:00:00"}
    </script>
    </head><body><p>Schedule times are IST. This weekend hackathon is open to students across India.</p></body></html>
    """
    _, facts = _page_document("https://example.com/hack", raw)
    proposal = _proposal_from_raw(_fill_from_facts({}, facts))
    assert proposal.timezone == "Asia/Kolkata"
    assert proposal.registration_opens_at is not None
    assert proposal.registration_opens_at.utcoffset() == timedelta(hours=5, minutes=30)


def test_relative_banner_resolves_against_the_official_page():
    proposal = _proposal_from_raw(
        {"official_website": "https://example.com/hack", "banner_url": "/banner.png"}
    )
    assert proposal.banner_url == "https://example.com/banner.png"


def test_stated_phrases_are_kept_and_unknown_values_stay_empty():
    proposal = _proposal_from_raw(
        {
            "name": "River Open",
            "organiser": "River Org",
            "mode": "in-person",
            "difficulty": "expert",
            "participation_type": "teams",
            "resources": [{"title": "Deck", "url": "https://example.com/slides", "kind": "slides"}],
            "milestones": [{"title": "Kickoff", "type": "kickoff"}],
        }
    )
    assert proposal.mode == "offline"
    assert proposal.difficulty is None
    assert proposal.participation_type == "team"
    assert proposal.resources[0].kind == "other"
    assert proposal.milestones[0].type == "other"


def test_sheet_row_round_trips_prizes_and_faqs():
    from app.services.sheets import SHEET_HEADER, cells_to_proposal, proposal_to_cells

    proposal = _proposal_from_raw(
        {
            "name": "River Open",
            "organiser": "River Org",
            "prizes": [
                {"label": "Gold", "detail": "A laptop"},
                {"label": "Silver", "detail": "A keyboard"},
            ],
            "faqs": [{"question": "Who can join?", "answer": "Students"}],
        }
    )
    cells = proposal_to_cells(proposal, source_url="https://example.com/hack")
    assert "\n" in cells[SHEET_HEADER.index("prizes")]
    again = cells_to_proposal(cells)
    assert [(item.label, item.detail) for item in again.prizes] == [("Gold", "A laptop"), ("Silver", "A keyboard")]
    assert [(item.question, item.answer) for item in again.faqs] == [("Who can join?", "Students")]
    assert again.source_urls == ["https://example.com/hack"]


def test_sheet_date_uses_the_timezone_column():
    from app.services.sheets import SHEET_HEADER, cells_to_proposal

    cells = [""] * len(SHEET_HEADER)
    cells[SHEET_HEADER.index("timezone")] = "Asia/Kolkata"
    cells[SHEET_HEADER.index("registration_opens_at")] = "2026-04-01 09:00"
    kept = cells_to_proposal(cells)
    assert kept.timezone == "Asia/Kolkata"
    assert kept.registration_opens_at is not None
    assert kept.registration_opens_at.utcoffset() == timedelta(hours=5, minutes=30)

    cells[SHEET_HEADER.index("timezone")] = ""
    bare = cells_to_proposal(cells)
    assert bare.registration_opens_at is None
    assert bare.timezone is None


def test_sheet_maps_stated_mode_and_drops_unknown_difficulty():
    from app.services.sheets import SHEET_HEADER, cells_to_proposal

    cells = [""] * len(SHEET_HEADER)
    cells[SHEET_HEADER.index("mode")] = "in-person"
    cells[SHEET_HEADER.index("difficulty")] = "expert"
    proposal = cells_to_proposal(cells)
    assert proposal.mode == "offline"
    assert proposal.difficulty is None


def test_ready_sheet_row_without_a_name_is_skipped():
    from app.services.sheets import SHEET_HEADER, assert_sheet_id, classify_sheet

    cells = [""] * len(SHEET_HEADER)
    cells[SHEET_HEADER.index("ready")] = "yes"
    cells[SHEET_HEADER.index("organiser")] = "River Org"
    classified = classify_sheet([list(SHEET_HEADER), cells])
    assert classified.ready == []
    assert classified.skipped[0].row == 2

    with pytest.raises(AppError) as caught:
        assert_sheet_id("https://docs.google.com/spreadsheets/d/abc")
    assert caught.value.code == "invalid_sheet"


def test_a_label_in_hackathon_id_is_still_ready():
    from app.services.sheets import SHEET_HEADER, classify_sheet

    cells = [""] * len(SHEET_HEADER)
    cells[SHEET_HEADER.index("ready")] = "yes"
    cells[SHEET_HEADER.index("hackathon_id")] = "ODSC-NEBIUS-2026"
    cells[SHEET_HEADER.index("name")] = "River Open"
    cells[SHEET_HEADER.index("organiser")] = "River Org"
    classified = classify_sheet([list(SHEET_HEADER), cells])
    assert classified.skipped == []
    assert len(classified.ready) == 1

