import asyncio
import json
import logging
import os
import requests
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from token_monitor import SolanaTokenMonitor, TokenData
from typing import List, Optional
from pydantic import BaseModel
import base58

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models for request validation
class WalletRequest(BaseModel):
    action: str
    public_key: str
    private_key: Optional[str] = None
    api_key: Optional[str] = None
    pool: Optional[str] = "pump"

class TradingSettings(BaseModel):
    slippage: Optional[float] = None
    priority_fee: Optional[float] = None

class TradeRequest(BaseModel):
    mint: str
    action: str
    wallet_public_key: str
    amount: float
    denominated_in_sol: bool = True

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for active connections and global settings
active_connections = []
monitor = SolanaTokenMonitor()
WALLETS_FILE = "secure/wallets.json"
SETTINGS_FILE = "secure/settings.json"
RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"

# Ensure secure directory exists
os.makedirs("secure", exist_ok=True)

# Initialize or load wallets
def load_wallets():
    try:
        with open(WALLETS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # If file is empty or invalid, return default structure
                return {"wallets": []}
    except FileNotFoundError:
        # Create directory if it doesn't exist
        os.makedirs("secure", exist_ok=True)
        # Create file with default structure
        default_data = {"wallets": []}
        with open(WALLETS_FILE, 'w') as f:
            json.dump(default_data, f, indent=2)
        return default_data

def save_wallets(wallets_data):
    with open(WALLETS_FILE, 'w') as f:
        json.dump(wallets_data, f, indent=2)

# Initialize or load settings
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # If file is empty or invalid, return default settings
                return {"slippage": 5, "priority_fee": 0.005}
    except FileNotFoundError:
        # Create directory if it doesn't exist
        os.makedirs("secure", exist_ok=True)
        # Create file with default settings
        default_settings = {"slippage": 5, "priority_fee": 0.005}
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f, indent=2)
        return default_settings

def save_settings(settings_data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings_data, f, indent=2)

# Load initial data
wallets_data = load_wallets()
settings_data = load_settings()

async def get_wallet_balance(public_key: str) -> float:
    """Get wallet balance in SOL"""
    try:
        response = requests.post(RPC_ENDPOINT, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [public_key]
        })
        
        if response.ok:
            result = response.json()
            if 'result' in result:
                return result['result']['value'] / 1_000_000_000  # Convert lamports to SOL
    except Exception as e:
        logger.error(f"Error fetching balance for {public_key}: {str(e)}")
    
    return 0

async def get_wallet_balances():
    """Get balances for all wallets"""
    total_sol = 0
    for wallet in wallets_data["wallets"]:
        balance = await get_wallet_balance(wallet["public_key"])
        wallet["balance"] = balance
        total_sol += balance
    return total_sol

async def token_update_callback(token_mint: str, token_data: TokenData):
    """Callback for token updates from the monitor"""
    # Get the most recent trade type if available, otherwise use "create" for new tokens
    tx_type = "create"
    if token_data.trades:
        tx_type = token_data.trades[-1]['type']
    
    message = {
        "type": "token_update",
        "data": {
            "mint": token_data.mint,
            "name": token_data.name,
            "symbol": token_data.symbol,
            "marketCapSol": token_data.marketCapSol,
            "solAmount": token_data.solAmount,
            "timestamp": token_data.timestamp,
            "txType": tx_type,
            "trades": token_data.trades
        }
    }
    
    # Broadcast to all connected clients
    for client in active_connections:
        try:
            await client.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error broadcasting to client: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"New client connected. Total clients: {len(active_connections)}")
    
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except Exception as e:
        logger.error(f"Client websocket error: {str(e)}")
    finally:
        active_connections.remove(websocket)
        logger.info(f"Client disconnected. Remaining clients: {len(active_connections)}")

@app.post("/wallet")
async def manage_wallet(request: WalletRequest):
    global wallets_data
    
    if request.action == "add":
        if not all([request.public_key, request.private_key]):
            raise HTTPException(status_code=400, detail="Missing required wallet information")
        
        # Check if wallet already exists
        if any(w["public_key"] == request.public_key for w in wallets_data["wallets"]):
            raise HTTPException(status_code=400, detail="Wallet already exists")
        
        # Add new wallet
        new_wallet = {
            "public_key": request.public_key,
            "private_key": request.private_key,
            "api_key": request.api_key,
            "pool": request.pool,
            "last_used": None
        }
        wallets_data["wallets"].append(new_wallet)
        save_wallets(wallets_data)
        return {"status": "success", "message": "Wallet added successfully"}
    
    elif request.action == "remove":
        # Remove wallet
        wallets_data["wallets"] = [w for w in wallets_data["wallets"] if w["public_key"] != request.public_key]
        save_wallets(wallets_data)
        return {"status": "success", "message": "Wallet removed successfully"}
    
    raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/wallet-status")
async def get_wallet_status():
    total_sol = await get_wallet_balances()
    return {
        "active_wallets": len(wallets_data["wallets"]),
        "total_wallets": len(wallets_data["wallets"]),
        "total_sol": total_sol,
        "wallets": [{
            "public_key": w["public_key"],
            "last_used": w["last_used"],
            "pool": w["pool"],
            "balance": w.get("balance", 0)
        } for w in wallets_data["wallets"]]
    }

@app.post("/trading-settings")
async def update_trading_settings(settings: TradingSettings):
    global settings_data
    
    if settings.slippage is not None:
        settings_data["slippage"] = settings.slippage
    if settings.priority_fee is not None:
        settings_data["priority_fee"] = settings.priority_fee
    
    save_settings(settings_data)
    return {"status": "success", "settings": settings_data}

@app.post("/execute-trade")
async def execute_trade(trade: TradeRequest):
    # Find wallet
    wallet = next((w for w in wallets_data["wallets"] if w["public_key"] == trade.wallet_public_key), None)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    try:
        # Prepare trade request
        trade_data = {
            "action": trade.action,
            "mint": trade.mint,
            "amount": trade.amount,
            "denominatedInSol": str(trade.denominated_in_sol).lower(),
            "slippage": settings_data["slippage"],
            "priorityFee": settings_data["priority_fee"],
            "pool": wallet.get("pool", "pump")
        }
        
        # Execute trade using PumpPortal API
        response = requests.post(
            f"https://pumpportal.fun/api/trade?api-key={wallet['api_key']}",
            data=trade_data
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        # Update last used timestamp
        wallet["last_used"] = datetime.now().isoformat()
        save_wallets(wallets_data)
        
        return response.json()
        
    except Exception as e:
        logger.error(f"Trade execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("Starting services...")
    
    # Add callback for token updates
    monitor.add_callback(token_update_callback)
    
    # Start the token monitor
    asyncio.create_task(monitor.monitor_tokens())
    
    logger.info("Startup complete - services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down services...")
    await monitor.stop()
    logger.info("Shutdown complete")