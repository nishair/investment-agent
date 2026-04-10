"""AI Agent — evaluates the market, picks trades, and manages risk."""

import logging
from datetime import datetime
from portfolio import Portfolio
from market_data import get_price, get_bulk_signals
from strategies import composite_score
from config import (
    WATCHLIST, MAX_POSITION_PCT, MAX_OPEN_POSITIONS,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, TARGET_VALUE, STARTING_CASH,
    LOG_FILE, DATA_DIR,
)
import os

os.makedirs(DATA_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("agent")


class TradingAgent:
    def __init__(self):
        self.portfolio = Portfolio()

    def run(self) -> str:
        """Run one full cycle: check stops, scan market, execute trades."""
        log.info("=" * 50)
        log.info("Starting trading cycle")

        # 1. Get current prices for open positions
        position_prices = self._get_position_prices()

        # 2. Check stop-losses and take-profits
        self._check_exits(position_prices)

        # 3. Scan the full universe for opportunities
        opportunities = self._scan_universe()

        # 4. Execute the best trades
        self._execute_trades(opportunities)

        # 5. Get updated prices and return summary
        position_prices = self._get_position_prices()
        summary = self.portfolio.summary(position_prices)
        log.info("\n" + summary)
        return summary

    def _get_position_prices(self) -> dict[str, float]:
        """Fetch current prices for all open positions."""
        prices = {}
        for ticker in self.portfolio.positions:
            price = get_price(ticker)
            if price is not None:
                prices[ticker] = price
        return prices

    def _check_exits(self, prices: dict[str, float]):
        """Check stop-loss and take-profit for all positions."""
        tickers_to_check = list(self.portfolio.positions.keys())
        for ticker in tickers_to_check:
            if ticker not in prices:
                continue
            price = prices[ticker]
            pnl = self.portfolio.position_pnl(ticker, price)

            if pnl <= -STOP_LOSS_PCT:
                log.info(f"STOP LOSS: {ticker} at {pnl:.1%}")
                self.portfolio.sell(ticker, price, reason=f"stop-loss at {pnl:.1%}")

            elif pnl >= TAKE_PROFIT_PCT:
                # Take partial profit — sell 50%, let the rest ride
                log.info(f"TAKE PROFIT: {ticker} at {pnl:.1%} — selling 50%")
                self.portfolio.sell(ticker, price, pct=0.5, reason=f"take-profit at {pnl:.1%}")

    def _scan_universe(self) -> list[tuple[str, float, dict, float]]:
        """Scan all assets and rank by composite score."""
        all_tickers = []
        for category_tickers in WATCHLIST.values():
            all_tickers.extend(category_tickers)

        log.info(f"Scanning {len(all_tickers)} assets...")
        signals = get_bulk_signals(all_tickers)
        log.info(f"Got signals for {len(signals)} assets")

        scored = []
        for ticker, signal in signals.items():
            total_score, breakdown = composite_score(signal)
            scored.append((ticker, total_score, signal, signal["price"]))
            if total_score > 0.2:
                log.info(
                    f"  {ticker:10s} score={total_score:+.2f}  "
                    f"price=${signal['price']:.2f}  rsi={signal['rsi']:.0f}  "
                    f"mom={signal['momentum']:.1%}  vol_ratio={signal['vol_ratio']:.1f}"
                )

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _execute_trades(self, opportunities: list[tuple[str, float, dict, float]]):
        """Execute buy orders for the best opportunities."""
        open_positions = len(self.portfolio.positions)
        slots_available = MAX_OPEN_POSITIONS - open_positions
        cash = self.portfolio.cash

        if slots_available <= 0:
            log.info("Max positions reached, skipping buys")
            return

        if cash < 5.0:
            log.info(f"Low cash (${cash:.2f}), skipping buys")
            return

        # Adjust aggressiveness based on how far we are from target
        position_prices = self._get_position_prices()
        current_value = self.portfolio.total_value(position_prices)
        progress = (current_value - STARTING_CASH) / (TARGET_VALUE - STARTING_CASH)
        buy_threshold = self._adaptive_threshold(progress)

        buys_made = 0
        for ticker, score, signal, price in opportunities:
            if buys_made >= slots_available:
                break
            if score < buy_threshold:
                break
            if ticker in self.portfolio.positions:
                continue
            if self.portfolio.cash < 5.0:
                break

            # Position sizing: higher score = bigger position
            base_pct = MAX_POSITION_PCT
            if score > 0.5:
                size_pct = base_pct
            elif score > 0.3:
                size_pct = base_pct * 0.7
            else:
                size_pct = base_pct * 0.5

            amount = min(self.portfolio.cash, current_value * size_pct)
            amount = max(amount, 5.0)  # Minimum $5 trade

            reason = (
                f"score={score:+.2f} rsi={signal['rsi']:.0f} "
                f"mom={signal['momentum']:.1%} bb={signal['bb_pct']:.2f}"
            )
            trade = self.portfolio.buy(ticker, price, amount, reason=reason)
            if trade:
                log.info(f"BUY {ticker}: ${trade.value:.2f} @ ${price:.2f} — {reason}")
                buys_made += 1

    def _adaptive_threshold(self, progress: float) -> float:
        """Adjust buy threshold based on progress toward target.

        Early on or if behind: be more aggressive (lower threshold).
        If ahead of pace: be more selective (higher threshold).
        """
        if progress >= 0.8:
            return 0.3  # Almost there, be selective
        elif progress >= 0.4:
            return 0.15  # On track
        elif progress >= 0.0:
            return 0.1  # Normal
        else:
            return 0.05  # Behind, be aggressive
