"""数据库配置与会话管理。

符合 Google Python Style Guide。
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 使用 SQLite 作为开发环境数据库
# Use a fresh filename to ensure schema updates are applied
SQLALCHEMY_DATABASE_URL = "sqlite:///./aigentic_pay_prod.db"

# 创建数据库引擎
# check_same_thread=False 仅对 SQLite 是必需的
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类，供模型继承
Base = declarative_base()


def get_db():
    """获取数据库会话的依赖项。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
