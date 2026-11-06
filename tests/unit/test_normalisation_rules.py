import json

import httpx
import pytest
from pydantic import SecretStr

from app.services.groq_normalisation import GroqNormaliser
from app.services.normalisation import lookup_key


@pytest.mark.parametrize(
    "body",
    [
        {"choices": [None]},
        {"choices": []},
        {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
    ],
)
async def test_bad_response_envelope(body: dict) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    async with GroqNormaliser(SecretStr("test-key"), "test-model", transport=transport) as fallback:
        assert await fallback.suggest("club", "Unknown") is None


async def test_timeout_preserves_unknown_name() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async with GroqNormaliser(
        SecretStr("test-key"), "test-model", transport=httpx.MockTransport(handler)
    ) as fallback:
        assert await fallback.suggest("club", "Unknown") is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  VITÓRIA   Guimarães ", "vitoria guimaraes"),
        ("U. Leiria", "u leiria"),
        ("AVS - Futebol SAD", "avs futebol sad"),
        ("Benfica B", "benfica b"),
        ("SPORT TV 2", "sport tv 2"),
        ("CANAL+", "canal+"),
    ],
)
def test_lookup_rules(raw: str, expected: str) -> None:
    assert lookup_key(raw) == expected


async def test_groq_request_and_validated_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        assert json.loads(payload["messages"][1]["content"]) == {
            "context": "club",
            "name": "Unknown",
        }
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"canonical_name":"Example FC"}'},
                    }
                ]
            },
        )

    async with GroqNormaliser(
        SecretStr("test-key"), "test-model", transport=httpx.MockTransport(handler)
    ) as fallback:
        assert await fallback.suggest("club", "Unknown") == "Example FC"


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "{}",
        '{"canonical_name":""}',
        '{"canonical_name":42}',
        '{"canonical_name":null}',
        '{"canonical_name":"Name", "extra":true}',
    ],
)
async def test_invalid_or_uncertain_groq_responses(content: str) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": content}}],
            },
        )
    )
    async with GroqNormaliser(SecretStr("test-key"), "test-model", transport=transport) as fallback:
        assert await fallback.suggest("channel", "Unknown") is None


@pytest.mark.parametrize("status", [401, 429, 500])
async def test_groq_outages_fail_open(status: int) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    async with GroqNormaliser(SecretStr("test-key"), "test-model", transport=transport) as fallback:
        assert await fallback.suggest("club", "Unknown") is None
