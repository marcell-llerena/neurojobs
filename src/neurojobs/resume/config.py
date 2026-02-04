from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr


class ResumeConfig(BaseModel):
    """Configuration for LLM-based resume extraction.

    Defines model parameters, API credentials, and retry behavior for
    extracting structured data from resume PDFs. Used by ResumeExtractor
    to configure ChatOpenAI instances with structured output.
    """

    model: str = Field(
        default="gpt-5-nano",
        description="LLM model identifier used for resume parsing and extraction.",
    )
    api_key: SecretStr = Field(
        default=...,
        description="API key for the configured LLM provider (e.g. OpenAI).",
    )
    temperature: float = Field(
        default=0,
        description="Sampling temperature (0-1). Lower values increase determinism.",
    )
    request_timeout: int = Field(
        default=60,
        description="Request timeout in seconds.",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries on request failure.",
    )
