from app.core.config import settings
from web3 import Web3
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_HARDHAT_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bac478cbed5efcae"


class BlockchainService:
    def __init__(self):
        self.rpc_url = (
            os.getenv("BLOCKCHAIN_RPC_URL")
            or os.getenv("RPC_URL")
            or settings.BLOCKCHAIN_RPC_URL
            or "http://127.0.0.1:8545"
        )
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 20}))
        self.contract = None
        self.contract_address = None
        self.abi = None
        self.network_name = "localhost"
        self.private_key = (
            os.getenv("BLOCKCHAIN_PRIVATE_KEY")
            or os.getenv("PRIVATE_KEY")
            or settings.BLOCKCHAIN_PRIVATE_KEY
            or None
        )
        self.account_address = None
        self._last_error = None
        self._backend_config_path = None
        self._address_file_path = Path(__file__).resolve().parents[3] / "contract-address.json"
        self._resolve_config_paths()
        self._load_config()
        self._ensure_connection()

    def calculate_hash(self, file_content: bytes) -> str:
        return hashlib.sha256(file_content).hexdigest()

    def _resolve_config_paths(self) -> None:
        candidate_paths = [
            Path(__file__).resolve().parent / "blockchain_config.json",
            Path(__file__).resolve().parents[1] / "blockchain_config.json",
            Path(__file__).resolve().parents[2] / "app" / "blockchain_config.json",
            Path(__file__).resolve().parents[3] / "backend" / "app" / "blockchain_config.json",
            Path(__file__).resolve().parents[3] / "backend" / "blockchain_config.json",
        ]

        for candidate_path in candidate_paths:
            if candidate_path.exists():
                self._backend_config_path = candidate_path
                break

        if not self._backend_config_path:
            self._backend_config_path = Path(__file__).resolve().parents[3] / "backend" / "app" / "blockchain_config.json"

    def _resolve_contract_address(self) -> Optional[str]:
        candidate_paths = [
            self._address_file_path,
            Path(__file__).resolve().parents[2] / "contract-address.json",
            Path(__file__).resolve().parents[3] / "backend" / "contract-address.json",
        ]

        for candidate_path in candidate_paths:
            if not candidate_path.exists():
                continue
            try:
                with candidate_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                address = payload.get("contract_address") or payload.get("address")
                if address:
                    return address
            except Exception as exc:
                print(f"[Blockchain] Unable to read contract address from {candidate_path}: {exc}")

        return None

    def _load_config(self) -> None:
        if self._backend_config_path.exists():
            try:
                with self._backend_config_path.open("r", encoding="utf-8") as handle:
                    config = json.load(handle)

                self.contract_address = self.contract_address or config.get("contract_address") or config.get("contractAddress") or config.get("address")
                self.abi = config.get("abi") or self.abi
                self.rpc_url = config.get("rpc_url") or config.get("rpcUrl") or self.rpc_url
                self.network_name = config.get("network") or config.get("networkName") or self.network_name
                print(f"Loaded blockchain config for {self.network_name}: {self.contract_address}")
            except Exception as exc:
                self._last_error = f"Failed to load blockchain config: {exc}"
                print(self._last_error)

        address_from_file = self._resolve_contract_address()
        if address_from_file:
            self.contract_address = address_from_file

    def _ensure_connection(self) -> bool:
        self._load_config()

        if not self.rpc_url:
            self._last_error = "RPC URL is not configured."
            return False

        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 20}))
            if not self.w3.is_connected():
                raise ConnectionError("RPC unavailable")

            if not self.private_key and self.rpc_url.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0")):
                self.private_key = DEFAULT_HARDHAT_PRIVATE_KEY

            if self.private_key:
                try:
                    self.account_address = self.w3.eth.account.from_key(self.private_key).address
                except Exception as exc:
                    self._last_error = f"Invalid private key: {exc}"
                    self.account_address = None
                    return False
            else:
                self.account_address = None

            if self.contract_address and self.abi:
                try:
                    self.contract = self.w3.eth.contract(address=self.w3.to_checksum_address(self.contract_address), abi=self.abi)
                except Exception as exc:
                    self._last_error = f"Failed to load contract: {exc}"
                    self.contract = None
                    return False
            else:
                self.contract = None

            self._last_error = None
            return True
        except Exception as exc:
            self.contract = None
            self._last_error = str(exc)
            return False

    def _classify_error(self, error: Exception) -> Dict[str, Any]:
        message = str(error).lower()
        if "insufficient funds" in message or ("funds" in message and "gas" in message):
            return {"blockchain_status": "failed", "error": "Insufficient funds for transaction."}
        if "invalid private key" in message or "hex has invalid length" in message or ("private key" in message and "invalid" in message):
            return {"blockchain_status": "failed", "error": "Invalid private key."}
        if any(token in message for token in ["connection", "timeout", "econnrefused", "network error", "429", "fetch failed", "temporarily unavailable", "rpc unavailable"]):
            return {"blockchain_status": "failed", "error": "RPC unavailable."}
        if "contract" in message or "not found" in message or "no code" in message:
            return {"blockchain_status": "failed", "error": "Contract not found or not deployed."}
        if "revert" in message or "reverted" in message or "execution reverted" in message:
            return {"blockchain_status": "failed", "error": "Transaction reverted."}
        return {"blockchain_status": "failed", "error": str(error)}

    def _format_contract_record(self, evidence_data) -> Optional[dict]:
        """Convert on-chain evidence tuple into a normalized record."""
        if not evidence_data or not evidence_data[0]:
            return None

        timestamp_unix = evidence_data[5]
        timestamp_str = datetime.fromtimestamp(timestamp_unix).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "evidence_id": evidence_data[0],
            "stored_hash": evidence_data[1],
            "file_type": evidence_data[2],
            "case_id": evidence_data[3],
            "uploader_role": evidence_data[4],
            "timestamp": timestamp_str,
            "previous_hash": evidence_data[6],
            "uploader_address": evidence_data[7],
            "provider": f"{self.network_name} (EvidenceRegistry)",
            "contract_address": self.contract_address,
            "chain_id": self.w3.eth.chain_id if self.w3.is_connected() else None,
            "network": self.rpc_url,
        }

    def get_evidence_chain_record(self, evidence_id: str) -> dict:
        if self._ensure_connection() and self.contract:
            try:
                evidence_data = self.contract.functions.getEvidence(evidence_id).call()
                contract_record = self._format_contract_record(evidence_data)
                if contract_record:
                    return contract_record
            except Exception as exc:
                print(f"[Blockchain] Contract query error: {exc}")

        return {
            "evidence_id": evidence_id,
            "stored_hash": None,
            "file_type": None,
            "case_id": None,
            "uploader_role": None,
            "timestamp": None,
            "previous_hash": None,
            "tx_hash": None,
            "provider": "Blockchain Unavailable",
            "contract_address": self.contract_address,
            "chain_id": self.w3.eth.chain_id if self.w3.is_connected() else None,
            "network": self.rpc_url,
        }

    def store_hash_on_chain(
        self,
        case_id: str,
        evidence_id: str,
        file_hash: str,
        file_type: str,
        uploader_role: str,
        previous_hash: str = None
    ):
        previous_hash = previous_hash or ""
        chain_id = self.w3.eth.chain_id if self.w3.is_connected() else None
        result = {
            "tx_hash": None,
            "provider": None,
            "contract_address": self.contract_address,
            "chain_id": chain_id,
            "network": self.rpc_url,
            "block_number": None,
            "gas_used": None,
            "timestamp": str(datetime.now()),
            "evidence_id": evidence_id,
            "case_id": case_id,
            "file_hash": file_hash,
            "stored_hash": file_hash,
            "file_type": file_type,
            "uploader_role": uploader_role,
            "previous_hash": previous_hash,
            "blockchain_status": "pending",
        }

        if not self._ensure_connection():
            result.update({
                "tx_hash": None,
                "provider": "Blockchain Unavailable",
                "chain_id": self.w3.eth.chain_id if self.w3.is_connected() else None,
                "block_number": None,
                "gas_used": None,
                "stored_hash": file_hash,
                "blockchain_status": "failed",
                "error": self._last_error or "Blockchain unavailable",
            })
            return result

        if not self.contract:
            result.update({
                "tx_hash": None,
                "provider": "Blockchain Unavailable",
                "chain_id": self.w3.eth.chain_id if self.w3.is_connected() else None,
                "block_number": None,
                "gas_used": None,
                "stored_hash": file_hash,
                "blockchain_status": "failed",
                "error": "Contract not found or not deployed.",
            })
            return result

        try:
            print("\n==================== BLOCKCHAIN ====================")
            print(f"Connecting to {self.network_name}...")
            print(f"Evidence ID : {evidence_id}")
            print(f"Case ID     : {case_id}")
            print(f"File Hash   : {file_hash}")

            chain_id = self.w3.eth.chain_id
            nonce = self.w3.eth.get_transaction_count(self.account_address)
            tx = self.contract.functions.anchorEvidence(
                evidence_id,
                file_hash,
                file_type,
                case_id,
                uploader_role,
                previous_hash,
            ).build_transaction({
                "from": self.account_address,
                "nonce": nonce,
                "gas": 2000000,
                "gasPrice": self.w3.to_wei("20", "gwei"),
                "chainId": chain_id,
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

            if receipt.status != 1:
                raise ValueError("Transaction reverted.")

            result.update({
                "tx_hash": tx_hash.hex(),
                "provider": f"{self.network_name} (EvidenceRegistry)",
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "timestamp": str(datetime.now()),
                "stored_hash": file_hash,
                "blockchain_status": "confirmed",
            })

            try:
                on_chain_data = self.contract.functions.getEvidence(evidence_id).call()
                on_chain_hash = on_chain_data[1] if on_chain_data and len(on_chain_data) > 1 else None
                result["on_chain_hash"] = on_chain_hash
                print(f"On-chain Stored Hash : {on_chain_hash}")
            except Exception as read_err:
                print(f"Failed to read back on-chain evidence: {read_err}")

            print("\n====================================================")
            print("✅ BLOCKCHAIN TRANSACTION SUCCESSFUL")
            print("====================================================")
            print(f"Transaction Hash : {result['tx_hash']}")
            print(f"Block Number     : {result['block_number']}")
            print(f"Gas Used         : {result['gas_used']}")
            print(f"Contract Address : {self.contract_address}")
            print(f"Evidence ID      : {evidence_id}")
            print(f"Case ID          : {case_id}")
            print("====================================================\n")

            return result

        except Exception as exc:
            failure = self._classify_error(exc)
            result.update({
                "tx_hash": tx_hash.hex() if "tx_hash" in locals() else None,
                "provider": "Blockchain Unavailable",
                "block_number": None,
                "gas_used": None,
                "stored_hash": file_hash,
                "blockchain_status": failure["blockchain_status"],
                "error": failure["error"],
            })
            print("\n====================================================")
            print("❌ BLOCKCHAIN TRANSACTION FAILED")
            print(failure["error"])
            print("====================================================\n")
            return result

    def verify_integrity(self, evidence_id: str, computed_hash: str) -> dict:
        """Verifies if the computed hash matches the stored hash on-chain."""
        if self._ensure_connection() and self.contract:
            try:
                is_valid = self.contract.functions.verifyHash(evidence_id, computed_hash).call()
                evidence_data = self.contract.functions.getEvidence(evidence_id).call()
                if evidence_data and evidence_data[0]:
                    timestamp_unix = evidence_data[5]
                    timestamp_str = datetime.fromtimestamp(timestamp_unix).strftime("%Y-%m-%d %H:%M:%S")

                    print(f"[Blockchain] Found on-chain. Stored: {evidence_data[1]} | Computed: {computed_hash} | Match: {is_valid}")
                    return {
                        "verified": is_valid,
                        "status": "VERIFIED" if is_valid else "TAMPERED",
                        "details": "Hash matches blockchain record." if is_valid else "Hash MISMATCH — file altered after upload!",
                        "provider": f"{self.network_name} (EvidenceRegistry)",
                        "blockchain_record": {
                            "timestamp": timestamp_str,
                            "uploader_role": evidence_data[4],
                            "stored_hash": evidence_data[1],
                            "contract_address": self.contract_address,
                            "chain_id": self.w3.eth.chain_id if self.w3.is_connected() else None,
                            "block_number": None,
                            "gas_used": None,
                            "network": self.rpc_url,
                        },
                    }
            except Exception as exc:
                print(f"[Blockchain] Contract query error: {exc}")

        return {
            "verified": False,
            "status": "NOT_FOUND",
            "details": "Evidence ID not found in blockchain contract.",
            "provider": "Blockchain Unavailable",
            "blockchain_record": {"stored_hash": ""},
        }


blockchain = BlockchainService()
