from app.core.config import settings
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
        self.contract = None
        self.contract_address = None
        self.abi = None
        self.network_name = "aws-lambda"
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

        print("[Blockchain] Local blockchain disabled. Using AWS Lambda blockchain service.")
        self.contract = None
        self.account_address = None
        self._last_error = None
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

    def get_evidence_chain_record(self, evidence_id: str) -> dict:
        self._ensure_connection()
        return {
            "evidence_id": evidence_id,
            "stored_hash": None,
            "file_type": None,
            "case_id": None,
            "uploader_role": None,
            "timestamp": None,
            "previous_hash": None,
            "tx_hash": None,
            "provider": "AWS Lambda",
            "contract_address": self.contract_address,
            "chain_id": None,
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
        print("[Blockchain] Local blockchain disabled. Using AWS Lambda blockchain service.")
        return {
            "tx_hash": None,
            "provider": "AWS Lambda",
            "contract_address": self.contract_address,
            "chain_id": None,
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
            "blockchain_status": "disabled",
            "message": "Local direct blockchain transactions are disabled; hashes are anchored through AWS Lambda."
        }

    def verify_integrity(self, evidence_id: str, computed_hash: str) -> dict:
        """Verifies hash integrity using the AWS Lambda-backed metadata path."""
        self._ensure_connection()
        return {
            "verified": False,
            "status": "NOT_AVAILABLE",
            "details": "Local blockchain verification is disabled; evidence integrity is tracked through AWS Lambda metadata.",
            "provider": "AWS Lambda",
            "blockchain_record": {"stored_hash": ""},
        }


blockchain = BlockchainService()
