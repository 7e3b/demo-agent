from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langmem.short_term import SummarizationNode
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from tools import (
    current_datetime,
    add,
    subtract,
    multiply,
    divide,
)


class _State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class Agent:
    _tools = [current_datetime, add, subtract, multiply,divide]

    def __init__(self, key: str, mcp: MultiServerMCPClient | None = None):
        self._mcp = mcp
        self._model = ChatGoogleGenerativeAI(model = "gemini-3.5-flash-lite", api_key = key)
        self._graph: CompiledStateGraph | None = None

    async def setup(self, checkpointer: BaseCheckpointSaver):
        tools = [*self._tools]
        if self._mcp is not None:
            tools.extend(await self._mcp.get_tools())
        agent = create_agent(model = self._model, tools = tools)

        summarize = SummarizationNode(
            model = self._model,
            max_tokens = 8000,
            output_messages_key = "messages",
        )

        builder = StateGraph(_State)

        builder.add_node("agent",agent)
        builder.add_node("summarize",summarize)

        builder.add_edge(START,"agent")
        builder.add_edge("agent","summarize")
        builder.add_edge("summarize",END)

        self._graph = builder.compile(checkpointer=checkpointer)

    async def ainvoke(self, message: str, thread_id: str) -> str:
        if self._graph is None:
            raise RuntimeError(
                "agent has not been setup"
            )
        result = await self._graph.ainvoke(
            {"messages": [HumanMessage(content = message)]},
            config={"configurable": {"thread_id": thread_id}},
        )
        message = result["messages"][-1]
        content = message.content[0]
        return content['text']