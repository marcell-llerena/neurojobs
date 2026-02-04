from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr


class AgentConfig(BaseModel):
    """Configuration for the LangGraph-based conversational agent.

    Defines LLM model parameters, API credentials, and retry behavior
    for the agent's language model interactions. Used by GraphBuilder to
    initialize the ChatOpenAI instance.

    Attributes:
        model: LLM model identifier (e.g., "gpt-4", "gpt-3.5-turbo").
        api_key: Secret API key for the LLM provider.
        temperature: Sampling temperature (0.0-1.0). Lower values
            produce more deterministic outputs.
        request_timeout: Maximum seconds to wait for LLM API responses.
        max_retries: Maximum number of retry attempts on API failures.
    """

    model: str = Field(
        default="gpt-5-nano",
        description="LLM model identifier used for the agent.",
    )
    api_key: SecretStr = Field(
        default=...,
        description="API key for the configured LLM provider (e.g. OpenAI).",
    )
    temperature: float = Field(
        default=0.2,
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
