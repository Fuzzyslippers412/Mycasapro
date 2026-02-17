"""
Polymarket Trade Tracker
Parses CSV exports and tracks win/loss statistics
"""
from typing import Dict, Any, List
from datetime import datetime
import csv
import io
from pydantic import BaseModel


class Trade(BaseModel):
    """Individual trade record"""
    market_name: str
    action: str  # Buy, Sell, Redeem
    usdc_amount: float
    token_amount: float
    token_name: str  # Up, Down, or empty for redeems
    timestamp: int
    hash: str


class TradeStats(BaseModel):
    """Aggregated trade statistics"""
    total_trades: int
    total_invested_usdc: float
    total_redeemed_usdc: float
    net_profit_loss: float
    win_count: int
    loss_count: int
    win_rate: float
    avg_profit_per_win: float
    avg_loss_per_loss: float
    biggest_win: float
    biggest_loss: float
    total_up_bets: int
    total_down_bets: int
    up_win_rate: float
    down_win_rate: float


class TradeTracker:
    """
    Parses Polymarket CSV exports and calculates performance metrics
    """

    def parse_csv(self, csv_content: str) -> List[Trade]:
        """
        Parse Polymarket CSV export

        Expected format:
        "marketName","action","usdcAmount","tokenAmount","tokenName","timestamp","hash"
        """
        trades = []
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            try:
                trade = Trade(
                    market_name=row["marketName"],
                    action=row["action"],
                    usdc_amount=float(row["usdcAmount"]),
                    token_amount=float(row["tokenAmount"]),
                    token_name=row["tokenName"],
                    timestamp=int(row["timestamp"]),
                    hash=row["hash"]
                )
                trades.append(trade)
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue

        return trades

    def calculate_stats(self, trades: List[Trade]) -> TradeStats:
        """
        Calculate win/loss statistics from trades

        Logic:
        - Buy = Investment
        - Sell = Early exit (realized P&L)
        - Redeem = Market settlement (winning position)
        """
        total_invested = 0.0
        total_redeemed = 0.0
        wins = []
        losses = []
        up_bets = []
        down_bets = []

        # Group trades by market
        markets: Dict[str, List[Trade]] = {}
        for trade in trades:
            if trade.market_name not in markets:
                markets[trade.market_name] = []
            markets[trade.market_name].append(trade)

        # Calculate P&L per market
        for market_name, market_trades in markets.items():
            invested = 0.0
            redeemed = 0.0
            direction = None

            for trade in sorted(market_trades, key=lambda t: t.timestamp):
                if trade.action == "Buy":
                    invested += trade.usdc_amount
                    direction = trade.token_name  # Up or Down

                    # Track direction
                    if direction == "Up":
                        up_bets.append(trade)
                    elif direction == "Down":
                        down_bets.append(trade)

                elif trade.action == "Sell":
                    # Early exit - calculate realized P&L
                    redeemed += trade.usdc_amount

                elif trade.action == "Redeem":
                    # Market settled - full payout
                    redeemed += trade.usdc_amount

            # Calculate net P&L for this market
            net_pl = redeemed - invested

            if net_pl > 0:
                wins.append((net_pl, direction))
            elif net_pl < 0:
                losses.append((net_pl, direction))

            total_invested += invested
            total_redeemed += redeemed

        # Calculate stats
        net_profit_loss = total_redeemed - total_invested
        win_count = len(wins)
        loss_count = len(losses)
        total_trades = win_count + loss_count

        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

        avg_profit_per_win = sum(w[0] for w in wins) / win_count if win_count > 0 else 0.0
        avg_loss_per_loss = sum(l[0] for l in losses) / loss_count if loss_count > 0 else 0.0

        biggest_win = max([w[0] for w in wins], default=0.0)
        biggest_loss = min([l[0] for l in losses], default=0.0)

        # Direction-specific win rates
        up_wins = sum(1 for w in wins if w[1] == "Up")
        up_total = len([b for b in up_bets])
        up_win_rate = (up_wins / up_total * 100) if up_total > 0 else 0.0

        down_wins = sum(1 for w in wins if w[1] == "Down")
        down_total = len([b for b in down_bets])
        down_win_rate = (down_wins / down_total * 100) if down_total > 0 else 0.0

        return TradeStats(
            total_trades=total_trades,
            total_invested_usdc=total_invested,
            total_redeemed_usdc=total_redeemed,
            net_profit_loss=net_profit_loss,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            avg_profit_per_win=avg_profit_per_win,
            avg_loss_per_loss=avg_loss_per_loss,
            biggest_win=biggest_win,
            biggest_loss=biggest_loss,
            total_up_bets=up_total,
            total_down_bets=down_total,
            up_win_rate=up_win_rate,
            down_win_rate=down_win_rate
        )

    def generate_recommendations(self, stats: TradeStats) -> Dict[str, Any]:
        """
        Generate betting recommendations based on historical performance
        """
        recommendations = {
            "preferred_direction": "UP" if stats.up_win_rate > stats.down_win_rate else "DOWN",
            "avoid_direction": "DOWN" if stats.up_win_rate > stats.down_win_rate else "UP",
            "recommended_bet_size_pct": 2.0,  # % of bankroll
            "risk_assessment": "MODERATE",
            "insights": []
        }

        # Adjust bet size based on win rate
        if stats.win_rate >= 60:
            recommendations["recommended_bet_size_pct"] = 5.0
            recommendations["risk_assessment"] = "AGGRESSIVE"
            recommendations["insights"].append(f"Strong win rate ({stats.win_rate:.1f}%) - increase position size")
        elif stats.win_rate >= 50:
            recommendations["recommended_bet_size_pct"] = 3.0
            recommendations["risk_assessment"] = "MODERATE"
            recommendations["insights"].append(f"Solid win rate ({stats.win_rate:.1f}%) - maintain position size")
        else:
            recommendations["recommended_bet_size_pct"] = 1.0
            recommendations["risk_assessment"] = "CONSERVATIVE"
            recommendations["insights"].append(f"Win rate needs improvement ({stats.win_rate:.1f}%) - reduce position size")

        # Direction insights
        if abs(stats.up_win_rate - stats.down_win_rate) > 15:
            diff = abs(stats.up_win_rate - stats.down_win_rate)
            recommendations["insights"].append(
                f"Strong directional edge: {recommendations['preferred_direction']} wins {diff:.1f}% more often"
            )

        # Risk/reward insights
        if stats.win_count > 0 and stats.loss_count > 0:
            rr_ratio = abs(stats.avg_profit_per_win / stats.avg_loss_per_loss)
            if rr_ratio > 1.5:
                recommendations["insights"].append(
                    f"Excellent risk/reward ratio ({rr_ratio:.2f}:1)"
                )
            elif rr_ratio < 0.8:
                recommendations["insights"].append(
                    f"Poor risk/reward ratio ({rr_ratio:.2f}:1) - wins are smaller than losses"
                )

        return recommendations
