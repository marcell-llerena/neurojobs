from abc import ABC
from abc import abstractmethod
from functools import partial
from types import TracebackType
from typing import Self

from aiohttp import ClientSession
from aiohttp import ClientTimeout
from aiometer import run_all
from fake_headers import Headers
from loguru import logger
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from neurojobs.scrapers.config import ScraperConfig
from neurojobs.scrapers.schemas import JobSearchParams
from neurojobs.scrapers.schemas import RawJobPostings
from neurojobs.scrapers.schemas import ScraperResponse
from neurojobs.scrapers.schemas import ScraperResponses


class BaseScraper(ABC):
    """Abstract base class for job posting scrapers.

    Provides common infrastructure for HTTP-based scraping including session
    management, retry logic, concurrent request handling, and error
    recovery. Subclasses implement source-specific parsing logic in the
    scrape() method.

    Attributes:
        _config: Scraper configuration for timeouts, retries, and
            concurrency limits.
        _headers: Fake headers generator for request anonymization.
        _session: Async HTTP session (initialized in __aenter__).
        _retry: Tenacity retry decorator for automatic retry logic.
    """

    def __init__(self, config: ScraperConfig | None = None) -> None:
        self._config = config or ScraperConfig()
        self._headers = Headers()
        self._session: ClientSession | None = None
        self._retry = retry(
            stop=stop_after_attempt(self._config.max_retries + 1),
            wait=wait_exponential(
                multiplier=self._config.retry_multiplier,
                min=self._config.retry_wait_min,
                max=self._config.retry_wait_max,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )

    async def __aenter__(self) -> Self:
        """Initialize async HTTP session for scraping operations.

        Creates an aiohttp ClientSession with configured timeout. Must be
        called before using scraper methods.

        Returns:
            Self for use as async context manager.
        """
        self._session = ClientSession(
            timeout=ClientTimeout(total=self._config.request_timeout), trust_env=True
        )
        logger.info("Initialized scraper session")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Clean up HTTP session resources.

        Closes the aiohttp session and cleans up connections. Called
        automatically when exiting async context manager.
        """
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Closed scraper session")

    async def _request(
        self, url: str | list[str], method: str = "GET"
    ) -> ScraperResponses:
        """Execute HTTP request(s) with concurrency control and retry logic.

        Handles single or batch URL requests using aiometer for rate
        limiting and concurrency. Applies retry decorator to individual
        requests. Returns successful responses only.

        Args:
            url: Single URL string or list of URLs to fetch.
            method: HTTP method (defaults to "GET").

        Returns:
            ScraperResponses object containing successful response
            objects. Failed requests are filtered out.
        """
        urls = [url] if isinstance(url, str) else url

        logger.info("Fetching {} URLs with method {}", len(urls), method)
        requests = [partial(self._fetch_single_url, url, method) for url in urls]

        responses = await run_all(
            requests,
            max_at_once=self._config.max_concurrent_requests,
            max_per_second=self._config.max_requests_per_minute / 60,
        )

        successful_responses = [
            response for response in responses if response is not None
        ]
        success_rate = (len(successful_responses) / len(urls) * 100) if urls else 0.0
        logger.info("Success rate: {:.2f}%", success_rate)

        return ScraperResponses(items=successful_responses)

    async def _fetch_single_url(self, url: str, method: str) -> ScraperResponse | None:
        """Fetch a single URL with retry logic and error handling.

        Executes HTTP request with automatic retries on failure. Returns
        None if all retries are exhausted, allowing batch operations to
        continue with partial success.

        Args:
            url: URL to fetch.
            method: HTTP method to use.

        Returns:
            ScraperResponse object on success, None on failure after
            retries exhausted.
        """

        @self._retry
        async def _execute_request() -> ScraperResponse:
            if not self._session:
                raise RuntimeError("Scraper session not initialized")

            logger.debug("{} {}", method, url)
            async with self._session.request(
                method, url, headers=self._headers.generate()
            ) as response:
                response.raise_for_status()
                content = await response.text()
                logger.debug("Successfully fetched {}", url)
                return ScraperResponse(url=url, status=response.status, content=content)

        try:
            return await _execute_request()
        except Exception:
            logger.exception("Failed to fetch {} with method {}", url, method)
            return None

    @abstractmethod
    async def scrape(self, search_params: JobSearchParams) -> RawJobPostings:
        """Scrape job postings from the configured source.

        Subclasses must implement this method to perform source-specific
        scraping logic. Typically uses _request() for HTTP operations and
        parses responses into RawJobPostings format.

        Args:
            search_params: Search criteria including job title and location.

        Returns:
            RawJobPostings object containing scraped job postings.

        Raises:
            Exception: May raise various exceptions from HTTP requests or
                parsing failures. Implementations should handle gracefully.
        """
