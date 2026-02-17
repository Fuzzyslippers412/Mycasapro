"""
Edge Lab Configuration

Central configuration for the Edge Lab system.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class UniversePolicyConfig:
    """Default universe policy configuration"""
    name: str = "US_LIQUID_V1"
    version: int = 1
    rules: Dict[str, Any] = field(default_factory=lambda: {
        "min_price": 5.0,
        "min_avg_dollar_vol_20d": 25_000_000,
        "exclude_etfs": True,
        "exchanges": ["NYSE", "NASDAQ"],
        "exclude_adr": False,
        "max_spread_proxy": None,  # Optional
    })


@dataclass 
class FeatureSetConfig:
    """Default feature set configuration"""
    name: str = "CORE_V1"
    version: int = 1
    features: List[str] = field(default_factory=lambda: [
        "ret_1d",
        "ret_5d",
        "ret_20d",
        "ret_60d",
        "vol_20d",
        "atr_14_pct",
        "gap_pct",
        "rel_vol_20d",
        "dollar_vol_20d",
        "dist_sma_20",
        "dist_sma_50",
        "trend_slope_20",
    ])
    windows: Dict[str, int] = field(default_factory=lambda: {
        "ret_1d": 1,
        "ret_5d": 5,
        "ret_20d": 20,
        "ret_60d": 60,
        "vol_20d": 20,
        "atr_14_pct": 14,
        "gap_pct": 1,
        "rel_vol_20d": 20,
        "dollar_vol_20d": 20,
        "dist_sma_20": 20,
        "dist_sma_50": 50,
        "trend_slope_20": 20,
    })


@dataclass
class ModelConfig:
    """Default model configuration"""
    name: str = "BASELINE_V1"
    version: int = 1
    model_type: str = "rule_score"
    train_window: Dict[str, Any] = field(default_factory=lambda: {
        "years": 3,
        "min_samples": 5000,
    })
    config: Dict[str, Any] = field(default_factory=lambda: {
        "momentum_weight": 0.3,
        "mean_reversion_weight": 0.2,
        "volatility_penalty": 0.2,
        "liquidity_weight": 0.3,
    })


@dataclass
class RiskFlagConfig:
    """Risk flag thresholds"""
    low_liquidity_threshold: float = 10_000_000  # $10M
    huge_gap_threshold: float = 0.08  # 8%
    extreme_1d_move_threshold: float = 0.15  # 15%
    microcap_threshold: float = 500_000_000  # $500M


@dataclass
class EdgeLabConfig:
    """Main Edge Lab configuration"""
    
    # Database - default to SQLite in data folder
    database_url: str = field(default_factory=lambda: os.environ.get(
        "EDGELAB_DATABASE_URL",
        os.environ.get("DATABASE_URL", "sqlite:///data/edgelab.db")
    ))
    
    # Default configurations
    universe_policy: UniversePolicyConfig = field(default_factory=UniversePolicyConfig)
    feature_set: FeatureSetConfig = field(default_factory=FeatureSetConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    risk_flags: RiskFlagConfig = field(default_factory=RiskFlagConfig)
    
    # Data settings
    min_history_days: int = 90  # Minimum days of history required
    preferred_history_days: int = 252  # Full year of history
    
    # Prediction settings
    default_horizon_days: int = 5  # Weekly prediction horizon
    top_candidates_count: int = 20  # Number of top candidates to output
    
    # Adapter settings
    default_adapter: str = "yfinance"  # Default data adapter
    
    @classmethod
    def from_env(cls) -> "EdgeLabConfig":
        """Create configuration from environment variables"""
        return cls()


# Global configuration instance
_config: Optional[EdgeLabConfig] = None


def get_config() -> EdgeLabConfig:
    """Get or create global configuration"""
    global _config
    if _config is None:
        _config = EdgeLabConfig.from_env()
    return _config


def set_config(config: EdgeLabConfig):
    """Set global configuration"""
    global _config
    _config = config
