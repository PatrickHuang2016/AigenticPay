"""主应用入口。

包含支付网关 API、用户管理 API 以及静态文件服务。
符合 Google Python Style Guide。
"""

from datetime import datetime, date
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from . import models, schemas, auth, database
from .database import engine, get_db, Base
from .audit_manager import AuditManager

# Ensure all models are loaded for metadata
from . import models

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AigenticPay",
    description="""
    Next-generation secure payment gateway system.
    
    ### Features:
    * **Auth**: Registration & JWT Authentication.
    * **Users**: Profile, balance, and transaction history.
    * **Rules**: Daily limits & Smart merchant whitelist with per-tx caps.
    * **Gateway**: Simulated 3rd party merchant payment requests.
    """,
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置跨域请求 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 辅助函数 ---

def perform_onchain_audit(user_email: str, tx_data: dict, transaction_id: int = None):
    """在后台执行上链审计，不阻塞主接口响应。"""
    from .database import SessionLocal
    db = SessionLocal()
    try:
        audit = AuditManager(db)
        # 将交易字典转为 JSON 字符串上传
        audit.upload_audit_record(user_email, json.dumps(tx_data, default=str), transaction_id)
    except Exception as e:
        import logging
        logging.error(f"Background audit failed for {user_email}: {e}")
    finally:
        db.close()

# --- 身份认证接口 ---

@app.post("/api/token", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: schemas.UserLogin, # 这里使用新的 UserLogin 而不是带有 address 的 UserCreate
    db: Session = Depends(get_db)
):
    """用户登录获取令牌。"""
    user = db.query(models.User).filter(models.User.email == form_data.email).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/register", response_model=schemas.User, tags=["Authentication"])
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """注册新用户。"""
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="This email is already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        address=user.address,
        virtual_card_enabled=False,
        balance=0.0,
        daily_limit=1000.0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- 用户管理接口 (需要认证) ---

@app.get("/api/me", response_model=schemas.User, tags=["User Management"])
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """获取当前用户信息。"""
    return current_user

@app.put("/api/rules", response_model=schemas.User, tags=["Payment Rules"])
async def update_rules(
    rules: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """更新支付规则（如日限额）。"""
    if rules.daily_limit is not None:
        current_user.daily_limit = rules.daily_limit
    if rules.virtual_card_enabled is not None:
        current_user.virtual_card_enabled = rules.virtual_card_enabled
    db.commit()
    return current_user
    
@app.get("/api/whitelist", response_model=List[schemas.WhitelistItem], tags=["Payment Rules"])
async def get_whitelist(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """获取用户的商户白名单。"""
    return current_user.whitelist

@app.post("/api/whitelist", response_model=schemas.WhitelistItem, tags=["Payment Rules"])
async def add_to_whitelist(
    item: schemas.WhitelistItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Add merchant to whitelist with smart duplicate/fuzzy detection."""
    from difflib import SequenceMatcher
    
    # helper for string similarity
    def similar(a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    # 1. Exact case-insensitive check
    existing = db.query(models.WhitelistItem).filter(
        models.WhitelistItem.user_id == current_user.id,
        func.lower(models.WhitelistItem.merchant_name) == item.merchant_name.lower()
    ).first()

    if existing:
        if item.force_update:
            existing.max_per_transaction = item.max_per_transaction
            db.commit()
            db.refresh(existing)
            return existing
        else:
            raise HTTPException(
                status_code=409, 
                detail=f"Merchant '{existing.merchant_name}' already exists. Change limit from ${existing.max_per_transaction:.2f} to ${item.max_per_transaction:.2f}?"
            )

    # 2. Fuzzy match check
    if not item.skip_fuzzy:
        all_merchants = db.query(models.WhitelistItem).filter(models.WhitelistItem.user_id == current_user.id).all()
        for m in all_merchants:
            if similar(m.merchant_name, item.merchant_name) > 0.7: # Threshold for similarity
                if not item.force_update:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Found similar merchant: '{m.merchant_name}' (Current Limit: ${m.max_per_transaction:.2f}). Is this the same merchant?"
                    )

    # 3. Create new if no match found
    db_item = models.WhitelistItem(
        merchant_name=item.merchant_name, 
        max_per_transaction=item.max_per_transaction,
        user_id=current_user.id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/whitelist/{item_id}", tags=["Payment Rules"])
async def remove_from_whitelist(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """从白名单移除商户。"""
    item = db.query(models.WhitelistItem).filter(
        models.WhitelistItem.id == item_id,
        models.WhitelistItem.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Whitelist item not found")
    db.delete(item)
    db.commit()
    return {"message": "Merchant removed from whitelist"}

@app.post("/api/deposit", response_model=schemas.User, tags=["Wallet & Transactions"])
async def deposit_funds(
    request: schemas.DepositRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Deposit funds to account."""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    current_user.balance += request.amount
    
    # 记录充值交易
    transaction = models.Transaction(
        user_id=current_user.id,
        amount=request.amount,
        type="deposit"
    )
    db.add(transaction)
    db.commit()
    db.refresh(current_user)

    # 触发审计上链
    background_tasks.add_task(
        perform_onchain_audit, 
        current_user.email, 
        {"type": "deposit", "amount": request.amount, "timestamp": datetime.utcnow()},
        transaction.id
    )

    return current_user

@app.get("/api/transactions", response_model=List[schemas.Transaction], tags=["Wallet & Transactions"])
async def get_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """获取个人交易记录。"""
    return db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    ).order_by(models.Transaction.timestamp.desc()).all()

# --- 核心支付网关接口 (不对外直接暴露 Token，通过 identity 识别) ---

@app.post("/api/pay", response_model=schemas.PaymentResponse, tags=["Payment Gateway"])
async def process_payment(
    payment: schemas.PaymentRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """支付网关逻辑入口。"""
    import uuid
    import random
    
    # 1. Generate Request ID
    req_id = "REQ-" + str(uuid.uuid4())[:8].upper()
    
    # 2. User Look-up
    user = db.query(models.User).filter(models.User.email == payment.identity).first()
    if not user:
        return schemas.PaymentResponse(status="error", message="User not found", request_id=req_id)

    # Helper function to log transaction
    def log_tx(status: str, msg: str, order_id: str = None, failed_reason: str = None):
        new_tx = models.Transaction(
            user_id=user.id,
            merchant_name=payment.merchant_name,
            amount=payment.amount,
            type="payment",
            status=status,
            request_id=req_id,
            order_id=order_id,
            failed_reason=failed_reason,
            virtual_card_number=None
        )
        db.add(new_tx)
        db.commit()
        db.refresh(new_tx)
        return new_tx

    # 3. Rule Check - Whitelist & Per-transaction limit
    whitelist_entry = db.query(models.WhitelistItem).filter(
        models.WhitelistItem.user_id == user.id,
        models.WhitelistItem.merchant_name == payment.merchant_name
    ).first()
    
    if not whitelist_entry:
        log_tx("failed", f"Merchant '{payment.merchant_name}' is not in whitelist", failed_reason="Merchant not whitelisted")
        return schemas.PaymentResponse(status="error", message=f"Merchant '{payment.merchant_name}' is not in your whitelist", request_id=req_id)

    if payment.amount > whitelist_entry.max_per_transaction:
        log_tx("failed", f"Amount exceeds individual limit for '{payment.merchant_name}'", failed_reason=f"Exceeds merchant limit (${whitelist_entry.max_per_transaction})")
        return schemas.PaymentResponse(
            status="error", 
            message=f"Amount exceeds individual limit for '{payment.merchant_name}' (Max: ${whitelist_entry.max_per_transaction})",
            request_id=req_id
        )

    # 4. Rule Check - Daily Limit
    today = date.today()
    spent_today = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user.id,
        models.Transaction.type == "payment",
        models.Transaction.status == "success", # Only count successful payments
        func.date(models.Transaction.timestamp) == today
    ).scalar() or 0.0

    if spent_today + payment.amount > user.daily_limit:
        log_tx("failed", "Daily spending limit exceeded", failed_reason=f"Exceeds daily limit (${user.daily_limit})")
        return schemas.PaymentResponse(status="error", message="Daily spending limit exceeded", request_id=req_id)

    # 5. Balance Check
    if user.balance < payment.amount:
        log_tx("failed", "Insufficient balance", failed_reason="Insufficient account balance")
        return schemas.PaymentResponse(status="error", message="Insufficient balance", request_id=req_id)

    # 6. Execute Payment (Atomic)
    try:
        ord_id = "ORD-" + str(random.randint(100000, 999999))
        
        # Virtual Card generation
        vcard_num = None
        exp_date = None
        cvv = None
        billing_addr = None

        if user.virtual_card_enabled:
            # To support strict 10-minute expiration burn cards
            from datetime import timedelta
            vcard_num = f"4111 {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"
            expire_time = datetime.now() + timedelta(minutes=10)
            exp_date = expire_time.strftime("%Y-%m-%d %H:%M:%S")
            cvv = f"{random.randint(100, 999):03d}"
            billing_addr = user.address

        user.balance -= payment.amount
        
        # Insert success manually to attach virtual_card_number
        transaction = models.Transaction(
            user_id=user.id,
            merchant_name=payment.merchant_name,
            amount=payment.amount,
            type="payment",
            status="success",
            request_id=req_id,
            order_id=ord_id,
            virtual_card_number=vcard_num
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        # 触发审计上链
        background_tasks.add_task(
            perform_onchain_audit, 
            user.email, 
            {
                "type": "payment", 
                "merchant": payment.merchant_name,
                "amount": payment.amount, 
                "order_id": ord_id,
                "request_id": req_id
            },
            transaction.id
        )

        return schemas.PaymentResponse(
            status="success",
            message="Payment successful",
            request_id=req_id,
            transaction_id=transaction.id,
            order_id=ord_id,
            virtual_card_number=vcard_num,
            exp_date=exp_date,
            cvv=cvv,
            billing_address=billing_addr
        )
    except Exception as e:
        db.rollback()
        return schemas.PaymentResponse(status="error", message=f"Processing failed: {str(e)}", request_id=req_id)

# 挂载静态文件
app.mount("/", StaticFiles(directory="static", html=True), name="static")
