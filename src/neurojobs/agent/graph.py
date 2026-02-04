from langchain_core.messages import SystemMessage
from langchain_core.messages import ToolMessage
from langchain_core.messages import trim_messages
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.graph.message import MessagesState
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from loguru import logger

from neurojobs.agent.config import AgentConfig
from neurojobs.prompts.loader import load_prompt


class GraphBuilder:
    """Builds and configures LangGraph agent workflows.

    Constructs a stateful conversational agent graph with tool-calling
    capabilities. The graph routes between agent reasoning and tool
    execution nodes, maintaining conversation state via checkpoints.

    Attributes:
        _tools: List of LangChain tools available to the agent.
        _checkpointer: Checkpoint saver for conversation state persistence.
        _llm: Base ChatOpenAI instance for agent reasoning.
        _llm_with_tools: LLM instance bound with tool definitions.
        _system_prompt: Base system prompt for agent behavior.
        _tool_mode_prompts: Context-specific prompts keyed by tool name.
    """

    def __init__(
        self,
        config: AgentConfig,
        tools: list[BaseTool],
        checkpointer: BaseCheckpointSaver,
    ) -> None:
        self._tools = tools
        self._checkpointer = checkpointer
        self._llm = ChatOpenAI(
            model_name=config.model,
            openai_api_key=config.api_key,
            temperature=config.temperature,
            request_timeout=config.request_timeout,
            max_retries=config.max_retries,
        )
        self._llm_with_tools = self._llm.bind_tools(self._tools)
        self._system_prompt = SystemMessage(
            content=load_prompt("neurojobs.prompts", "agent_system.md")
        )
        self._tool_mode_prompts: dict[str, SystemMessage] = {
            "scrape_jobs": SystemMessage(
                content=load_prompt("neurojobs.prompts", "scrape_jobs_system.md")
            ),
            "get_resume_status": SystemMessage(
                content=load_prompt("neurojobs.prompts", "resume_status_system.md")
            ),
            "match_jobs": SystemMessage(
                content=load_prompt("neurojobs.prompts", "match_jobs_system.md")
            ),
        }

    def _get_tool_mode_prompt(self, state: MessagesState) -> list[SystemMessage]:
        """Determine context-specific system prompt based on last tool call.

        Analyzes the conversation state to detect which tool was last
        executed, then returns a specialized system prompt for that tool's
        context. Enables tool-specific agent behavior and instructions.

        Args:
            state: Current LangGraph messages state.

        Returns:
            List containing the relevant tool-mode system message, or
            empty list if no tool context is detected.
        """
        if not state["messages"]:
            return []

        last = state["messages"][-1]
        logger.info(f"Last message: {last}")
        if isinstance(last, ToolMessage):
            tool_name = getattr(last, "name", None)
            logger.info(f"Tool name: {tool_name}")
            if tool_name and tool_name in self._tool_mode_prompts:
                return [self._tool_mode_prompts[tool_name]]

        return []

    async def _agent_node(self, state: MessagesState) -> MessagesState:
        """Execute agent reasoning step in the graph.

        Processes conversation history with message trimming for token
        efficiency, applies context-aware system prompts, invokes the LLM
        with tool bindings, and returns updated state with the agent's
        response.

        Args:
            state: Current conversation state with message history.

        Returns:
            Updated state containing the agent's response message.
        """
        tool_mode = self._get_tool_mode_prompt(state)
        trimmed_messages = trim_messages(
            state["messages"],
            max_tokens=12,
            token_counter=len,
            strategy="last",
            start_on="human",
            include_system=False,
        )
        messages = [self._system_prompt, *tool_mode, *trimmed_messages]
        response = await self._llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def build_graph(self) -> CompiledStateGraph[MessagesState]:  # type: ignore[reportArgumentType]
        """Compile and return the configured LangGraph agent workflow.

        Constructs a StateGraph with the following structure:
        - START -> agent (initial reasoning)
        - agent -> tools (if tool calls detected) or END
        - tools -> agent (continue after tool execution)
        - agent -> END (final response)

        The graph uses conditional edges to route between agent and tools
        based on whether the agent requests tool execution.

        Returns:
            Compiled graph ready for async invocation with thread-based
            conversation state management via checkpointer.
        """
        graph = StateGraph(MessagesState)  # type: ignore[reportArgumentType]
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
        graph.add_edge("agent", END)
        return graph.compile(checkpointer=self._checkpointer)
