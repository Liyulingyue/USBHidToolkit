import uvicorn

if __name__ == "__main__":
    # 启动 FastAPI 服务
    # 默认端口 8000，支持热重载
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
