"""Streamlit dashboard for the Pod Risk Monitor."""

import plotly.express as px
import streamlit as st

import main as engine

st.set_page_config(page_title="Pod Risk Monitor", page_icon="📉", layout="wide")


@st.cache_data(ttl=900)
def get_data():
    """Download and prepare everything once, then reuse it for 15 minutes."""
    prices = engine.load_prices(engine.TICKERS, engine.HISTORY)
    prices_usd = engine.convert_to_usd(prices, engine.UK_TICKERS, engine.HISTORY)
    portfolio_returns = engine.book_returns(prices_usd)
    return engine.risk_metrics(portfolio_returns), engine.risk_contributions(prices_usd)


def style(fig, title, y_title):
    """Apply the shared dark look to a chart."""
    fig.update_layout(template="plotly_dark", title=title, showlegend=False,
                      yaxis_title=y_title, xaxis_title=None)
    return fig


st.title("📉 Pod Risk Monitor")
st.caption("Mock 9-stock book, equal weights, in USD. Limits are illustrative. "
           "The latest price is live and unsettled.")

if st.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()

metrics, contributions = get_data()

# ---------- Traffic-light cards ----------
checks = [
    ("Annualised volatility", metrics["annual_vol"], engine.LIMITS["vol"]),
    ("95% 1-day VaR", -metrics["var"], engine.LIMITS["var"]),
    ("Current drawdown", abs(metrics["current_drawdown"]), engine.LIMITS["drawdown"]),
]
cols = st.columns(4)
cols[0].metric("Value of 100 invested", f"{metrics['growth'].iloc[-1]:.1f}")
for col, (name, value, (amber, red)) in zip(cols[1:], checks):
    light = engine.STATUS_ICONS[engine.status(value, amber, red)]
    col.metric(f"{light} {name}", f"{value:.2%}")
    col.caption(f"Amber {amber:.0%} · Red {red:.0%}")

# ---------- Growth and drawdown ----------
left, right = st.columns(2)
with left:
    fig = style(px.line(metrics["growth"]), "Growth of 100", "Value of 100 invested")
    st.plotly_chart(fig, width="stretch")
with right:
    fig = style(px.area(metrics["drawdown"] * 100), "Drawdown from peak (%)", "%")
    fig.update_traces(line_color="#ff4b4b")
    st.plotly_chart(fig, width="stretch")

# ---------- Where the risk comes from ----------
fig = px.bar(x=contributions.values * 100, y=contributions.index, orientation="h")
fig = style(fig, "Share of book volatility by position (%)", None)
fig.update_layout(xaxis_title="% of book volatility")
st.plotly_chart(fig, width="stretch")

top3 = contributions.sort_values(ascending=False).head(3)
st.caption(f"Top 3 positions ({', '.join(top3.index)}) drive {top3.sum():.0%} of book "
           f"volatility, from {3 / len(contributions):.0%} of positions.")

with st.expander("Method and limitations"):
    st.markdown(
        "- Volatility: daily standard deviation x sqrt(252).\n"
        "- VaR: historical 5th percentile of daily book returns. It ignores how bad the tail gets.\n"
        "- Drawdown: fall from the running peak of the equal-weighted book.\n"
        "- Equal weights are reset daily (a simplification), and tickers were chosen with hindsight."
    )