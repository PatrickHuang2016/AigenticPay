import os
import solcx
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Install solc compiler
solcx.install_solc('0.8.20')
solcx.set_solc_version('0.8.20')

# Source code
contract_source_code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AigenticAudit {
    address public owner;
    event RecordPosted(bytes32 indexed emailHash, string data);
    constructor() { owner = msg.sender; }
    
    // Using a simple require.
    function postRecord(bytes32 emailHash, string memory data) public {
        require(msg.sender == owner, "Only owner can post");
        emit RecordPosted(emailHash, data);
    }
}
"""

compiled_sol = solcx.compile_source(
    contract_source_code,
    output_values=['abi', 'bin'],
    evm_version='paris' # ensures no PUSH0 compatibility issues on older EVM networks
)

contract_id, contract_interface = compiled_sol.popitem()

bytecode = contract_interface['bin']
abi = contract_interface['abi']

RPC_URL = "https://testnet.skalenodes.com/v1/juicy-low-small-testnet"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

priv_key = os.environ.get("SKALE_PRIVATE_KEY")
if not priv_key.startswith("0x"):
    priv_key = "0x" + priv_key

account = w3.eth.account.from_key(priv_key)
AuditContract = w3.eth.contract(abi=abi, bytecode=bytecode)

nonce = w3.eth.get_transaction_count(account.address)

tx = AuditContract.constructor().build_transaction({
    'chainId': 1444673419,
    'gasPrice': w3.eth.gas_price,
    'from': account.address,
    'nonce': nonce,
    'gas': 3000000
})

signed_tx = w3.eth.account.sign_transaction(tx, priv_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print("Deploying contract... tx:", w3.to_hex(tx_hash))
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print("NEW_CONTRACT_ADDRESS:", receipt.contractAddress)

