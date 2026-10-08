"""Pod Risk Monitor

Measures the risk of a mock 9-stock book: volatility, VaR and drawdown,
and checks each against traffic-light limits.

Assumptions:
- Data comes from Yahoo Finance (yfinance); the latest row is a live, unsettled price.
- All positions are converted to USD.
- Equal weights, reset to 1/9 each day (a simplification).
- Tickers were chosen with hindsight, so growth is NOT a track record.
- Limits are illustrative placeholders, not any fund's real rules.
"""

import pandas as pd
import plotly.express as px
import yfinance as yf

# ---------- Settings ----------
TICKERS = ["AAPL", "MSFT", "NVDA", "JPM", "AMD", "PLTR", "PRU.L", "SHEL.L", "AZN.L"]
UK_TICKERS = ["PRU.L", "SHEL.L", "AZN.L"]
HISTORY = "2y"
TRADING_DAYS = 252
VAR_CONFIDENCE = 0.95

# (amber, red) thresholds, as loss/risk magnitudes. Illustrative placeholders.
LIMITS = {
    "vol": (0.15, 0.25),
    "var": (0.02, 0.03),
    "drawdown": (0.05, 0.10),
}
STATUS_ICONS = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}


def load_prices(tickers, period):
    """Download daily closing prices for each ticker."""
    return yf.download(tickers, period=period, progress=False)["Close"]


def convert_to_usd(prices, uk_tickers, period):
    """Convert London prices from pence to US dollars using GBP/USD."""
    fx = yf.download(["GBPUSD=X"], period=period, progress=False)["Close"]["GBPUSD=X"]
    fx = fx.reindex(prices.index).ffill()
    prices_usd = prices.copy()
    prices_usd[uk_tickers] = prices[uk_tickers].div(100).mul(fx, axis=0)
    return prices_usd


def book_returns(prices_usd):
    """Daily returns of an equal-weighted book."""
    returns = prices_usd.pct_change().dropna()
    if returns.empty:
        raise SystemExit("No data after cleaning - download probably failed. Run again.")
    weights = pd.Series(1 / len(returns.columns), index=returns.columns)
    return (returns * weights).sum(axis=1)


def risk_metrics(portfolio_returns):
    """Compute growth of 100, drawdown, volatility and VaR."""
    growth = (1 + portfolio_returns).cumprod() * 100
    drawdown = growth / growth.cummax() - 1
    return {
        "growth": growth,
        "drawdown": drawdown,
        "current_drawdown": drawdown.iloc[-1],
        "annual_vol": portfolio_returns.std() * TRADING_DAYS ** 0.5,
        "var": portfolio_returns.quantile(1 - VAR_CONFIDENCE),
    }


def risk_contributions(prices_usd):
    """Each position's share of book volatility (shares add up to 100%)."""
    returns = prices_usd.pct_change().dropna()
    weight = 1 / len(returns.columns)
    book = returns.mean(axis=1)
    contributions = returns.apply(lambda col: weight * col.cov(book)) / book.var()
    return contributions.sort_values()


def status(value, amber, red):
    """Return GREEN, AMBER or RED for a risk number (higher = worse)."""
    if value >= red:
        return "RED"
    if value >= amber:
        return "AMBER"
    return "GREEN"


def row(label, value):
    """Print one aligned line of the report."""
    print(f"{label:<24}{value}")


def print_report(metrics):
    """Print a clean risk summary with limit checks."""
    print("=" * 40)
    print("POD RISK MONITOR")
    print("=" * 40)
    row("Positions:", len(TICKERS))
    row("Value of 100 invested:", f"{metrics['growth'].iloc[-1]:.1f}")
    row("Annualised volatility:", f"{metrics['annual_vol']:.1%}")
    row(f"{VAR_CONFIDENCE:.0%} 1-day VaR:", f"{metrics['var']:.2%}")
    row("Max drawdown:", f"{metrics['drawdown'].min():.1%}")
    row("Trough date:", metrics["drawdown"].idxmin().date())
    print("-" * 40)
    print("LIMITS")
    checks = [
        ("Volatility", metrics["annual_vol"], LIMITS["vol"]),
        ("1-day VaR", -metrics["var"], LIMITS["var"]),
        ("Current drawdown", abs(metrics["current_drawdown"]), LIMITS["drawdown"]),
    ]
    for name, value, (amber, red) in checks:
        light = STATUS_ICONS[status(value, amber, red)]
        row(name + ":", f"{light} {value:.2%} (amber {amber:.0%}, red {red:.0%})")
    print("=" * 40)


def plot_growth(growth):
    """Show the growth-of-100 chart in the browser."""
    fig = px.line(growth, title="Pod Risk Monitor: growth of 100")
    fig.update_layout(template="plotly_dark", showlegend=False, yaxis_title="Value of 100 invested")
    fig.show()


def main():
    prices = load_prices(TICKERS, HISTORY)
    prices_usd = convert_to_usd(prices, UK_TICKERS, HISTORY)
    portfolio_returns = book_returns(prices_usd)
    metrics = risk_metrics(portfolio_returns)
    print_report(metrics)
    plot_growth(metrics["growth"])


if __name__ == "__main__":
    main()