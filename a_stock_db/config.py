"""
配置文件
"""
import os

# 数据库
DB_PATH = os.path.join(os.path.dirname(__file__), "a_stock.db")

# 日线数据源: "baostock" | "mxdata"
# 可通过环境变量 DAILY_DATA_SOURCE 覆盖
DAILY_DATA_SOURCE = os.getenv("DAILY_DATA_SOURCE", "mxdata")

# 妙想 API Key（优先从环境变量 MX_APIKEY 读取）
MX_APIKEY = os.getenv("MX_APIKEY", "")

# 分时数据保留天数
MINUTE_KEEP_DAYS = 5

# 请求间隔（秒），避免触发风控
REQUEST_DELAY = 0.3

# 分时获取股票数量限制，None表示全部
MINUTE_STOCK_LIMIT = None

# 日线数据获取天数范围
DAILY_HISTORY_DAYS = 365

# 日线数据复权类型: qfq=前复权 hfq=后复权
ADJUST = "qfq"

# 交易时段
TRADING_HOURS = {
    "morning_start": "09:30",
    "morning_end": "11:30",
    "afternoon_start": "13:00",
    "afternoon_end": "15:00",
}

# 可交易的市场配置
# True = 拉取数据，False = 不拉取
ENABLED_EXCHANGES = {
    'SH': True,   # 沪市主板
    'SZ': True,   # 深市主板
    'BJ': False,  # 北交所
    'CY': False,  # 创业板（深市 0/3开头）
    'KC': False,  # 科创板（沪市 688开头）
}

# 股票类型映射（用于分类股票）
def get_stock_type(code: str) -> str:
    """根据股票代码判断所属市场"""
    if code.startswith('688'):
        return 'KC'  # 科创板
    elif code.startswith('6'):
        return 'SH'  # 沪市主板
    elif code.startswith('3'):
        return 'CY'  # 创业板
    elif code.startswith('0') or code.startswith('0'):
        return 'SZ'  # 深市主板
    elif code.startswith('4') or code.startswith('8') or code.startswith('92'):
        return 'BJ'  # 北交所
    else:
        return 'OTHER'
