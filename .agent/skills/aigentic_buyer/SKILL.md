---
name: Aigentic Buyer Agent
description: An autonomous shopping agent skill that evaluates product requests and uses the local AigenticPay API gateway to complete payments.
---

# Aigentic Buyer Agent Skill

This skill empowers you (the Assistant) to act as an autonomous agent that can purchase items on behalf of the user using the AigenticPay API.

## Workflow

When the user asks you to "buy [Item]" or perform a similar purchasing action, follow these exact steps:

### 1. Evaluate and Determine Details
Determine the likely real-world price of the item and the appropriate merchant to buy it from. When selecting a merchant, try to use real-world names that align with typical Merchant Category Codes (MCC) to test the user's spending limits. For example:
- **Retail**: "Nike", "Apple", "Best Buy"
- **Grocery**: "Whole Foods", "Walmart"
- **Fast Food / Restaurants**: "McDonalds", "Starbucks"
- **Ride Shares**: "Uber", "Lyft"
- **Other**: "Coursera", "Steam", "Amazon" (These will fall into the default 'Other' category limit of $50)
You can estimate the price or make a realistic guess if not provided.

### 2. Confirm the User Identity (Email)
Ask the user for their registered `email` if you don't already have it in context, as the payment gateway requires an identity to process their rules and balance.

### 3. Execute the Payment
Use the `run_command` tool to execute the `buy.py` script located in this skill folder. This script natively points to the production AigenticPay backend at `https://aigenticpay.onrender.com/api/pay`.

**Command syntax**:
```bash
.\.venv\Scripts\python.exe .agent\skills\aigentic_buyer\scripts\buy.py --user "<USER_EMAIL>" --merchant "<MERCHANT_NAME>" --amount <AMOUNT>
```

### 4. Analyze the Response
The script will output the JSON response from the Payment Gateway.

- **If Status == "success"**: Celebrate! Tell the user the payment was approved, and that their autonomous auditing system has securely logged the transaction hash directly to the SKALE blockchain.
- **If Status == "error"**: Pay attention to the error message (e.g., *Merchant not whitelisted*, *Amount exceeds individual limit*, *Daily limit exceeded*, or *Insufficient balance*). Explain to the user *why* their payment rules blocked you (the agent) from completing the transaction, demonstrating the security of the AigenticPay system.
