from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field


class ProcessedJobPosting(BaseModel):
    """Normalized job posting data after processing and validation.

    Represents a cleaned, validated job posting ready for storage and
    embedding generation. All fields are required and text content has
    been normalized (emoji removal, whitespace cleanup).
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
    company: str = Field(
        ...,
        description="Employer or company name.",
    )
    location: str = Field(
        ...,
        description="Work location (e.g. city, state, country).",
    )
    description: str = Field(
        ...,
        description="Full text of the role description.",
    )
    url: str = Field(
        ...,
        description="Canonical URL of the job posting.",
    )


class ProcessedJobPostings(BaseModel):
    """Collection of processed job postings with batch metadata.

    Groups multiple ProcessedJobPosting items with processing run
    identifiers for tracking ingestion batches and timestamps.
    """

    items: list[ProcessedJobPosting] = Field(
        default_factory=list,
        description="Collection of processed job postings.",
    )
    processed_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this processing run.",
    )
    processed_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp at which processing was completed.",
    )
