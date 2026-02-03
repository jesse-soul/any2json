"""
any2json Backend API
FastAPI server with auth, payments, and convert endpoints
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets
import hashlib
import pyotp
import jwt
import time
from pathlib import Path

app = FastAPI(title="any2json API", version="0.1.0")

# Config
JWT_SECRET = secrets.token_hex(32)  # TODO: load from env
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY = 86400 * 7  # 7 days

# In-memory store (TODO: PostgreSQL)
users_db = {}
addresses_pool = {}  # network -> [addresses]
user_addresses = {}  # user_id -> {network: address}


# --- Models ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class ConvertRequest(BaseModel):
    input: str
    max_tokens: int = 500
    type: str = "auto"
    expand: Optional[list] = None

class PaymentAddressRequest(BaseModel):
    network: str  # trc20, erc20, dai, xdai


# --- Auth helpers ---

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": time.time() + TOKEN_EXPIRY
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload["exp"] < time.time():
            raise HTTPException(401, "Token expired")
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


# --- Routes: Static ---

@app.get("/", response_class=HTMLResponse)
async def landing():
    """Serve landing page."""
    static_path = Path(__file__).parent.parent / "static" / "index.html"
    if static_path.exists():
        return HTMLResponse(static_path.read_text())
    return HTMLResponse("<h1>any2json</h1><p>Landing page not found</p>")

@app.get("/install")
async def install_script():
    """Serve install script."""
    script_path = Path(__file__).parent.parent / "install.sh"
    if script_path.exists():
        return FileResponse(script_path, media_type="text/plain")
    raise HTTPException(404, "Install script not found")

@app.get("/cli/any2json.py")
async def cli_download():
    """Serve CLI script."""
    cli_path = Path(__file__).parent.parent / "cli" / "any2json.py"
    if cli_path.exists():
        return FileResponse(cli_path, media_type="text/plain")
    raise HTTPException(404, "CLI not found")


# --- Routes: Auth ---

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    """Register new user."""
    if req.email in users_db:
        raise HTTPException(400, "Email already registered")
    
    user_id = secrets.token_hex(16)
    api_key = f"a2j_{secrets.token_hex(24)}"
    
    users_db[req.email] = {
        "id": user_id,
        "email": req.email,
        "password_hash": hash_password(req.password),
        "api_key": api_key,
        "balance": 0.0,
        "used": 0.0,
        "tier": "free",
        "totp_secret": None,
        "totp_enabled": False
    }
    
    return {
        "token": create_token(user_id),
        "api_key": api_key,
        "user_id": user_id
    }

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Login user."""
    user = users_db.get(req.email)
    if not user or user["password_hash"] != hash_password(req.password):
        raise HTTPException(401, "Invalid credentials")
    
    # Check 2FA
    if user["totp_enabled"]:
        if not req.totp_code:
            return {"requires_2fa": True}
        
        totp = pyotp.TOTP(user["totp_secret"])
        if not totp.verify(req.totp_code):
            raise HTTPException(401, "Invalid 2FA code")
    
    return {
        "token": create_token(user["id"]),
        "api_key": user["api_key"]
    }


# --- Routes: Account ---

@app.get("/api/account/balance")
async def get_balance(user_id: str = Depends(verify_token)):
    """Get user balance."""
    for user in users_db.values():
        if user["id"] == user_id:
            return {
                "balance": user["balance"],
                "used": user["used"],
                "tier": user["tier"]
            }
    raise HTTPException(404, "User not found")

@app.post("/api/account/regenerate-key")
async def regenerate_key(user_id: str = Depends(verify_token)):
    """Generate new API key."""
    for user in users_db.values():
        if user["id"] == user_id:
            new_key = f"a2j_{secrets.token_hex(24)}"
            user["api_key"] = new_key
            return {"api_key": new_key}
    raise HTTPException(404, "User not found")

@app.post("/api/account/2fa/setup")
async def setup_2fa(user_id: str = Depends(verify_token)):
    """Setup 2FA."""
    for email, user in users_db.items():
        if user["id"] == user_id:
            secret = pyotp.random_base32()
            user["totp_secret"] = secret
            
            totp = pyotp.TOTP(secret)
            otpauth_url = totp.provisioning_uri(email, issuer_name="any2json")
            
            return {
                "secret": secret,
                "otpauth_url": otpauth_url
            }
    raise HTTPException(404, "User not found")

@app.post("/api/account/2fa/verify")
async def verify_2fa(code: str, user_id: str = Depends(verify_token)):
    """Verify and enable 2FA."""
    for user in users_db.values():
        if user["id"] == user_id:
            if not user["totp_secret"]:
                raise HTTPException(400, "2FA not set up")
            
            totp = pyotp.TOTP(user["totp_secret"])
            if totp.verify(code):
                user["totp_enabled"] = True
                return {"success": True}
            else:
                return {"success": False}
    raise HTTPException(404, "User not found")


# --- Routes: Payments ---

@app.post("/api/payments/get-address")
async def get_payment_address(req: PaymentAddressRequest, user_id: str = Depends(verify_token)):
    """Get unique payment address for user."""
    
    network_names = {
        "trc20": "USDT (TRC-20)",
        "erc20": "USDT (ERC-20)",
        "dai": "DAI (Ethereum)",
        "xdai": "xDAI (Gnosis)"
    }
    
    if req.network not in network_names:
        raise HTTPException(400, f"Invalid network. Supported: {list(network_names.keys())}")
    
    # Check if user already has address for this network
    if user_id in user_addresses and req.network in user_addresses[user_id]:
        return {
            "address": user_addresses[user_id][req.network],
            "network": req.network,
            "network_name": network_names[req.network]
        }
    
    # Assign new address from pool
    if req.network not in addresses_pool or not addresses_pool[req.network]:
        raise HTTPException(503, "No addresses available. Please try again later.")
    
    address = addresses_pool[req.network].pop(0)
    
    if user_id not in user_addresses:
        user_addresses[user_id] = {}
    user_addresses[user_id][req.network] = address
    
    return {
        "address": address,
        "network": req.network,
        "network_name": network_names[req.network]
    }


# --- Routes: Convert ---

@app.post("/api/convert")
async def convert(req: ConvertRequest, user_id: str = Depends(verify_token)):
    """Convert media to JSON."""
    
    # Check balance
    for user in users_db.values():
        if user["id"] == user_id:
            # TODO: Calculate cost based on input type and max_tokens
            estimated_cost = 0.01  # $0.01 per request for now
            
            if user["balance"] < estimated_cost and user["tier"] == "free":
                # Allow some free requests
                pass
            
            # TODO: Actual conversion logic
            # For now, return mock response
            result = {
                "type": "image",
                "summary": f"Mock response for {req.input}",
                "elements": [
                    {"id": "e1", "type": "mock", "content": "Integration pending"}
                ],
                "metadata": {
                    "max_tokens": req.max_tokens,
                    "input": req.input[:100]
                },
                "_expandable": ["e1"],
                "_tokens_used": 85
            }
            
            # Deduct balance
            user["used"] += estimated_cost
            
            return result
    
    raise HTTPException(404, "User not found")


# --- Health ---

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# --- Admin: Load addresses ---

def load_addresses(network: str, addresses: list):
    """Load addresses into pool (called on startup or via admin endpoint)."""
    if network not in addresses_pool:
        addresses_pool[network] = []
    addresses_pool[network].extend(addresses)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
