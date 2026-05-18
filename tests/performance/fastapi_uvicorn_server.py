#!/usr/bin/env python
import argparse
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI()

@app.get("/", response_class=PlainTextResponse)
async def hello():
    return "Hello world"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    uvicorn.run(
        "fastapi_uvicorn_server:app",
        host="0.0.0.0",
        port=8000,
        workers=args.workers,
        log_level="error",
    )
