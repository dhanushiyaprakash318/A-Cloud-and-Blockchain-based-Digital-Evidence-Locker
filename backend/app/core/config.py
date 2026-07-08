from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

# Load backend-related .env files early so values override stale process environment variables.
# Search workspace root, backend root, and blockchain root for .env files.
root_dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
backend_dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
project_root = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

blockchain_dotenv_path = os.path.join(project_root, "blockchain", ".env")
print("Root .env:", root_dotenv_path)
print("Backend .env:", backend_dotenv_path)
print("Blockchain .env:", blockchain_dotenv_path)
for dotenv_path in (root_dotenv_path, backend_dotenv_path, blockchain_dotenv_path):
    print("Checking:", dotenv_path)

    if os.path.exists(dotenv_path):
        print("Loaded:", dotenv_path)
        load_dotenv(dotenv_path, override=True)
    else:
        print("Not Found:", dotenv_path)

class Settings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Digital Evidence Locker Backend"
    
    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "eu-north-1"
    AWS_SESSION_TOKEN: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    DYNAMODB_TABLE_CASES: Optional[str] = None
    DYNAMODB_TABLE_EVIDENCE: Optional[str] = None
    S3_ENCRYPTION: Optional[str] = "AES256"  # Options: AES256, aws:kms, None
    S3_KMS_KEY_ID: Optional[str] = None

    # Blockchain
    BLOCKCHAIN_RPC_URL: str = "http://127.0.0.1:8545"
    BLOCKCHAIN_CONTRACT_ADDRESS: Optional[str] = None
    BLOCKCHAIN_PRIVATE_KEY: Optional[str] = None

    # AI
    GEMINI_API_KEY: Optional[str] = None
    AI_PROVIDER: str = "gemini" # Options: gemini, local
    OLLAMA_BASE_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "llama3"
    # Fallback behavior for assistant when DB has no data.
    # Options: 'strict' - only DB answers; 'hybrid' - fallback to LLM with disclaimer; 'general' - always use LLM
    AI_FALLBACK_MODE: str = "hybrid"

    # Security
    SECRET_KEY: str = "supersecretkeydefaultsfortestingonly"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        extra="ignore"
    )

settings = Settings()
print("BLOCKCHAIN_RPC_URL =", settings.BLOCKCHAIN_RPC_URL)
# Report whether a private key is available under either supported name
print(
    "BLOCKCHAIN_PRIVATE_KEY exists =",
    (settings.BLOCKCHAIN_PRIVATE_KEY is not None) or bool(os.getenv("PRIVATE_KEY")) or bool(os.getenv("BLOCKCHAIN_PRIVATE_KEY"))
)