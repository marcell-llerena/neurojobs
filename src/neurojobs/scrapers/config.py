from pydantic import BaseModel
from pydantic import Field


class ScraperConfig(BaseModel):
    """Configuration for web scraping operations.

    Defines rate limits, concurrency controls, timeouts, and retry
    behavior for HTTP-based job posting scrapers. Used to prevent
    overwhelming target servers and handle transient failures.
    """

    max_requests_per_minute: int = Field(
        default=10,
        ge=1,
        le=30,
        description="Rate limit: maximum requests per minute.",
    )
    max_concurrent_requests: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of simultaneous requests.",
    )
    request_timeout: int = Field(
        default=30,
        gt=0,
        description="Request timeout in seconds.",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries on request failure.",
    )
    retry_multiplier: int = Field(
        default=2,
        gt=0,
        description="Exponential backoff multiplier applied between retries.",
    )
    retry_wait_min: float = Field(
        default=1,
        gt=0,
        description="Minimum delay in seconds before retry.",
    )
    retry_wait_max: float = Field(
        default=30,
        gt=0,
        description="Maximum delay in seconds before retry.",
    )
