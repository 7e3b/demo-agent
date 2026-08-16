import uvicorn

from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Response
from pydantic import BaseModel

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import config
from agent import Agent

agent = Agent(
    # mcp = MultiServerMCPClient(
    #     {
    #         "weather_service": {
    #             "transport": "streamable_http",
    #             "url": "http://localhost:4055/mcp",
    #         },
    #     }
    # ),
    # a2a = ["http://localhost:4052"],
    key = config.gemini,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(config.postgres) as checkpointer:
        await checkpointer.setup()
        await agent.setup(checkpointer = checkpointer)
        yield
        await agent.close()

app = FastAPI(lifespan = lifespan)

@app.get("/")
def root():
    return Response()

class ChatRequest(BaseModel):
    timezone: str
    message: str
    thread_id: str

class ChatResponse(BaseModel):
    message: str

@app.post("/chat", response_model = ChatResponse)
async def chat(request: ChatRequest):
    message = await agent.ainvoke(
        message = request.message,
        thread_id = request.thread_id,
        timezone = ZoneInfo(request.timezone)
    )
    return ChatResponse(message = message)

def main():
    uvicorn.run(app, port = 3000)

if __name__ == "__main__":
    main()