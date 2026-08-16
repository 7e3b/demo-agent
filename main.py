import uvicorn
from config import config
from fastapi import FastAPI, Response
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
import graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(
        config.postgres
    ) as checkpointer:
        await checkpointer.setup()
        graph.compile(checkpointer)
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return Response()

class ChatRequest(BaseModel):
    message: str
    thread_id: str

class ChatResponse(BaseModel):
    message: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await graph.client.ainvoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"configurable": {"thread_id": request.thread_id}},
    )
    message = result["messages"][-1]
    content = message.content[0]
    text = content['text']
    return ChatResponse(message=text)

def main():
    uvicorn.run(app, port=3000)

if __name__ == '__main__':
    main()
    