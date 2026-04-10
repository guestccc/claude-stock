"""启动 FastAPI 服务器"""
import uvicorn
from server.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=True)
