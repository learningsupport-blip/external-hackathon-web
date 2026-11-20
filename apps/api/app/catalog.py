"""Fixed hackathon categories. Stored on each event, not in a table."""

import uuid

_NAMESPACE = uuid.UUID("6f0d6e0a-7c1e-4c3a-9b2d-4e5f1a2b3c4d")

FIXED_CATEGORIES = (
    ("AI/ML", "ai-ml"),
    ("Web Development", "web-development"),
    ("Open Source", "open-source"),
    ("Cloud Computing", "cloud-computing"),
    ("Cybersecurity", "cybersecurity"),
    ("Sustainability", "sustainability"),
    ("Social Impact", "social-impact"),
    ("Robotics", "robotics"),
    ("Product Development", "product-development"),
    ("Other", "other"),
)


def category_id(slug: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"hackhub:category:{slug}")


def all_categories() -> list[dict]:
    return [{"id": category_id(slug), "name": name, "slug": slug} for name, slug in FIXED_CATEGORIES]


def category_by_id(value: uuid.UUID) -> dict | None:
    for item in all_categories():
        if item["id"] == value:
            return item
    return None
