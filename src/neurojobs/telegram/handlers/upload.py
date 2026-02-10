from loguru import logger
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

from neurojobs.config.paths import DEFAULT_CV_DIR


WAITING_FOR_CV = 1


async def _upload_cv_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initialize the CV upload conversation flow.

    Entry point handler for the /upload command. Prompts the user to send
    a PDF document containing their CV/resume.

    Args:
        update: Telegram update object containing the command message.
        context: Telegram bot context (unused in this handler).

    Returns:
        Conversation state constant indicating we're waiting for a CV file.
    """
    logger.info("CV upload flow started")
    if update.message:
        await update.message.reply_text(
            text=("📄 <b>CV upload</b>\nSend your CV as a <b>PDF document</b>."),
            parse_mode="html",
        )
    return WAITING_FOR_CV


async def _upload_cv_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process an uploaded PDF document as a CV/resume.

    Downloads the PDF file, runs it through the resume processing pipeline
    (extraction, embedding, storage), and confirms success to the user.
    On failure, prompts the user to retry.

    Args:
        update: Telegram update containing the document message.
        context: Telegram bot context with bot_data['resume_pipeline'].

    Returns:
        ConversationHandler.END on success, WAITING_FOR_CV on failure
        to allow retry.
    """
    if not update.message:
        return WAITING_FOR_CV

    doc = update.message.document

    if not doc or not doc.file_name:
        return WAITING_FOR_CV

    DEFAULT_CV_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DEFAULT_CV_DIR / doc.file_name

    logger.info("Processing CV upload | file_name={}", doc.file_name)

    try:
        file = await doc.get_file()
        await file.download_to_drive(file_path)
        logger.info(
            "CV file downloaded successfully | file_name={} path={}",
            doc.file_name,
            file_path,
        )

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,  # type: ignore[reportOptionalMemberAccess]
            action=ChatAction.TYPING,
        )

        resume_pipeline = context.application.bot_data["resume_pipeline"]
        resume_pipeline.run(file_path)
        logger.info(
            "CV pipeline completed successfully | file_name={} path={}",
            doc.file_name,
            file_path,
        )
        await update.message.reply_text(
            text=("✅ <b>CV saved and processed</b>\nYour CV has been stored."),
            parse_mode="html",
        )
        return ConversationHandler.END
    except Exception:
        logger.exception("CV upload or pipeline failed | file_name={}", doc.file_name)
        await update.message.reply_text(
            text=(
                "❌ <b>Something went wrong</b>\n"
                "I could not save or process your CV. "
                "Please check that the file is a valid PDF and try again. "
                "If it keeps failing, try a different file or a smaller size."
            ),
            parse_mode="html",
        )
        return WAITING_FOR_CV


async def _upload_cv_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the CV upload conversation.

    Handler for the /cancel command during upload flow. Ends the
    conversation and informs the user they can restart with /upload.

    Args:
        update: Telegram update containing the cancel command.
        context: Telegram bot context (unused).

    Returns:
        ConversationHandler.END to terminate the conversation.
    """
    logger.info("CV upload cancelled by user")
    if update.message:
        await update.message.reply_text(
            text="❌ Upload cancelled. Send /upload when you want to try again."
        )
    return ConversationHandler.END


def upload_conv_handler() -> ConversationHandler:
    """Create a conversation handler for CV/resume upload workflow.

    Configures a state machine for handling the /upload command:
    - Entry: /upload command triggers _upload_cv_start
    - State: WAITING_FOR_CV accepts PDF documents via _upload_cv_receive
    - Fallback: /cancel command ends the conversation

    Returns:
        Configured ConversationHandler instance ready to be registered
        with a Telegram Application.
    """
    return ConversationHandler(
        entry_points=[CommandHandler("upload", _upload_cv_start)],
        states={
            WAITING_FOR_CV: [MessageHandler(filters.Document.PDF, _upload_cv_receive)],
        },
        fallbacks=[CommandHandler("cancel", _upload_cv_cancel)],
        name="upload_conv_handler",
        persistent=False,
    )
