"""数据库模型定义。

包含用户账户、支付规则以及交易记录的模型。
符合 Google Python Style Guide。
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    """用户账户模型。"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # 账户余额
    balance = Column(Float, default=0.0)
    
    # 支付规则：每日最高消费上限
    daily_limit = Column(Float, default=1000.0)
    
    # 关系映射
    whitelist = relationship("WhitelistItem", back_populates="owner", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="owner")

class WhitelistItem(Base):
    """Merchant whitelist model with per-transaction limits."""
    __tablename__ = "whitelist"

    id = Column(Integer, primary_key=True, index=True)
    merchant_name = Column(String, index=True, nullable=False)
    max_per_transaction = Column(Float, default=500.0) # Default limit per transaction
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="whitelist")

class Transaction(Base):
    """交易记录模型。"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    merchant_name = Column(String, nullable=True)  # 若为充值则为空
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # 'payment' 或 'deposit'
    status = Column(String, default="success") # 'success' 或 'failed'
    request_id = Column(String, nullable=True) 
    order_id = Column(String, nullable=True)
    failed_reason = Column(String, nullable=True)
    onchain_hash = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="transactions")

class AuditRecord(Base):
    """交易上链审计记录模型。"""
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    transaction_data = Column(String, nullable=False)  # 原始 JSON 数据
    data_hash = Column(String, nullable=False)         # 数据的哈希
    tx_hash = Column(String, nullable=False)           # 链上交易哈希
    timestamp = Column(DateTime, default=datetime.utcnow)
