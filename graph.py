from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config import config
from langgraph.checkpoint.base import BaseCheckpointSaver
from langmem.short_term import SummarizationNode
from langgraph.prebuilt import ToolNode, tools_condition
from tools import current_datetime, add, subtract, multiply, divide
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

client = None

async def compile(checkpointer: BaseCheckpointSaver):
    global client
    mcp = MultiServerMCPClient(
        {
            "user_service": {
                "transport": "streamable_http",
                "url": "http://localhost:4050/mcp",
            },
            "wallet_service": {
                "transport": "streamable_http",
                "url": "http://localhost:4051/mcp",
            },
        }
    )

    gemini = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite",api_key=config.gemini)
    local_tools = [current_datetime, add, subtract, multiply, divide]
    mcp_tools = await mcp.get_tools()
    gemini_agent = create_agent(model=gemini, tools=[*local_tools, *mcp_tools])

    summarize = SummarizationNode(model=gemini,max_tokens=8000,output_messages_key="messages")

    async def agent(state: State):
        response = await gemini_agent.ainvoke({"messages": state["messages"]})
        return {"messages": response["messages"]}

    builder = StateGraph(State)

    builder.add_node("agent", agent)
    builder.add_node("summarize", summarize)

    builder.add_edge(START, "agent")
    builder.add_edge("agent", "summarize")
    builder.add_edge("summarize", END)

    client = builder.compile(checkpointer=checkpointer)