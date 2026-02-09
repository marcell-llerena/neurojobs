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

3. **Upload your resume:**
   - Open your Telegram bot conversation
   - Send the `/upload` command
   - The bot will prompt you to send your resume as a PDF document
   - Upload your resume PDF file
   - Wait for confirmation that your CV has been saved and processed

4. **Search for jobs:**
   - Send a message to the bot requesting job searches, for example:
     - "Search jobs of Data Scientist at Remote"
     - "Find Software Engineer positions in New York"
     - "Look for Machine Learning Engineer jobs in San Francisco"
   - The bot will scrape and store relevant job postings based on your criteria

5. **Get personalized recommendations:**
   - After uploading your resume and searching for jobs, you can ask for personalized matches:
     - "What are the best jobs to fit with my resume profile?"
     - "Show me job recommendations based on my resume"
     - "What jobs match my skills?"
   - The bot will analyze your resume and provide job recommendations ranked by relevance


## Roadmap

NeuroJobs is evolving from **resume ingestion** → **job discovery** → **matching** → **recommendations**.
Below is a high-level roadmap of what’s already built and what’s coming next.

### ✅ Done
- Upload resume via Telegram (`/upload`)
- Parse CV → clean data → structured profile
- Job search by **title** and **location**
- Match job postings against the user’s resume/profile (rank relevant fits)
- Seniority / experience level support (user can specify it and use it as a search filter)

### ⏳ Planned (Next)
- More filters (keywords, stack/skills, company, salary range if available)
- Multi-source scraping (pluggable scrapers per platform)
- More sophisticated matching strategies (hybrid scoring: semantic similarity + structured rules)
- Weighted scoring (skills, years of experience, seniority, location/remote, keywords)
