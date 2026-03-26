import traceback
from web3 import Web3
from app.audit_manager import CONTRACT_ABI

RPC_URL = "https://testnet.skalenodes.com/v1/juicy-low-small-testnet"
w3 = Web3(Web3.HTTPProvider(RPC_URL))
addr = w3.to_checksum_address('0x65Eb7434B0E067e80b5645E37f5633E005aca3DD')
contract = w3.eth.contract(address=addr, abi=CONTRACT_ABI)

from_addr = w3.to_checksum_address('0x07CdB2BF47beED16a2BE5CE78Ce14580d1CC9B11')

email_hash = Web3.keccak(text="test@test.com")
data_hash = Web3.to_hex(Web3.keccak(text="{\"amount\":1}"))

try:
    contract.functions.postRecord(email_hash, data_hash).call({'from': from_addr})
    print("Call successful!")
except Exception as e:
    print("Call reverted with:", e)

