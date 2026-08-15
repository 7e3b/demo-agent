import uvicorn
from config import config
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/")
async def root():
    return Response()

def main():
    if config.reload:
        uvicorn.run("main:app", port=config.port, reload=True)
    else:
        uvicorn.run(app, port=config.port)

if __name__ == '__main__':
    main()
    