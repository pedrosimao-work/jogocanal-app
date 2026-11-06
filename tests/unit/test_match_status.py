from datetime import UTC, datetime, timedelta

import pytest

from app.services.schedule import public_status


@pytest.mark.parametrize(
    "raw,minutes,expected",
    [
        ("live", -10, "AO VIVO"),
        ("postponed", -300, "ADIADO"),
        ("finished", -100, "TERMINADO"),
        (None, 30, "A SEGUIR"),
        (None, 90, "AGENDADO"),
        (None, -130, "POR CONFIRMAR"),
        ("untrusted status", -1, "POR CONFIRMAR"),
    ],
)
def test_status_does_not_invent_live_or_finished(raw, minutes, expected):
    now = datetime(2026, 11, 6, 12, tzinfo=UTC)
    assert public_status(raw, now + timedelta(minutes=minutes), now)[1] == expected
