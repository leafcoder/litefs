#!/usr/bin/env python
# coding: utf-8

from fastapi import FastAPI

# 创建 FastAPI 应用
app = FastAPI()

# 只返回 "Hello world" 的端点
@app.get("/")
def hello():
    return "Hello world"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="critical")
