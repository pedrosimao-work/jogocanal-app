import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.commands.seed_reference_data import load_source_mappings
from app.data.reference import CLUB_SEEDS_BY_SLUG

EXAMPLE = Path(__file__).resolve().parents[2] / "private/source_mappings.example.json"


def test_public_mapping_example_is_valid() -> None:
    mappings = load_source_mappings(EXAMPLE)
    assert len(mappings) == 1
    mapping = mappings[0]
    assert mapping.club_slug in CLUB_SEEDS_BY_SLUG
    assert mapping.provider_key == "primary_schedule"
    assert mapping.source_url.host == "example.invalid"
    assert mapping.source_slug == "replace-with-private-source-identifier"


def test_mappings_are_optional() -> None:
    assert load_source_mappings(None) == ()


def test_duplicate_club_provider_mappings_are_rejected(tmp_path: Path) -> None:
    records = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    path = tmp_path / "mappings.json"
    path.write_text(json.dumps(records + records), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate club/provider"):
        load_source_mappings(path)


def test_missing_source_url_is_rejected(tmp_path: Path) -> None:
    records = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    del records[0]["source_url"]
    path = tmp_path / "mappings.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    with pytest.raises(ValidationError) as error:
        load_source_mappings(path)
    assert error.value.errors()[0]["loc"] == (0, "source_url")
