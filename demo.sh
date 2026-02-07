#!/bin/bash
# Demo script for Moltiverse hackathon submission
# Run this to demonstrate FRED on Monad

echo "═══════════════════════════════════════════════════"
echo "  FRED - Autonomous Trading Agent on Monad"
echo "  Moltiverse Hackathon Entry"
echo "═══════════════════════════════════════════════════"
echo ""

# Show project structure
echo "📁 Project Structure:"
echo "────────────────────"
ls -la *.py *.md requirements.txt 2>/dev/null
echo ""

# Show key code
echo "🔧 Core Agent Architecture:"
echo "────────────────────────────"
head -50 fred_monad.py | tail -30
echo ""

# Check Monad connection
echo "🌐 Monad Network Status:"
echo "────────────────────────"
python3 -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://testnet-rpc.monad.xyz'))
print(f'Connected: {w3.is_connected()}')
print(f'Chain ID: {w3.eth.chain_id}')
print(f'Block: {w3.eth.block_number}')
"

echo ""
echo "🚀 Starting FRED (status mode)..."
echo "────────────────────────────────"
python3 fred_monad.py --status

echo ""
echo "═══════════════════════════════════════════════════"
echo "  FRED ready for autonomous trading on Monad!"
echo "═══════════════════════════════════════════════════"
