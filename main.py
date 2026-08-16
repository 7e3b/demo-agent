import uvicorn
from config import config
from fastapi import FastAPI, Response
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from graph import graph

app = FastAPI()

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
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"configurable": {"thread_id": request.thread_id}},
    )
    message = result["messages"][-1]
    content = message.content[0]
    text = content['text']
    return ChatResponse(message=text)


def main():
    if config.reload:
        uvicorn.run("main:app", port=config.port, reload=True)
    else:
        uvicorn.run(app, port=config.port)

if __name__ == '__main__':
    main()
    