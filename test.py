import urllib.request
import json
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/register', 
    data=b'{"email":"test5@test.com","password":"test"}', 
    headers={'Content-Type': 'application/json'}, 
    method='POST'
)
try:
    urllib.request.urlopen(req)
except Exception as e:
    print(e.read().decode())
