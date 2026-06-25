from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from app.core import security
from jose import jwt

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class User(BaseModel):
    username: str
    role: str

# Mock user database
FAKE_USERS_DB = {
    "polaris": {"username": "polaris", "password_hash": security.get_password_hash("polaris123"), "role": "Polaris"},
    "forensics": {"username": "forensics", "password_hash": security.get_password_hash("forensics123"), "role": "Forensics"},
    "judge": {"username": "judge", "password_hash": security.get_password_hash("judge123"), "role": "Judge"},
}

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or not security.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(
        subject=user["username"],
        role=user["role"]
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # In a real app, we would decode and validate more thoroughly
    # For now, we trust the subject we encoded
    try:
        payload = jwt.decode(token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return User(username=username, role=role)
    except Exception as e:
        print(f"DEBUG AUTH ERROR: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate credentials: {str(e)}")

async def get_current_polaris_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "Polaris":
        raise HTTPException(status_code=403, detail="Not authorized (Police role required)")
    return current_user

async def get_current_forensics_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "Forensics":
        raise HTTPException(status_code=403, detail="Not authorized (Forensics role required)")
    return current_user

async def get_current_judge_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "Judge":
        raise HTTPException(status_code=403, detail="Not authorized (Judge role required)")
    return current_user

async def get_mock_polaris_user():
    """Returns a default Polaris user to bypass auth."""
    return User(username="polaris", role="Polaris")
