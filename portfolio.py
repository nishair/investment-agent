"""Paper trading portfolio engine — tracks positions, cash, trades, and P&L."""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from config import STARTING_CASH, DATA_DIR, PORTFOLIO_FILE, TRADES_FILE


@dataclass
class Position:
    ticker: str
    shares: float
    avg_cost: float
    opened_at: str


@dataclass
class Trade:
    ticker: str
    side: str  # "buy" or "sell"
    shares: float
    price: float
    value: float
    reason: str
    timestamp: str


class Portfolio:
    def __init__(self):
        self.cash: float = STARTING_CASH
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self._ensure_data_dir()
        self._load()

    def _ensure_data_dir(self):
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load(self):
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE) as f:
                data = json.load(f)
            self.cash = data["cash"]
            self.positions = {
                k: Position(**v) for k, v in data["positions"].items()
            }
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE) as f:
                self.trades = [Trade(**t) for t in json.load(f)]

    def save(self):
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump({
                "cash": self.cash,
                "positions": {k: asdict(v) for k, v in self.positions.items()},
            }, f, indent=2)
        with open(TRADES_FILE, "w") as f:
            json.dump([asdict(t) for t in self.trades], f, indent=2)

    def buy(self, ticker: str, price: float, amount_usd: float, reason: str = "") -> Trade | None:
        """Buy a position. amount_usd is how much cash to spend."""
        amount_usd = min(amount_usd, self.cash)
        if amount_usd < 1.0 or price <= 0:
            return None

        shares = amount_usd / price

        if ticker in self.positions:
            pos = self.positions[ticker]
            total_shares = pos.shares + shares
            pos.avg_cost = ((pos.shares * pos.avg_cost) + (shares * price)) / total_shares
            pos.shares = total_shares
        else:
            self.positions[ticker] = Position(
                ticker=ticker,
                shares=shares,
                avg_cost=price,
                opened_at=datetime.now().isoformat(),
            )

        self.cash -= amount_usd
        trade = Trade(
            ticker=ticker,
            side="buy",
            shares=round(shares, 6),
            price=price,
            value=round(amount_usd, 2),
            reason=reason,
            timestamp=datetime.now().isoformat(),
        )
        self.trades.append(trade)
        self.save()
        return trade

    def sell(self, ticker: str, price: float, pct: float = 1.0, reason: str = "") -> Trade | None:
        """Sell a position (or fraction of it). pct=1.0 sells all."""
        if ticker not in self.positions:
            return None

        pos = self.positions[ticker]
        shares_to_sell = pos.shares * pct
        proceeds = shares_to_sell * price

        if pct >= 1.0:
            del self.positions[ticker]
        else:
            pos.shares -= shares_to_sell

        self.cash += proceeds
        trade = Trade(
            ticker=ticker,
            side="sell",
            shares=round(shares_to_sell, 6),
            price=price,
            value=round(proceeds, 2),
            reason=reason,
            timestamp=datetime.now().isoformat(),
        )
        self.trades.append(trade)
        self.save()
        return trade

    def total_value(self, prices: dict[str, float]) -> float:
        """Calculate total portfolio value given current prices."""
        position_value = sum(
            pos.shares * prices.get(pos.ticker, pos.avg_cost)
            for pos in self.positions.values()
        )
        return self.cash + position_value

    def position_pnl(self, ticker: str, current_price: float) -> float:
        """Return P&L percentage for a position."""
        if ticker not in self.positions:
            return 0.0
        pos = self.positions[ticker]
        return (current_price - pos.avg_cost) / pos.avg_cost

    def summary(self, prices: dict[str, float]) -> str:
        """Human-readable portfolio summary."""
        total = self.total_value(prices)
        pnl = total - STARTING_CASH
        pnl_pct = (pnl / STARTING_CASH) * 100

        lines = [
            f"{'='*50}",
            f"  PORTFOLIO SUMMARY",
            f"{'='*50}",
            f"  Cash:          ${self.cash:.2f}",
            f"  Positions:     {len(self.positions)}",
            f"  Total Value:   ${total:.2f}",
            f"  P&L:           ${pnl:+.2f} ({pnl_pct:+.1f}%)",
            f"  Target:        $200.00 (need {200 - total:+.2f})",
            f"  Trades Made:   {len(self.trades)}",
            f"{'='*50}",
        ]

        if self.positions:
            lines.append("  OPEN POSITIONS:")
            for ticker, pos in self.positions.items():
                price = prices.get(ticker, pos.avg_cost)
                pos_pnl = self.position_pnl(ticker, price)
                value = pos.shares * price
                lines.append(
                    f"    {ticker:10s}  {pos.shares:.4f} shares @ ${pos.avg_cost:.2f}"
                    f"  now ${price:.2f}  val=${value:.2f}  {pos_pnl:+.1%}"
                )
            lines.append(f"{'='*50}")

        return "\n".join(lines)
