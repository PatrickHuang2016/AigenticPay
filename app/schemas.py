"""Pydantic 数据验证模型 (Schemas)。

定义 API 的请求与响应结构。
符合 Google Python Style Guide。
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

# --- 用户认证相关 ---

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    daily_limit: Optional[float] = None

class User(UserBase):
    id: int
    balance: float
    daily_limit: float

    class Config:
        from_attributes = True

# --- 白名单相关 ---

class WhitelistItemBase(BaseModel):
    merchant_name: str
    max_per_transaction: float = 500.0

class WhitelistItemCreate(WhitelistItemBase):
    force_update: Optional[bool] = False
    skip_fuzzy: Optional[bool] = False

class WhitelistItem(WhitelistItemBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

# --- 交易与支付相关 ---

class TransactionBase(BaseModel):
    amount: float
    type: str  # 'payment' or 'deposit'
    merchant_name: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    status: str
    request_id: Optional[str] = None
    order_id: Optional[str] = None
    failed_reason: Optional[str] = None
    onchain_hash: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class PaymentRequest(BaseModel):
    """网关支付请求模型。"""
    identity: EmailStr
    merchant_name: str
    amount: float

class PaymentResponse(BaseModel):
    """网关支付响应模型。"""
    status: str
    message: str
    request_id: Optional[str] = None
    transaction_id: Optional[int] = None
    order_id: Optional[str] = None

# --- 其他 ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class DepositRequest(BaseModel):
    amount: float
