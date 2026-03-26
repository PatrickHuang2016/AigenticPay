import traceback
from app.database import SessionLocal
from app.audit_manager import AuditManager

db = SessionLocal()
try:
    audit = AuditManager(db)
    res = audit.upload_audit_record('test@test.com', '{"amount":1}')
    with open('test_audit_err.txt', 'w', encoding='utf-8') as f:
        f.write('Success: ' + res.tx_hash)
except Exception as e:
    with open('test_audit_err.txt', 'w', encoding='utf-8') as f:
        f.write('ERROR: ' + str(e) + '\n')
        traceback.print_exc(file=f)
finally:
    db.close()
