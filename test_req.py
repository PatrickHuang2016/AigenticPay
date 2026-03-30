import urllib.request
import json
req = urllib.request.Request(
    'https://aigenticpay.onrender.com/api/pay', 
    data=b'{"identity":"test@test.com","merchant_name":"amazon","amount":5.00}', 
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read().decode('utf-8'))
except Exception as e:
    print("Error:", e.read().decode('utf-8'))
