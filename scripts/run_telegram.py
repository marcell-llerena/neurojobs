import asyncio

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from loguru import logger
from telegram.ext import ApplicationBuilder

from neurojobs.agent.graph import GraphBuilder
from neurojobs.config.settings import get_settings
from neurojobs.ingestion.resume_pipeline import ResumePipeline
from neurojobs.ingestion.scraper_pipeline import ScraperPipeline
from neurojobs.scrapers.linkedin import LinkedinScraper
from neurojobs.storage.chroma import ChromaStorage
from neurojobs.storage.sqlite import SQLiteStorage
from neurojobs.telegram.registry import register_handlers
from neurojobs.tools import make_tools


async def main() -> None:
    logger.info("Starting Telegram bot")

    settings = get_settings()
    settings.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(
        settings.checkpoint_path
    ) as checkpointer:
        storage = SQLiteStorage(settings.db_path)
        vector_store = ChromaStorage(
            chroma_dir=settings.chroma_dir, config=settings.chroma
        )
        resume_pipeline = ResumePipeline(
            storage=storage,
            vector_store=vector_store,
            config=settings.resume,
        )
        scraper_pipeline = ScraperPipeline(
            scraper=LinkedinScraper(settings.scraper),
            storage=storage,
            vector_store=vector_store,
        )
        tools = make_tools(storage, vector_store, scraper_pipeline)

        graph_builder = GraphBuilder(
            settings.agent,
            tools=tools,
            checkpointer=checkpointer,
        )
        graph = graph_builder.build_graph()

        application = (
            ApplicationBuilder()
            .token(settings.telegram_bot_token.get_secret_value())
            .build()
        )

        application.bot_data.update(
            {
                "resume_pipeline": resume_pipeline,
                "scraper_pipeline": scraper_pipeline,
                "storage": storage,
                "vector_store": vector_store,
                "settings": settings,
                "graph": graph,
            }
        )

        register_handlers(application)

        await application.initialize()
        await application.start()
        if application.updater:
            await application.updater.start_polling()
            await asyncio.Event().wait()
            await application.updater.stop()

        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
