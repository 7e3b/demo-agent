import uvicorn
from config import config
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/")
async def root():
    return Response()

if __name__ == '__main__':
    uvicorn.run(app, port=config.port)