from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config import config
from langgraph.checkpoint.base import BaseCheckpointSaver

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

gemini = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    api_key=config.gemini
)

async def llm(state: State):
    response = await gemini.ainvoke(state["messages"])
    return {"messages": [response]}

builder = StateGraph(State)

builder.add_node("llm", llm)

builder.add_edge(START, "llm")
builder.add_edge("llm", END)

client = None

def compile(checkpointer: BaseCheckpointSaver):
    global client
    client = builder.compile(checkpointer=checkpointer)