#!/usr/bin/env python3
"""Investment Agent — paper trading bot aiming to turn $100 into $200 by May 9."""

import argparse
import time
import schedule
from datetime import datetime, date
from agent import TradingAgent
from config import RUN_INTERVAL_MINUTES, END_DATE


def run_once():
    """Run a single trading cycle."""
    if date.today() > END_DATE:
        print("Past the deadline (May 9). Agent is stopped.")
        return False

    agent = TradingAgent()
    summary = agent.run()
    print(summary)
    return True


def run_continuous():
    """Run the agent continuously on a schedule."""
    print(f"Starting continuous mode — running every {RUN_INTERVAL_MINUTES} minutes")
    print(f"Deadline: {END_DATE}")
    print()

    # Run immediately on start
    if not run_once():
        return

    schedule.every(RUN_INTERVAL_MINUTES).minutes.do(_scheduled_run)

    while True:
        schedule.run_pending()
        time.sleep(10)


def _scheduled_run():
    if date.today() > END_DATE:
        print("Past the deadline. Stopping.")
        return schedule.CancelJob
    agent = TradingAgent()
    agent.run()


def show_status():
    """Show current portfolio status without trading."""
    from portfolio import Portfolio
    from market_data import get_price

    portfolio = Portfolio()
    prices = {}
    for ticker in portfolio.positions:
        price = get_price(ticker)
        if price is not None:
            prices[ticker] = price

    print(portfolio.summary(prices))

    if portfolio.trades:
        print(f"\n  RECENT TRADES (last 10):")
        for trade in portfolio.trades[-10:]:
            print(
                f"    {trade.timestamp[:16]}  {trade.side:4s}  {trade.ticker:10s}"
                f"  {trade.shares:.4f} @ ${trade.price:.2f}  (${trade.value:.2f})"
                f"  — {trade.reason}"
            )


def reset():
    """Reset portfolio to starting state."""
    import os
    from config import PORTFOLIO_FILE, TRADES_FILE, LOG_FILE
    for f in [PORTFOLIO_FILE, TRADES_FILE, LOG_FILE]:
        if os.path.exists(f):
            os.remove(f)
    print("Portfolio reset to $100.00")


def main():
    parser = argparse.ArgumentParser(
        description="Investment Agent — $100 to $200 by May 9"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("run", help="Run one trading cycle")
    subparsers.add_parser("start", help="Run continuously on schedule")
    subparsers.add_parser("status", help="Show portfolio status")
    subparsers.add_parser("reset", help="Reset portfolio to $100")

    args = parser.parse_args()

    if args.command == "run":
        run_once()
    elif args.command == "start":
        run_continuous()
    elif args.command == "status":
        show_status()
    elif args.command == "reset":
        reset()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
