"""数据库配置与会话管理。

符合 Google Python Style Guide。
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 优先读取环境变量中的 DATABASE_URL，一般生产环境由云平台注入
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # SQLAlchemy 1.4+ 强校验：协议必须写 postgresql:// 而不仅仅是 postgres://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # 创建 PostgreSQL 的引擎（不需要 check_same_thread）
    engine = create_engine(DATABASE_URL)
else:
    # 如果没有注入 DATABASE_URL，默认回落使用本地开发环境的 SQLite
    SQLALCHEMY_DATABASE_URL = "sqlite:///./aigentic_pay_prod.db"
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
