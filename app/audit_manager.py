import os
import json
import logging
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ContractLogicError, TransactionNotFound
from dotenv import load_dotenv

# 加载 .env 文件内容到环境变量中
load_dotenv()

logger = logging.getLogger(__name__)

# --- 配置参数 ---
# 网络: SKALE Europa Testnet
RPC_URL = "https://testnet.skalenodes.com/v1/juicy-low-small-testnet"
CHAIN_ID = 1444673419
CONTRACT_ADDRESS = "0x31B9D837cA7015fe6B2580590a913012e1Fbb97A"
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "emailHash", "type": "bytes32"},
            {"internalType": "string", "name": "data", "type": "string"}
        ],
        "name": "postRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class AuditManager:
    """审计日志管理器：负责将交易记录上传到 SKALE Europa 区块链并在本地数据库存储。"""
    
    def __init__(self, db: Session):
        from . import models
        self.db = db
        self.models = models
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        # 从环境变量读取私钥
        self.private_key = os.environ.get("SKALE_PRIVATE_KEY") or os.environ.get("PRIVATE_KEY")
        if not self.private_key:
            logger.warning("SKALE_PRIVATE_KEY 环境变量未设置！上传到区块链将失败。")
        else:
            if not self.private_key.startswith("0x"):
                self.private_key = "0x" + self.private_key
            self.account = self.w3.eth.account.from_key(self.private_key)
            self.contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(CONTRACT_ADDRESS),
                abi=CONTRACT_ABI
            )


    def upload_audit_record(self, user_email: str, transaction_json: str, transaction_id: int = None):
        """将交易记录发布到 SKALE 合约并通过本地数据库持久化"""
        if not self.private_key:
            raise ValueError("本地未配置私钥，无法发布交易审计链上记录。")

        # 1. 计算哈希 (web3.keccak 返回 bytes)
        email_hash_bytes = Web3.keccak(text=user_email)
        # 获取 transaction_json 哈希用于数据库记录
        data_hash_hex = Web3.to_hex(Web3.keccak(text=transaction_json))

        # 2. 构建并发送区块链交易
        try:
            # 确保地址是一个 Checksum Address
            address = self.account.address
            
            # Nonce 管理（使用 pending 状态获取最新可用的 nonce 避免覆盖问题）
            nonce = self.w3.eth.get_transaction_count(address, 'pending')
            
            # Gas 价格获取（如果可用），对于 SKALE（zero-gas）费用很低甚至为0
            gas_price = self.w3.eth.gas_price

            # 构建基础交易
            tx_base = self.contract.functions.postRecord(
                email_hash_bytes, 
                data_hash_hex
            ).build_transaction({
                'from': address,
                'chainId': CHAIN_ID,
                'gasPrice': gas_price,
                'nonce': nonce,
                'gas': 3000000,
            })
            
                
            # 使用私钥对交易签名
            signed_tx = self.w3.eth.account.sign_transaction(tx_base, self.private_key)
            
            # 发送原始交易
            tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = self.w3.to_hex(tx_hash_bytes)
            logger.info(f"链上交易已发送，Hash: {tx_hash_hex}")

            # 等待确认回调（加入超时控制，开发网通常产块很快）
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)
            
            if receipt['status'] != 1:
                logger.error(f"区块链智能合约执行失败并发生回滚 (Status=0). Hash: {tx_hash_hex}")
                raise Exception(f"区块链交易执行被回退 (Reverted). TX Hash: {tx_hash_hex}")

        except ContractLogicError as cle:
            logger.error(f"智能合约逻辑验证不通过: {cle}")
            raise Exception(f"合约逻辑错误: {cle}")
        except Exception as e:
            logger.error(f"发布上链过程中出现错误: {e}")
            raise Exception(f"审计记录上链失败: {e}")

        # 3. 数据库持久化
        try:
            audit_record = self.models.AuditRecord(
                user_email=user_email,
                transaction_data=transaction_json,
                data_hash=data_hash_hex,
                tx_hash=tx_hash_hex
            )
            self.db.add(audit_record)
            if transaction_id:
                tx = self.db.query(self.models.Transaction).filter(self.models.Transaction.id == transaction_id).first()
                if tx:
                    tx.onchain_hash = tx_hash_hex
            self.db.commit()
            self.db.refresh(audit_record)
            return audit_record
            
        except Exception as db_err:
            self.db.rollback()
            logger.error(f"持久化记录至本地数据库失败 (上链已成功): {db_err}")
            raise Exception(f"数据库记录保存失败: {db_err}")
