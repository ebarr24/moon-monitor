import asyncio
import json
import websockets
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TokenData:
    mint: str
    name: str
    symbol: str
    marketCapSol: float
    solAmount: float
    initialMarketCap: float
    timestamp: int
    trades: List[dict]
    supply: int = 1_000_000_000  # Default supply of 1 billion tokens

class SolanaTokenMonitor:
    def __init__(self, websocket_url: str = "wss://pumpportal.fun/api/data"):
        self.websocket_url = websocket_url
        self.websocket = None
        self.token_data: Dict[str, TokenData] = {}
        self.running = False
        self.retry_delay = 1
        self.max_retry_delay = 30
        self.callbacks: List[Callable] = []
        self.subscribed_tokens: set = set()

    def add_callback(self, callback):
        """Add a callback function to be called when token data updates"""
        self.callbacks.append(callback)

    async def connect(self):
        if self.websocket:
            await self.websocket.close()
        
        self.websocket = await websockets.connect(
            self.websocket_url,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=20
        )
        logger.info("Connected to PumpPortal WebSocket")
        
        # Subscribe to new token events
        await self.websocket.send(json.dumps({
            "method": "subscribeNewToken"
        }))
        logger.info("Subscribed to new token events")
        
        # Resubscribe to all tracked tokens
        if self.subscribed_tokens:
            await self.websocket.send(json.dumps({
                "method": "subscribeTokenTrade",
                "keys": list(self.subscribed_tokens)
            }))
            logger.info(f"Resubscribed to {len(self.subscribed_tokens)} token trades")
        
        self.retry_delay = 1

    async def subscribe_to_token(self, token_mint: str, initial_data: dict = None):
        """Subscribe to a token's trades"""
        if not self.websocket:
            await self.connect()

        # Store initial token data if provided
        if initial_data and token_mint not in self.token_data:
            self.token_data[token_mint] = TokenData(
                mint=token_mint,
                name=initial_data.get('name', ''),
                symbol=initial_data.get('symbol', ''),
                marketCapSol=initial_data.get('marketCapSol', 0),
                solAmount=initial_data.get('solAmount', 0),
                initialMarketCap=initial_data.get('marketCapSol', 0),
                timestamp=int(datetime.now().timestamp() * 1000),
                trades=[],
                supply=initial_data.get('supply', 1_000_000_000)  # Use provided supply or default to 1B
            )

        # Subscribe to token trades if not already subscribed
        if token_mint not in self.subscribed_tokens:
            await self.websocket.send(json.dumps({
                "method": "subscribeTokenTrade",
                "keys": [token_mint]
            }))
            self.subscribed_tokens.add(token_mint)
            logger.info(f"Subscribed to trades for token {token_mint}")
            return True
        return False

    async def process_message(self, message: str):
        """Process incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get('txType', 'unknown')
            
            if msg_type == 'create':
                # Handle new token creation
                token_mint = data.get('mint')
                if token_mint and token_mint not in self.token_data:
                    await self.subscribe_to_token(token_mint, initial_data=data)
                    
                    # Notify callbacks
                    for callback in self.callbacks:
                        await callback(token_mint, self.token_data[token_mint])
                    
                    logger.info(f"New token created: {data.get('name')} ({token_mint})")
                    
            elif msg_type in ['buy', 'sell']:
                # Handle token trades
                token_mint = data.get('mint')
                if token_mint in self.token_data:
                    token = self.token_data[token_mint]
                    
                    # Update token data
                    new_market_cap = data.get('marketCapSol', token.marketCapSol)
                    new_sol_amount = data.get('solAmount', token.solAmount)
                    
                    token.marketCapSol = new_market_cap
                    token.solAmount = new_sol_amount
                    
                    # Calculate if this trade is within first 3 seconds
                    current_time = int(datetime.now().timestamp() * 1000)
                    is_early_trade = (current_time - token.timestamp) <= 3000  # 3 seconds in milliseconds
                    
                    # Add trade to history with market cap and early trade flag
                    token.trades.append({
                        'type': msg_type,
                        'amount': new_sol_amount,
                        'marketCap': new_market_cap,
                        'timestamp': current_time,
                        'isEarlyTrade': is_early_trade
                    })
                    
                    # Notify callbacks
                    for callback in self.callbacks:
                        await callback(token_mint, token)
                    
                    logger.info(f"Trade for {token.name}: {msg_type} {new_sol_amount} SOL, Market Cap: {new_market_cap}, Early Trade: {is_early_trade}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    async def monitor_tokens(self):
        """Main monitoring loop"""
        self.running = True
        
        while self.running:
            try:
                if not self.websocket:
                    await self.connect()

                async for message in self.websocket:
                    if not self.running:
                        break
                    await self.process_message(message)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed, attempting to reconnect...")
                await asyncio.sleep(self.retry_delay)
                self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
                continue
            
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.retry_delay)
                continue

    async def stop(self):
        """Stop the monitor"""
        self.running = False
        if self.websocket:
            # Unsubscribe from everything
            await self.websocket.send(json.dumps({"method": "unsubscribeNewToken"}))
            if self.subscribed_tokens:
                await self.websocket.send(json.dumps({
                    "method": "unsubscribeTokenTrade",
                    "keys": list(self.subscribed_tokens)
                }))
            await self.websocket.close()

    def get_token_data(self, token_mint: str) -> Optional[TokenData]:
        """Get current data for a token"""
        return self.token_data.get(token_mint) 