from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from neurojobs.agent.config import AgentConfig
from neurojobs.config.paths import DEFAULT_CHECKPOINTER_PATH
from neurojobs.config.paths import DEFAULT_CHROMA_DIR
from neurojobs.config.paths import DEFAULT_DB_PATH
from neurojobs.resume.config import ResumeConfig
from neurojobs.scrapers.config import ScraperConfig
from neurojobs.storage.config import ChromaConfig


class Settings(BaseSettings):
    """Application-wide configuration settings.

    Centralizes all configuration from environment variables and defaults.
    Uses Pydantic Settings for validation and type coercion. Supports
    nested configuration via environment variable prefixes and delimiters.

    Attributes:
        db_path: Path to SQLite database file.
        chroma_dir: Directory path for ChromaDB persistence.
        checkpoint_path: Path to SQLite checkpoint database for LangGraph.
        openai_api_key: OpenAI API key for LLM and embedding services.
        agent: Agent configuration (model, temperature, etc.).
        resume: Resume extraction configuration.
        chroma: ChromaDB embedding model configuration.
        telegram_bot_token: Telegram bot API token.
        scraper: Scraper configuration (rate limits, timeouts, etc.).
    """

    model_config = SettingsConfigDict(
        env_prefix="NEUROJOBS_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    db_path: Path = Field(default=DEFAULT_DB_PATH)
    chroma_dir: Path = Field(default=DEFAULT_CHROMA_DIR)
    checkpoint_path: Path = Field(default=DEFAULT_CHECKPOINTER_PATH)

    # OpenAI API key
    openai_api_key: SecretStr = Field(default=...)

    # Agent model settings
    agent: AgentConfig = Field(default_factory=AgentConfig)

    # Resume settings
    resume: ResumeConfig = Field(default_factory=ResumeConfig)

    # Embedder settings
    chroma: ChromaConfig = Field(default_factory=ChromaConfig)

    # Telegram bot settings
    telegram_bot_token: SecretStr = Field(default=...)

    # Scraper settings
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings singleton instance.

    Returns a cached Settings instance loaded from environment variables
    and defaults. Subsequent calls return the same instance.

    Returns:
        Settings object with validated configuration values.
    """
    return Settings()
