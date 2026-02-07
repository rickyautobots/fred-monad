"""
FRED on Monad - Autonomous Trading Agent

Optimized for Monad's 10,000 TPS, sub-second finality environment.
Uses LLM-powered analysis for market opportunities.
"""

import os
import json
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FRED")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """FRED configuration."""
    monad_rpc: str = os.getenv("MONAD_RPC", "https://testnet-rpc.monad.xyz")
    private_key: str = os.getenv("FRED_PRIVATE_KEY", "")
    
    # Risk parameters
    max_position_pct: float = 0.1  # Max 10% of portfolio per trade
    max_drawdown_pct: float = 0.15  # Stop if 15% drawdown
    min_edge_pct: float = 0.05  # Minimum 5% expected edge
    
    # Timing
    scan_interval_sec: int = 10  # Monad is fast, scan frequently
    
    # LLM
    use_llm_analysis: bool = True
    

# ============================================================================
# Monad Integration
# ============================================================================

class MonadClient:
    """Client for interacting with Monad chain."""
    
    def __init__(self, config: Config):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.monad_rpc))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if config.private_key:
            self.account = self.w3.eth.account.from_key(config.private_key)
            self.address = self.account.address
        else:
            self.account = None
            self.address = None
            
        logger.info(f"Connected to Monad: {self.w3.is_connected()}")
        if self.address:
            logger.info(f"Agent address: {self.address}")
    
    def get_balance(self) -> Decimal:
        """Get MON balance."""
        if not self.address:
            return Decimal(0)
        balance_wei = self.w3.eth.get_balance(self.address)
        return Decimal(self.w3.from_wei(balance_wei, 'ether'))
    
    def get_gas_price(self) -> int:
        """Get current gas price."""
        return self.w3.eth.gas_price
    
    async def send_transaction(self, to: str, value: int, data: bytes = b'') -> str:
        """Send a transaction on Monad."""
        if not self.account:
            raise ValueError("No private key configured")
        
        nonce = self.w3.eth.get_transaction_count(self.address)
        
        tx = {
            'nonce': nonce,
            'to': to,
            'value': value,
            'gas': 100000,
            'gasPrice': self.get_gas_price(),
            'data': data,
            'chainId': self.w3.eth.chain_id,
        }
        
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        
        # Monad has sub-second finality, wait briefly
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=5)
        
        logger.info(f"Transaction confirmed: {tx_hash.hex()}")
        return tx_hash.hex()


# ============================================================================
# Market Scanner
# ============================================================================

@dataclass
class Opportunity:
    """A trading opportunity."""
    pair: str
    direction: str  # 'long' or 'short'
    entry_price: Decimal
    target_price: Decimal
    edge_pct: float
    confidence: float
    source: str
    timestamp: datetime


class MarketScanner:
    """Scans Monad DEXes for opportunities."""
    
    def __init__(self, client: MonadClient):
        self.client = client
        self.last_scan = None
    
    async def scan(self) -> list[Opportunity]:
        """Scan for trading opportunities."""
        opportunities = []
        
        # TODO: Integrate with Monad DEXes once mainnet launches
        # For now, return simulated opportunities for demo
        
        # This would scan:
        # - LFJ (Liquidity Floor Joe) on Monad
        # - Other Monad-native DEXes
        # - Cross-chain arb opportunities
        
        logger.debug("Scanning Monad markets...")
        
        self.last_scan = datetime.utcnow()
        return opportunities


# ============================================================================
# Strategy Engine
# ============================================================================

class StrategyEngine:
    """LLM-powered strategy analysis."""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def analyze(self, opportunity: Opportunity, portfolio_value: Decimal) -> dict:
        """
        Analyze an opportunity and determine position sizing.
        
        Uses Kelly criterion for optimal position sizing:
        f* = (p*b - q) / b
        where:
        - p = probability of winning
        - q = 1 - p
        - b = win/loss ratio
        """
        
        # Calculate Kelly fraction
        p = opportunity.confidence
        q = 1 - p
        b = opportunity.edge_pct / 0.02  # Assume 2% stop loss
        
        kelly_fraction = (p * b - q) / b if b > 0 else 0
        
        # Apply half-Kelly for safety
        position_fraction = min(kelly_fraction * 0.5, self.config.max_position_pct)
        
        if position_fraction < 0:
            return {"action": "skip", "reason": "negative expected value"}
        
        position_size = float(portfolio_value) * position_fraction
        
        return {
            "action": "execute" if opportunity.edge_pct >= self.config.min_edge_pct else "skip",
            "position_size": position_size,
            "kelly_fraction": kelly_fraction,
            "adjusted_fraction": position_fraction,
            "edge": opportunity.edge_pct,
            "confidence": opportunity.confidence,
        }


# ============================================================================
# FRED Agent
# ============================================================================

class FRED:
    """
    Fully Autonomous Research & Execution Daemon
    
    Main agent loop that:
    1. Scans markets for opportunities
    2. Analyzes with LLM + quantitative models
    3. Executes trades autonomously
    4. Manages positions and risk
    """
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.client = MonadClient(self.config)
        self.scanner = MarketScanner(self.client)
        self.strategy = StrategyEngine(self.config)
        
        self.running = False
        self.positions = []
        self.trade_history = []
    
    async def run(self):
        """Main agent loop."""
        self.running = True
        logger.info("FRED starting on Monad...")
        
        # Log initial state
        balance = self.client.get_balance()
        logger.info(f"Initial balance: {balance} MON")
        
        while self.running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Tick error: {e}")
            
            await asyncio.sleep(self.config.scan_interval_sec)
    
    async def _tick(self):
        """Single iteration of the agent loop."""
        
        # 1. Scan for opportunities
        opportunities = await self.scanner.scan()
        
        if not opportunities:
            logger.debug("No opportunities found")
            return
        
        # 2. Get portfolio value
        portfolio_value = self.client.get_balance()
        
        # 3. Analyze each opportunity
        for opp in opportunities:
            analysis = await self.strategy.analyze(opp, portfolio_value)
            
            if analysis["action"] == "execute":
                logger.info(f"Executing: {opp.pair} {opp.direction}")
                logger.info(f"  Size: {analysis['position_size']:.4f} MON")
                logger.info(f"  Edge: {analysis['edge']*100:.1f}%")
                
                # TODO: Execute trade when DEX integrations ready
                
                self.trade_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "pair": opp.pair,
                    "direction": opp.direction,
                    "size": analysis["position_size"],
                    "edge": analysis["edge"],
                })
    
    def stop(self):
        """Stop the agent."""
        self.running = False
        logger.info("FRED stopping...")
    
    def get_status(self) -> dict:
        """Get current agent status."""
        return {
            "running": self.running,
            "address": self.client.address,
            "balance_mon": float(self.client.get_balance()),
            "positions": len(self.positions),
            "total_trades": len(self.trade_history),
            "last_scan": self.scanner.last_scan.isoformat() if self.scanner.last_scan else None,
        }


# ============================================================================
# CLI
# ============================================================================

async def main():
    """Run FRED agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FRED on Monad")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    args = parser.parse_args()
    
    fred = FRED()
    
    if args.status:
        print(json.dumps(fred.get_status(), indent=2))
        return
    
    try:
        await fred.run()
    except KeyboardInterrupt:
        fred.stop()


if __name__ == "__main__":
    asyncio.run(main())
