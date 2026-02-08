"""
Unit tests for FRED on Monad trading agent.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime
import asyncio

# Mock web3 before importing fred_monad
import sys
sys.modules['web3'] = MagicMock()
sys.modules['web3.middleware'] = MagicMock()

from fred_monad import (
    Config,
    MonadClient,
    Opportunity,
    MarketScanner,
    StrategyEngine,
    FRED,
)


# ============================================================================
# Config Tests
# ============================================================================

class TestConfig:
    """Tests for Config dataclass."""
    
    def test_default_values(self):
        """Config should have sensible defaults."""
        config = Config()
        assert config.max_position_pct == 0.1
        assert config.max_drawdown_pct == 0.15
        assert config.min_edge_pct == 0.05
        assert config.scan_interval_sec == 10
        assert config.use_llm_analysis is True
    
    def test_custom_values(self):
        """Config should accept custom values."""
        config = Config(
            max_position_pct=0.2,
            max_drawdown_pct=0.1,
            min_edge_pct=0.03,
        )
        assert config.max_position_pct == 0.2
        assert config.max_drawdown_pct == 0.1
        assert config.min_edge_pct == 0.03
    
    def test_risk_params_reasonable(self):
        """Risk parameters should be reasonable values."""
        config = Config()
        # Max position should be <= 25% (quarter-Kelly max)
        assert config.max_position_pct <= 0.25
        # Max drawdown should be meaningful but not catastrophic
        assert 0.05 <= config.max_drawdown_pct <= 0.5
        # Min edge should require positive expectancy
        assert config.min_edge_pct > 0


# ============================================================================
# Opportunity Tests
# ============================================================================

class TestOpportunity:
    """Tests for Opportunity dataclass."""
    
    def test_opportunity_creation(self):
        """Opportunity should store all fields correctly."""
        opp = Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.50"),
            target_price=Decimal("1.65"),
            edge_pct=0.10,
            confidence=0.65,
            source="dex_scan",
            timestamp=datetime(2026, 2, 8, 6, 0, 0),
        )
        
        assert opp.pair == "MON/USDC"
        assert opp.direction == "long"
        assert opp.entry_price == Decimal("1.50")
        assert opp.target_price == Decimal("1.65")
        assert opp.edge_pct == 0.10
        assert opp.confidence == 0.65
        assert opp.source == "dex_scan"
    
    def test_edge_calculation(self):
        """Edge should be target - entry / entry."""
        opp = Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.00"),
            target_price=Decimal("1.10"),
            edge_pct=0.10,  # 10% edge
            confidence=0.6,
            source="test",
            timestamp=datetime.utcnow(),
        )
        
        calculated_edge = float((opp.target_price - opp.entry_price) / opp.entry_price)
        assert abs(calculated_edge - opp.edge_pct) < 0.01


# ============================================================================
# Strategy Engine Tests
# ============================================================================

class TestStrategyEngine:
    """Tests for StrategyEngine class."""
    
    @pytest.fixture
    def strategy(self):
        return StrategyEngine(Config())
    
    @pytest.fixture
    def sample_opportunity(self):
        return Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.00"),
            target_price=Decimal("1.10"),
            edge_pct=0.10,
            confidence=0.65,
            source="test",
            timestamp=datetime.utcnow(),
        )
    
    @pytest.mark.asyncio
    async def test_analyze_returns_dict(self, strategy, sample_opportunity):
        """Analyze should return a dict with required keys."""
        result = await strategy.analyze(sample_opportunity, Decimal("100"))
        
        assert "action" in result
        assert "position_size" in result or result["action"] == "skip"
    
    @pytest.mark.asyncio
    async def test_analyze_respects_min_edge(self, strategy):
        """Should skip opportunities below min_edge_pct."""
        low_edge_opp = Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.00"),
            target_price=Decimal("1.02"),
            edge_pct=0.02,  # Below 5% threshold
            confidence=0.65,
            source="test",
            timestamp=datetime.utcnow(),
        )
        
        result = await strategy.analyze(low_edge_opp, Decimal("100"))
        assert result["action"] == "skip"
    
    @pytest.mark.asyncio
    async def test_analyze_executes_good_opportunity(self, strategy, sample_opportunity):
        """Should execute opportunities above min_edge_pct."""
        result = await strategy.analyze(sample_opportunity, Decimal("100"))
        assert result["action"] == "execute"
    
    @pytest.mark.asyncio
    async def test_kelly_fraction_capped(self, strategy):
        """Position size should be capped at max_position_pct."""
        high_edge_opp = Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.00"),
            target_price=Decimal("2.00"),
            edge_pct=1.0,  # 100% edge (unrealistic but tests cap)
            confidence=0.95,
            source="test",
            timestamp=datetime.utcnow(),
        )
        
        portfolio = Decimal("1000")
        result = await strategy.analyze(high_edge_opp, portfolio)
        
        # Position should be capped at max_position_pct (10%)
        max_allowed = float(portfolio) * strategy.config.max_position_pct
        assert result["position_size"] <= max_allowed
    
    @pytest.mark.asyncio
    async def test_negative_ev_skipped(self, strategy):
        """Should skip negative expected value opportunities."""
        bad_opp = Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.00"),
            target_price=Decimal("1.05"),
            edge_pct=0.05,
            confidence=0.30,  # Low confidence = negative EV
            source="test",
            timestamp=datetime.utcnow(),
        )
        
        result = await strategy.analyze(bad_opp, Decimal("100"))
        assert result["action"] == "skip"


# ============================================================================
# MarketScanner Tests
# ============================================================================

class TestMarketScanner:
    """Tests for MarketScanner class."""
    
    @pytest.fixture
    def mock_client(self):
        client = Mock(spec=MonadClient)
        client.address = "0x1234567890abcdef"
        return client
    
    @pytest.fixture
    def scanner(self, mock_client):
        return MarketScanner(mock_client)
    
    @pytest.mark.asyncio
    async def test_scan_returns_list(self, scanner):
        """Scan should return a list."""
        result = await scanner.scan()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_scan_updates_last_scan(self, scanner):
        """Scan should update last_scan timestamp."""
        assert scanner.last_scan is None
        await scanner.scan()
        assert scanner.last_scan is not None
        assert isinstance(scanner.last_scan, datetime)


# ============================================================================
# FRED Agent Tests
# ============================================================================

class TestFRED:
    """Tests for FRED agent class."""
    
    @pytest.fixture
    def mock_fred(self):
        """Create FRED with mocked dependencies."""
        with patch.object(MonadClient, '__init__', return_value=None):
            with patch.object(MonadClient, 'get_balance', return_value=Decimal("100")):
                fred = FRED(Config())
                fred.client = Mock()
                fred.client.address = "0xtest"
                fred.client.get_balance = Mock(return_value=Decimal("100"))
                return fred
    
    def test_initialization(self, mock_fred):
        """FRED should initialize correctly."""
        assert mock_fred.running is False
        assert mock_fred.positions == []
        assert mock_fred.trade_history == []
    
    def test_get_status(self, mock_fred):
        """get_status should return required fields."""
        status = mock_fred.get_status()
        
        assert "running" in status
        assert "address" in status
        assert "balance_mon" in status
        assert "positions" in status
        assert "total_trades" in status
    
    def test_stop(self, mock_fred):
        """stop should set running to False."""
        mock_fred.running = True
        mock_fred.stop()
        assert mock_fred.running is False
    
    @pytest.mark.asyncio
    async def test_tick_handles_no_opportunities(self, mock_fred):
        """_tick should handle empty opportunity list gracefully."""
        mock_fred.scanner = Mock()
        mock_fred.scanner.scan = AsyncMock(return_value=[])
        
        # Should not raise
        await mock_fred._tick()
    
    @pytest.mark.asyncio
    async def test_tick_processes_opportunities(self, mock_fred):
        """_tick should analyze opportunities when found."""
        opp = Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.00"),
            target_price=Decimal("1.10"),
            edge_pct=0.10,
            confidence=0.65,
            source="test",
            timestamp=datetime.utcnow(),
        )
        
        mock_fred.scanner = Mock()
        mock_fred.scanner.scan = AsyncMock(return_value=[opp])
        mock_fred.strategy = Mock()
        mock_fred.strategy.analyze = AsyncMock(return_value={
            "action": "execute",
            "position_size": 10.0,
            "edge": 0.10,
        })
        
        await mock_fred._tick()
        
        # Should have recorded a trade
        assert len(mock_fred.trade_history) == 1
        assert mock_fred.trade_history[0]["pair"] == "MON/USDC"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for FRED components."""
    
    @pytest.mark.asyncio
    async def test_full_analysis_flow(self):
        """Test complete opportunity → analysis flow."""
        config = Config()
        strategy = StrategyEngine(config)
        
        opp = Opportunity(
            pair="MON/USDC",
            direction="long",
            entry_price=Decimal("1.50"),
            target_price=Decimal("1.65"),
            edge_pct=0.10,
            confidence=0.65,
            source="integration_test",
            timestamp=datetime.utcnow(),
        )
        
        portfolio = Decimal("1000")
        result = await strategy.analyze(opp, portfolio)
        
        # Should execute with proper sizing
        assert result["action"] == "execute"
        assert 0 < result["position_size"] <= float(portfolio) * config.max_position_pct
        assert result["kelly_fraction"] > 0
        assert result["adjusted_fraction"] <= config.max_position_pct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
