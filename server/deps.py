"""共享依赖：数据库 session 管理"""
from functools import cached_property
from a_stock_db.database import db


def get_session():
    """获取 SQLAlchemy session，用完后自动关闭"""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
