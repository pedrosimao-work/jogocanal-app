from app.data.reference import (
    ALIAS_SEEDS,
    CLUB_SEEDS,
    LEAGUE_SEEDS,
)  # Import the complete canonical reference-data definitions


def test_reference_data_contains_36_unique_clubs() -> (
    None
):  # Verify the seed contains exactly the two current professional divisions
    club_slugs = [club.slug for club in CLUB_SEEDS]  # Collect every canonical club identifier

    assert len(CLUB_SEEDS) == 36  # Require exactly 36 tracked current professional clubs
    assert len(club_slugs) == len(set(club_slugs))  # Prevent duplicate canonical club slugs


def test_each_current_league_contains_18_unique_clubs() -> (
    None
):  # Verify the confirmed current league membership sizes
    for league in LEAGUE_SEEDS:  # Check each professional league independently
        assert len(league.club_slugs) == 18  # Require exactly 18 current clubs in each league
        assert len(league.club_slugs) == len(
            set(league.club_slugs)
        )  # Prevent duplicate memberships inside one league


def test_every_membership_references_a_canonical_club() -> (
    None
):  # Ensure every league membership points to known seed data
    canonical_slugs = {
        club.slug for club in CLUB_SEEDS
    }  # Build the complete canonical club identifier set
    membership_slugs = {
        slug for league in LEAGUE_SEEDS for slug in league.club_slugs
    }  # Collect clubs referenced by league membership

    assert (
        membership_slugs == canonical_slugs
    )  # Require every club to belong to exactly one current tracked league


def test_current_2026_2027_roster_corrections_are_preserved() -> (
    None
):  # Protect the officially confirmed roster corrections from regression
    leagues = {
        league.slug: set(league.club_slugs) for league in LEAGUE_SEEDS
    }  # Build easy league-membership lookup sets

    assert (
        "fc-arouca" in leagues["liga-portugal-betclic"]
    )  # Keep FC Arouca in the current first tier
    assert (
        "estrela-amadora" in leagues["liga-portugal-betclic"]
    )  # Keep Estrela Amadora in the current first tier
    assert (
        "sc-farense" not in leagues["liga-portugal-betclic"]
    )  # Prevent the previous outdated Farense first-tier entry
    assert (
        "sc-farense" in leagues["liga-portugal-2-meu-super"]
    )  # Keep Farense in the confirmed current second tier
    assert (
        "academica" in leagues["liga-portugal-2-meu-super"]
    )  # Keep promoted Académica in the second tier
    assert (
        "amarante" in leagues["liga-portugal-2-meu-super"]
    )  # Keep promoted Amarante in the second tier


def test_normalized_aliases_are_globally_unique() -> (
    None
):  # Protect the database's global normalized-alias uniqueness constraint
    normalized_aliases = [
        alias.normalized_alias for alias in ALIAS_SEEDS
    ]  # Collect every deterministic alias lookup key

    assert len(normalized_aliases) == len(
        set(normalized_aliases)
    )  # Prevent two alias rows from competing for one normalized lookup key
