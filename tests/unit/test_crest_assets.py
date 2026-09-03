from pathlib import Path  # Import Path so test asset paths remain operating-system independent

from app.data.reference import (
    CLUB_SEEDS,
)  # Import every canonical club and its configured crest path

PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)  # Resolve the repository root from this unit-test file
STATIC_ROOT = PROJECT_ROOT / "app" / "static"  # Resolve the application's local static directory


def test_every_tracked_club_has_a_local_crest() -> (
    None
):  # Verify that no canonical club points to a missing public asset
    for club in CLUB_SEEDS:  # Check every current professional club
        crest_file = (
            STATIC_ROOT / club.crest_path
        )  # Resolve the configured crest path on the local filesystem

        assert crest_file.is_file(), (
            f"Missing crest for {club.name}: {crest_file}"
        )  # Fail with the exact missing club and path
