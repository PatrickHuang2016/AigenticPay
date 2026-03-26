import urllib.request, json
url = "https://juicy-low-small-testnet.explorer.testnet.skalenodes.com/api?module=contract&action=getsourcecode&address=0x4DBF898193692219f93c717edc7129a7eC633236"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as f:
        data = json.loads(f.read().decode('utf-8'))
        print(data['result'][0]['SourceCode'])
except Exception as e:
    print('ERROR:', e)
