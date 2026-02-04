from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr


class ChromaConfig(BaseModel):
    """Configuration for ChromaDB embedding operations.

    Defines embedding model selection and API credentials for vector
    generation. Used by ChromaStorage to initialize OpenAI embedding
    functions for semantic search.
    """

    model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model identifier (e.g. text-embedding-3-small).",
    )
    api_key: SecretStr = Field(
        default=...,
        description="API key for the embedding provider. Optional for local use.",
    )
