from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class JobSearchParams(BaseModel):
    """Search criteria for job posting queries.

    Parameters used to construct search queries for job boards and
    APIs. Represents user intent for job title and location filtering,
    plus a limit on the maximum number of job postings to scrape.
    """

    job_title: str = Field(
        ...,
        description="Search query for job title or position.",
    )
    job_location: str = Field(
        default="United States",
        description="Location filter for the search (e.g. city, state, country).",
    )
    job_limit: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Maximum number of job postings to scrape.",
    )


class ScraperResponse(BaseModel):
    """HTTP response data from a single scraping request.

    Captures raw HTML content and HTTP metadata from a fetched web page.
    Used internally by scrapers to pass response data to parsers.
    """

    url: str = Field(
        ...,
        description="URL of the page that was scraped.",
    )
    status: int = Field(
        ...,
        ge=100,
        le=599,
        description="HTTP response status code.",
    )
    content: str = Field(
        ...,
        description="Raw HTML body of the scraped page.",
    )


class ScraperResponses(BaseModel):
    """Collection of HTTP responses from batch scraping operations.

    Groups multiple ScraperResponse objects for concurrent request
    handling and batch processing.
    """

    items: list[ScraperResponse] = Field(
        default_factory=list,
        description="Collection of scraped responses.",
    )


class RawJobPosting(BaseModel):
    """Unprocessed job posting data from scraper output.

    Represents job posting data as extracted directly from source HTML
    without validation or normalization. Some fields may be None if not
    found during scraping. Used as input to processing pipeline.
    """

    job_id: str = Field(
        ...,
        description="Unique identifier of the job posting.",
    )
    source: str = Field(
        ...,
        description="Job board or platform (e.g. LinkedIn).",
    )
    title: str = Field(
        ...,
        description="Job title or position name.",
    )
    company: str | None = Field(
        default=None,
        description="Employer or company name.",
    )
    location: str | None = Field(
        default=None,
        description="Work location (e.g. city, state, country).",
    )
    description: str | None = Field(
        default=None,
        description="Full text of the role description.",
    )
    url: str = Field(
        ...,
        description="Canonical URL of the job posting.",
    )
    scraped_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp at which the posting was scraped.",
    )


class RawJobPostings(BaseModel):
    """Collection of raw job postings from scraping operations.

    Groups multiple RawJobPosting items as returned by scrapers before
    processing and validation stages.
    """

    items: list[RawJobPosting] = Field(
        default_factory=list,
        description="Collection of raw job postings.",
    )
