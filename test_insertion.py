from app.database import SessionLocal
from app.models import User, Transaction, WhitelistItem
from app.schemas import PaymentRequest

db = SessionLocal()
payment = PaymentRequest(identity="test@test.com", merchant_name="netflix", amount=15.49)

user = db.query(User).filter(User.email == payment.identity).first()
if not user:
    # mock a user
    user = User(email="test@test.com", hashed_password="fake", balance=1000)
    db.add(user)
    db.commit()

whitelist_entry = db.query(WhitelistItem).filter(
    WhitelistItem.user_id == user.id,
    WhitelistItem.merchant_name == payment.merchant_name
).first()

if not whitelist_entry:
    print("Merchant not in whitelist")
    new_tx = Transaction(
        user_id=user.id,
        merchant_name=payment.merchant_name,
        amount=payment.amount,
        type="payment",
        status="failed",
        request_id="REQ-123",
        order_id=None,
        failed_reason="Merchant not whitelisted"
    )
    db.add(new_tx)
    try:
        db.commit()
        print("Success committing tx")
    except Exception as e:
        print("Crash:", e)
