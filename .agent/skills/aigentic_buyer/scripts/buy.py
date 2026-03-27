import argparse
import urllib.request
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="AigenticPay Agent Checkout Simulator")
    parser.add_argument("--user", required=True, help="User email identity")
    parser.add_argument("--merchant", required=True, help="Merchant name")
    parser.add_argument("--amount", type=float, required=True, help="Amount to pay")
    parser.add_argument("--url", default="https://aigenticpay.onrender.com/api/pay", help="API URL")
    
    args = parser.parse_args()

    payload = json.dumps({
        "identity": args.user,
        "merchant_name": args.merchant,
        "amount": args.amount
    }).encode('utf-8')

    req = urllib.request.Request(
        args.url, 
        data=payload, 
        headers={'Content-Type': 'application/json'}, 
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode('utf-8'))
            print(json.dumps(res_body, indent=2))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
