"""Hello World 应用 - FastAPI 对照组"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI()


@app.get("/")
async def index():
    return "Hello World"


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    workers = int(os.environ.get("WORKERS", 1))
    uvicorn.run(app, host="0.0.0.0", port=8080, workers=workers)
