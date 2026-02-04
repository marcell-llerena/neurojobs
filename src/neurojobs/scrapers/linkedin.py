import hashlib
from typing import override
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from bs4 import BeautifulSoup
from bs4 import Tag
from loguru import logger

from neurojobs.scrapers.base import BaseScraper
from neurojobs.scrapers.config import ScraperConfig
from neurojobs.scrapers.schemas import JobSearchParams
from neurojobs.scrapers.schemas import RawJobPosting
from neurojobs.scrapers.schemas import RawJobPostings


class LinkedinScraper(BaseScraper):
    """LinkedIn-specific job posting scraper.

    Implements web scraping for LinkedIn job search results. Fetches job
    listings from LinkedIn's public job search page, extracts metadata
    from search results cards, and enriches postings with full
    descriptions by fetching individual job pages.

    Attributes:
        SOURCE: Source identifier string ("LinkedIn").
        BASE_URL: Base URL for LinkedIn job search endpoint.
        SELECTORS: CSS selectors for extracting job data from HTML.
    """

    SOURCE = "LinkedIn"
    BASE_URL = "https://www.linkedin.com/jobs/search/"
    SELECTORS = {
        "job_cards": "base-card",
        "job_title": "base-search-card__title",
        "job_company": "base-search-card__subtitle",
        "job_location": "job-search-card__location",
        "job_url": "base-card__full-link",
        "job_description": (
            ".core-section-container__content .show-more-less-html__markup"
        ),
    }

    def __init__(self, config: ScraperConfig | None = None) -> None:
        super().__init__(config or ScraperConfig())

    @override
    async def scrape(self, search_params: JobSearchParams) -> RawJobPostings:
        """Scrape job postings from LinkedIn.

        Executes a two-phase scraping process:
        1. Fetches search results page and extracts job metadata
        2. Enriches postings by fetching full descriptions from individual
           job pages

        Args:
            search_params: Search criteria including job title and location.

        Returns:
            RawJobPostings object containing scraped job postings. Returns
            empty collection if no postings found.

        Raises:
            RuntimeError: If scraping fails at any stage. Original exception
                is chained for debugging.
        """
        logger.info(
            "Scraping jobs for: job title={} and job location={}",
            search_params.job_title,
            search_params.job_location,
        )

        try:
            job_postings = await self._fetch_job_postings(search_params)
            if not job_postings.items:
                logger.info("No job postings found")
                return job_postings

            await self._fetch_job_description(job_postings)
            logger.info("Successfully scraped {} job postings", len(job_postings.items))
            return job_postings
        except Exception as error:
            logger.exception("Unexpected error occurred during scraping")
            raise RuntimeError("Failed to scrape job postings") from error

    async def _fetch_job_postings(
        self, search_params: JobSearchParams
    ) -> RawJobPostings:
        """Fetch job posting metadata from LinkedIn search results.

        Constructs search URL, fetches HTML content, and parses job cards
        to extract title, company, location, and URL fields.

        Args:
            search_params: Search criteria for building query URL.

        Returns:
            RawJobPostings object with metadata-only postings (descriptions
            are None until enriched).

        Raises:
            RuntimeError: If no HTTP response is received for the search URL.
        """
        search_url = self._build_search_url(search_params)
        logger.debug("Searching for jobs at {}", search_url)

        responses = await self._request(search_url)
        if not responses.items:
            raise RuntimeError(f"No responses received for {search_url}")

        return self._parse_job_postings(responses.items[0].content)

    def _parse_job_postings(self, html_content: str) -> RawJobPostings:
        """Parse HTML content to extract job posting cards.

        Uses BeautifulSoup to find job card elements and extracts structured
        data from each card. Limits results to first 20 postings.

        Args:
            html_content: Raw HTML string from LinkedIn search results page.

        Returns:
            RawJobPostings object containing parsed job postings. Returns
            empty collection if no cards found.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        job_cards = soup.find_all(class_=self.SELECTORS["job_cards"])
        if not job_cards:
            logger.debug("No job cards found")
            return RawJobPostings()

        logger.debug("Found {} job cards", len(job_cards))
        job_postings = [
            posting
            for card in job_cards
            if (posting := self._extract_job_posting_from_card(card))
        ][:20]

        return RawJobPostings(items=job_postings)

    def _extract_job_posting_from_card(self, card: Tag) -> RawJobPosting | None:
        """Extract job posting data from a single HTML card element.

        Parses BeautifulSoup Tag to extract title, company, location, and
        URL. Generates job_id as SHA256 hash of the URL for uniqueness.
        Returns None if required fields (title, URL) are missing.

        Args:
            card: BeautifulSoup Tag element representing a job card.

        Returns:
            RawJobPosting object if extraction succeeds, None otherwise.
        """
        try:
            title = self._extract_text(card, "job_title")
            company = self._extract_text(card, "job_company")
            location = self._extract_text(card, "job_location")
            url = self._extract_url(card)
            if not title or not url:
                return None

            job_id = hashlib.sha256(url.encode()).hexdigest()

            return RawJobPosting(
                job_id=job_id,
                source=self.SOURCE,
                title=title,
                company=company,
                location=location,
                description=None,
                url=url,
            )
        except Exception:
            logger.exception("Failed to extract job posting from card")
            return None

    def _extract_text(self, card: Tag, selector_key: str) -> str | None:
        """Extract text content from a card element using CSS selector.

        Args:
            card: BeautifulSoup Tag element to search within.
            selector_key: Key into SELECTORS dict for CSS class name.

        Returns:
            Stripped text content if element found, None otherwise.
        """
        tag = card.find(class_=self.SELECTORS[selector_key])
        return tag.get_text(strip=True) if tag else None

    def _extract_url(self, card: Tag) -> str | None:
        """Extract and normalize job posting URL from card element.

        Finds the job URL link, extracts href attribute, and normalizes
        it by removing query parameters and fragments to produce canonical
        URL.

        Args:
            card: BeautifulSoup Tag element containing job URL link.

        Returns:
            Canonical URL string if found, None otherwise.
        """
        url_tag = card.find(class_=self.SELECTORS["job_url"])
        if url_tag and url_tag.has_attr("href"):
            href = url_tag.get("href")
            if href:
                parts = urlsplit(str(href))
                return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return None

    async def _fetch_job_description(self, job_postings: RawJobPostings) -> None:
        """Enrich job postings with full descriptions from individual pages.

        Fetches HTML content for each job posting URL, parses description
        text, and updates the posting objects in-place. Silently skips
        postings where description cannot be extracted.

        Args:
            job_postings: RawJobPostings object to enrich. Postings are
                modified in-place with description fields populated.
        """
        job_urls = [job.url for job in job_postings.items]
        responses = await self._request(job_urls)
        url_to_description = {
            response.url: self._parse_job_description(response.content)
            for response in responses.items
        }
        for job in job_postings.items:
            job.description = url_to_description.get(job.url)
            if not job.description:
                logger.debug("No description found for {}", job.url)

    def _parse_job_description(self, html_content: str) -> str | None:
        """Extract job description text from job detail page HTML.

        Uses CSS selector to find description markup and extracts text
        content.

        Args:
            html_content: Raw HTML string from LinkedIn job detail page.

        Returns:
            Stripped description text if found, None otherwise.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            description = soup.select_one(self.SELECTORS["job_description"])
            return description.get_text(strip=True) if description else None
        except Exception:
            logger.exception("Failed to parse job description")
            return None

    def _build_search_url(self, search_params: JobSearchParams) -> str:
        """Construct LinkedIn job search URL with query parameters.

        Builds URL by encoding job title and location as query parameters
        and appending to BASE_URL.

        Args:
            search_params: Search criteria to encode in URL.

        Returns:
            Complete LinkedIn job search URL with query string.
        """
        params = {
            "keywords": search_params.job_title,
            "location": search_params.job_location,
        }
        query_params = urlencode(params)
        return f"{self.BASE_URL}?{query_params}"
