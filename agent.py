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
from langchain_core.tools import StructuredTool
from a2a.client import Client, A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message, get_stream_response_text
from a2a.types import Role, SendMessageRequest
import httpx
import re

def _format_agent_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name).lower()

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

    def __init__(
            self, 
            key: str, 
            mcp: MultiServerMCPClient | None = None, 
            a2a: list[str] | None = None
        ):
        self._mcp = mcp
        self._a2a = a2a
        self._a2a_clients: list[Client] = []
        self._model = ChatGoogleGenerativeAI(model = "gemini-3.5-flash-lite", api_key = key)
        self._graph: CompiledStateGraph | None = None

    async def setup(self, checkpointer: BaseCheckpointSaver):
        tools = [*self._tools]

        if self._mcp is not None:
            mcp_tools = await self._mcp.get_tools()
            tools.extend(mcp_tools)
        
        if self._a2a:
            self._httpx_client = httpx.AsyncClient()
            for url in self._a2a:
                resolver = A2ACardResolver(httpx_client = self._httpx_client, base_url = url)
                card = await resolver.get_agent_card()
                client = await create_client(
                    agent = card,
                    client_config = ClientConfig(
                        httpx_client = self._httpx_client,
                        streaming = False,
                    ),
                )
                self._a2a_clients.append(client)
                a2a_tool = self._create_a2a_tool(
                    client = client,
                    name = card.name,
                    description = self._a2a_description(card),
                )
                tools.append(a2a_tool)

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
                "Agent has not been setup"
            )
        result = await self._graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content = message),
                ],
            },
            config={
                "configurable": {
                    "thread_id": 
                    thread_id
                },
            },
        )
        message = result["messages"][-1]
        return message.content[0]["text"]

    def _a2a_description(self, card) -> str:
        parts = [
            f"Agent: {card.name}",
            f"Description: {card.description or ''}",
        ]

        if card.skills:
            parts.append("Skills:")

            for skill in card.skills:
                parts.append(
                    f"- ID: {skill.id}"
                )
                parts.append(
                    f"  Name: {skill.name}"
                )
                parts.append(
                    f"  Description: {skill.description or ''}"
                )

                if skill.tags:
                    parts.append(
                        f"  Tags: {', '.join(skill.tags)}"
                    )

                if skill.examples:
                    parts.append(
                        "  Examples: "
                        + "; ".join(skill.examples)
                    )

        return "\n".join(parts)

    def _create_a2a_tool(self,client: Client,name: str,description: str) -> StructuredTool:
        async def call(message: str) -> str:
            request = SendMessageRequest(
                message=new_text_message(
                    message,
                    role=Role.ROLE_USER,
                ),
            )
            response = None
            async for chunk in client.send_message(request):
                response = chunk
            if response is None:
                raise RuntimeError(
                    f"A2A agent '{name}' returned no response"
                )
            return self._extract_text(response)

        return StructuredTool.from_function(
            coroutine = call,
            name=f"a2a_{_format_agent_name(name)}",
            description=(
                f"Delegate work to the {name} agent. "
                f"{description}"
            ),
        )

    def _extract_text(self, response) -> str:
        text = get_stream_response_text(response)
        if not text:
            raise RuntimeError(
                "A2A agent returned no text"
            )
        return text

    async def close(self):
        for client in self._a2a_clients:
            await client.close()
        if self._httpx_client is not None:
            await self._httpx_client.aclose()