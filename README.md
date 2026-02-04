# NeuroJobs

NeuroJobs is a Telegram-based assistant designed to simplify the job search workflow.
Right now, it focuses on the first critical step: **collecting your resume and transforming it into a clean, structured profile** that can later be used for job discovery and matching.

## Tech Stack

- **Python 3.13** - Core programming language
- **python-telegram-bot** - Telegram Bot API integration
- **LangChain & LangGraph** - AI agent framework and workflow orchestration
- **OpenAI** - LLM and embedding services
- **ChromaDB** - Vector database for semantic search
- **BeautifulSoup4** - Web scraping and HTML parsing
- **SQLite** - Local data storage and checkpointing
- **Pydantic** - Data validation and settings management

## Basic Setup and Installation

### Prerequisites

- Python 3.13 or higher
- Docker and Docker Compose (for containerized deployment)
- OpenAI API key
- Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd neurojobs
   ```

2. **Create a `.env` file** in the project root with the following variables:
   ```env
   NEUROJOBS_OPENAI_API_KEY=your_openai_api_key_here
   NEUROJOBS_TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ```

3. **Install dependencies** (if running locally):
   ```bash
   pip install uv
   uv sync
   ```

## How to Run the Project

### Running Locally

1. Ensure all dependencies are installed (see Installation step 3).

2. Run the bot:
   ```bash
   uv run scripts/run_telegram.py
   ```

The bot will start polling for messages and is ready to interact with users on Telegram.
