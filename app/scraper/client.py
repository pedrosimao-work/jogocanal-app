"""Reusable async transport with bounded retries and source-neutral errors."""

import asyncio
import ssl
from datetime import date
from types import TracebackType

import httpx

from app.scraper.exceptions import ScheduleSourceRequestError
from app.scraper.parsers import parse_club_schedule, parse_daily_schedule
from app.scraper.schemas import ScheduleSourceConfig, ScrapedMatch


class ScheduleSourceClient:
    def __init__(
        self,
        config: ScheduleSourceConfig,
        *,
        timeout: float = 20,
        retries: int = 2,
        retry_delay: float = 0.5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if timeout <= 0 or not 0 <= retries <= 5 or retry_delay < 0:
            raise ValueError("Invalid HTTP timeout or retry settings")
        self.config = config
        self.retries = retries
        self.retry_delay = retry_delay
        self._client = httpx.AsyncClient(
            verify=ssl.create_default_context(),
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
            max_redirects=5,
            headers={"User-Agent": "JogoCanal/0.1", "Accept": "text/html"},
        )

    async def __aenter__(self) -> "ScheduleSourceClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def fetch_html(self, url: str) -> str:
        for attempt in range(self.retries + 1):
            retryable = False
            try:
                response = await self._client.get(url)
                retryable = response.status_code in {429, 500, 502, 503, 504}
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if (
                    content_type not in {"text/html", "application/xhtml+xml"}
                    or not response.text.strip()
                ):
                    raise ScheduleSourceRequestError("Schedule response was not nonempty HTML")
                return response.text
            except (httpx.TimeoutException, httpx.NetworkError):
                retryable = True
            except (httpx.HTTPError, httpx.InvalidURL):
                pass
            if not retryable or attempt == self.retries:
                break
            await asyncio.sleep(self.retry_delay * (2**attempt))
        raise ScheduleSourceRequestError("Schedule request failed") from None

    async def daily_schedule(self, *, reference_date: date) -> tuple[ScrapedMatch, ...]:
        html = await self.fetch_html(str(self.config.homepage_url))
        return parse_daily_schedule(html, self.config.selectors, reference_date=reference_date)

    async def club_schedule(
        self,
        url: str,
        *,
        reference_date: date,
    ) -> tuple[ScrapedMatch, ...]:
        html = await self.fetch_html(url)
        return parse_club_schedule(html, self.config.selectors, reference_date=reference_date)
