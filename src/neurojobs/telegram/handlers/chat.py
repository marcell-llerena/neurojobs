from collections.abc import Generator

from langchain_core.messages import BaseMessage
from langchain_core.messages import HumanMessage
from loguru import logger
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes


def _last_message(messages: list[BaseMessage]) -> str:
    """Extract the last non-empty text message from a message history.

    Searches backwards through the message list to find the first message
    with non-empty string content. Used to extract the agent's final
    response from a LangGraph conversation state.

    Args:
        messages: List of message objects from LangChain conversation state.

    Returns:
        The content of the last non-empty message, or a fallback error
        message if no valid content is found.
    """
    for message in reversed(messages):
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content
    return "Please try again, I have a problem generating a response."


def _chunk_message(message: str, size: int = 4000) -> Generator[str]:
    """Split a message into chunks of specified size.

    Telegram has message length limits. This function breaks long agent
    responses into smaller chunks that can be sent as separate messages.

    Args:
        message: The full message text to chunk.
        size: Maximum characters per chunk. Defaults to 4000 to stay
            under Telegram's 4096 character limit.

    Yields:
        Sequential chunks of the message, each up to `size` characters.
    """
    for i in range(0, len(message), size):
        yield message[i : i + size]


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages from Telegram users.

    Processes user text messages by invoking the LangGraph agent workflow
    stored in bot_data. Sends typing indicator, invokes the graph with
    thread-based conversation state, and replies with the agent's response
    (chunked if necessary).

    Args:
        update: Telegram update object containing the incoming message.
        context: Telegram bot context with application and bot_data access.

    Raises:
        Exception: Any exception during processing is caught, logged, and
            a user-friendly error message is sent. The exception is not
            propagated to the Telegram framework.
    """
    if not update.message:
        return

    text = update.message.text
    if not text:
        await update.message.reply_text(
            text="📝 Please send a text message to start the conversation"
        )
        return

    try:
        if not update.effective_chat:
            return

        graph = context.application.bot_data["graph"]

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )

        config = {"configurable": {"thread_id": str(update.effective_chat.id)}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=text)]}, config=config
        )

        last_message = _last_message(result["messages"])
        for chunk in _chunk_message(last_message):
            await update.message.reply_text(text=chunk, disable_web_page_preview=True)

    except Exception:
        logger.exception("Error in chat handler")
        await update.message.reply_text(
            text="❌ Something went wrong. Please try again in a few seconds."
        )
