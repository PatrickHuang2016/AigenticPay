import requests

BASE_URL = "http://localhost:8000/api"

# 1. Register
print("Registering new user...")
res = requests.post(f"{BASE_URL}/register", json={
    "email": "testmcc@example.com",
    "password": "pass",
    "address": "123 Main St"
})
if res.status_code == 400:
    print("User exists, trying to login...")
    pass # Exists
else:
    print("Registered", res.json())

# 2. Login
res = requests.post(f"{BASE_URL}/token", json={
    "email": "testmcc@example.com",
    "password": "pass"
})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Get MCCs
print("\nGetting MCCs...")
res = requests.get(f"{BASE_URL}/mcc", headers=headers)
print("MCCs:", res.json())

# 4. Deposit
requests.post(f"{BASE_URL}/deposit", json={"amount": 1000}, headers=headers)

# 5. Process Payment - Not in whitelist, matching MCC 5411 (Grocery - $200 limit)
# Under limit
print("\nPayment 1 (Walmart, $150)...")
res = requests.post(f"{BASE_URL}/pay", json={
    "identity": "testmcc@example.com",
    "merchant_name": "Walmart Superstore",
    "amount": 150
})
print(res.json())

# Over limit
print("\nPayment 2 (Walmart, $250)...")
res = requests.post(f"{BASE_URL}/pay", json={
    "identity": "testmcc@example.com",
    "merchant_name": "Walmart Superstore",
    "amount": 250
})
print(res.json())

# Unrecognized
print("\nPayment 3 (Hogwarts, $50)...")
res = requests.post(f"{BASE_URL}/pay", json={
    "identity": "testmcc@example.com",
    "merchant_name": "Hogwarts School",
    "amount": 50
})
print(res.json())

