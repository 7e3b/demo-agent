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
from tools import add, subtract, multiply, divide

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

tools = [add, subtract, multiply, divide]
gemini = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite",api_key=config.gemini).bind_tools(tools)
gemini_with_tools = gemini.bind_tools(tools)

summarize = SummarizationNode(model=gemini,max_tokens=8000,output_messages_key="messages")

async def llm(state: State):
    response = await gemini_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}

tools = ToolNode(tools)

builder = StateGraph(State)

builder.add_node("llm", llm)
builder.add_node("tools", tools)
builder.add_node("summarize", summarize)

builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", tools_condition)
builder.add_edge("tools", "llm")
builder.add_edge("llm", "summarize")
builder.add_edge("summarize", END)

client = None

def compile(checkpointer: BaseCheckpointSaver):
    global client
    client = builder.compile(checkpointer=checkpointer)