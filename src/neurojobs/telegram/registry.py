from neurojobs.telegram.handlers.chat import chat_handler
from neurojobs.telegram.handlers.upload import upload_conv_handler
from telegram.ext import Application
from telegram.ext import MessageHandler
from telegram.ext import filters


def register_handlers(application: Application) -> None:
    """Register Telegram bot handlers with the application.

    Configures message routing for the NeuroJobs Telegram bot:
    - Text messages (non-commands) are routed to the chat handler for
      agent interaction
    - Upload conversation handler manages CV/resume upload workflow

    Args:
        application: Telegram Bot application instance to register handlers
            with. Must have bot_data configured with 'graph' and
            'resume_pipeline' keys.
    """
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler)
    )
    application.add_handler(upload_conv_handler())
