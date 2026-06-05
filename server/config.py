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
HOST = "::"  # 同时监听 IPv4 和 IPv6
PORT = 8000

# AI 模型配置（兼容 OpenAI 格式，智谱/Anthropic 代理等）
# 已预配置为用户的智谱代理，如需更换可修改以下值
AI_API_KEY = os.getenv("AI_API_KEY", "sk-f65e2e243803ec772634d9c2b5987ad8")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://aicoding-proxy.myunke.com/cn-cch")
AI_MODEL = os.getenv("AI_MODEL", "glm-5")
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "60"))
