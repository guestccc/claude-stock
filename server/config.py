"""服务端配置"""
import os

# 项目根目录（claude-study/）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 数据库路径
DB_PATH = os.path.join(PROJECT_ROOT, "a_stock_db", "a_stock.db")

# FastAPI 配置
API_PREFIX = "/api"
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite 开发服务器
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

# 服务器配置
HOST = "0.0.0.0"
PORT = 8000
