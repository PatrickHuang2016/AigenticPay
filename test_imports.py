try:
    from app import main, auth, models, schemas, database
    print("Imports successful")
except Exception as e:
    import traceback
    traceback.print_exc()
