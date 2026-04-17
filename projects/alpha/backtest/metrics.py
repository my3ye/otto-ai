"""
Performance metrics for backtesting.
Calculates P&L, win rate, max drawdown, Sharpe ratio.
"""

import math
from typing import Optional


def calculate_returns(entry_price: float, exit_price: float) -> float:
    """Calculate percentage return."""
    if entry_price <= 0:
        return 0.0
    return (exit_price - entry_price) / entry_price * 100


def calculate_win_rate(trades: list[dict], exit_key: str = "return_pct_1h") -> dict:
    """Calculate win rate at different time horizons."""
    results = {}
    for horizon in ["return_pct_1h", "return_pct_4h", "return_pct_24h"]:
        valid = [t for t in trades if t.get(horizon) is not None]
        if not valid:
            results[horizon] = {"win_rate": None, "count": 0}
            continue
        wins = [t for t in valid if t[horizon] > 0]
        results[horizon] = {
            "win_rate": len(wins) / len(valid),
            "avg_return_pct": sum(t[horizon] for t in valid) / len(valid),
            "count": len(valid),
            "wins": len(wins),
            "losses": len(valid) - len(wins),
        }
    return results


def calculate_max_drawdown(equity_curve: list[float]) -> float:
    """
    Max drawdown from peak. Returns as a negative percentage.
    equity_curve: list of portfolio values over time.
    """
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return max_dd


def calculate_sharpe(returns: list[float], risk_free_rate: float = 0.0) -> Optional[float]:
    """
    Annualized Sharpe ratio from a list of per-trade returns (%).
    Assumes returns are independent trade outcomes.
    """
    if len(returns) < 2:
        return None
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    if variance <= 0:
        return None
    std = math.sqrt(variance)
    # Annualize: assume ~365 trades/year as approximation
    sharpe = (mean - risk_free_rate) / std
    return sharpe


def summarize_trades(trades: list[dict]) -> dict:
    """Full performance summary from backtest trade list."""
    if not trades:
        return {"error": "no trades"}

    summary = {
        "total_signals": len(trades),
        "signals_with_price_data": len([t for t in trades if t.get("entry_price")]),
    }

    for horizon_key, label in [
        ("return_pct_1h", "1h"),
        ("return_pct_4h", "4h"),
        ("return_pct_24h", "24h"),
    ]:
        valid = [t for t in trades if t.get(horizon_key) is not None]
        if not valid:
            summary[f"horizon_{label}"] = {"count": 0, "data": "insufficient"}
            continue

        returns = [t[horizon_key] for t in valid]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]

        # Build equity curve (100 USDC per trade)
        equity = [100.0]
        for r in returns:
            equity.append(equity[-1] * (1 + r / 100))

        sharpe = calculate_sharpe(returns)
        max_dd = calculate_max_drawdown(equity)

        summary[f"horizon_{label}"] = {
            "count": len(valid),
            "win_rate": len(wins) / len(valid) if valid else 0,
            "avg_return_pct": sum(returns) / len(returns),
            "median_return_pct": sorted(returns)[len(returns) // 2],
            "max_return_pct": max(returns),
            "min_return_pct": min(returns),
            "total_return_pct": sum(returns),  # sum of individual trade returns
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": max_dd,
            "wins": len(wins),
            "losses": len(losses),
            "avg_win_pct": sum(wins) / len(wins) if wins else 0,
            "avg_loss_pct": sum(losses) / len(losses) if losses else 0,
            "profit_factor": (
                abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else None
            ),
        }

    return summary
