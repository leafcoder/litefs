#!/usr/bin/env python
# coding: utf-8

from fastapi import FastAPI

# 创建 FastAPI 应用
app = FastAPI()

# 只返回 "Hello world" 的端点
@app.get("/")
def hello():
    return "Hello world"

# Gunicorn 配置
"""
# gunicorn.conf.py
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8001"
"""
