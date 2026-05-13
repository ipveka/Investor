import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime

# Import our custom modules
from data.market_data import MarketData
from data.fx import FXConverter, SUPPORTED_BASE_CURRENCIES, currency_symbol
from portfolio.allocation import PortfolioAllocator
from portfolio.persistence import PortfolioStore
from portfolio import risk
from visualization.plots import PortfolioVisualizer
from config import (
    ETF_TICKERS, EU_STOCK_TICKERS, US_STOCK_TICKERS,
    TICKER_DESCRIPTIONS, TICKER_CATEGORIES,
    DEFAULT_ETF_ALLOCATION, DEFAULT_EU_STOCKS_ALLOCATION, DEFAULT_US_STOCKS_ALLOCATION
)

# Set page config
st.set_page_config(
    page_title="Investor Tool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize our classes
@st.cache_resource
def load_resources():
    market_data = MarketData()
    fx_converter = FXConverter()
    allocator = PortfolioAllocator(market_data, fx_converter=fx_converter)
    visualizer = PortfolioVisualizer()
    store = PortfolioStore()
    return market_data, fx_converter, allocator, visualizer, store

market_data, fx_converter, allocator, visualizer, store = load_resources()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_history(tickers, period):
    """Cache yfinance history per (tickers, period) for one hour."""
    return risk.fetch_history(list(tickers), period=period)

# App title and description
st.title("Portfolio Builder 📈")
st.markdown("""
This app helps you build and manage your investment portfolio. You can:
- Select assets from ETFs, European stocks, and US stocks
- Calculate weights based on the default strategy or set your own
- Visualize your portfolio allocation
""")

# Sidebar for inputs
st.sidebar.header("Portfolio Settings")

# Base currency selector. Everything below is denominated in this currency;
# prices and market caps fetched in other currencies are converted via spot FX.
base_currency = st.sidebar.selectbox(
    "Base Currency", SUPPORTED_BASE_CURRENCIES, index=0,
    help="All totals are expressed in this currency. Native prices are still shown alongside.",
)
allocator.base_currency = base_currency
sym = currency_symbol(base_currency)

# Initial investment input
initial_investment = st.sidebar.number_input(
    f"Initial Investment ({sym})",
    min_value=1000.0,
    max_value=10000000.0,
    value=10000.0,
    step=1000.0,
    format="%.2f"
)

# Actions section (moved above allocation strategy)
st.sidebar.subheader("Actions")

# Action buttons. Allocation is now computed reactively as inputs change;
# these buttons handle one-shot side effects only.
load_sample_button = st.sidebar.button("Load Sample Data")
update_data_button = st.sidebar.button("Update Market Data")

# Allocation strategy selection
st.sidebar.subheader("Allocation Strategy")
allocation_strategy = st.sidebar.radio(
    "Choose allocation strategy",
    ["Default Strategy", "Manual Weights"],
    index=0
)

# Saved portfolios (sidebar)
st.sidebar.subheader("Saved Portfolios")
snapshots_df = store.list_snapshots()
if snapshots_df.empty:
    st.sidebar.caption("No saved portfolios yet. Save one after calculating an allocation.")
else:
    snapshot_names = snapshots_df["name"].tolist()
    selected_snapshot = st.sidebar.selectbox("Load snapshot", snapshot_names, key="snapshot_selector")
    if selected_snapshot:
        meta = snapshots_df[snapshots_df["name"] == selected_snapshot].iloc[0]
        st.sidebar.caption(
            f"Saved {meta['created_at']} | {meta['initial_investment']:,.0f} | {meta['strategy']}"
        )
    load_col, del_col = st.sidebar.columns(2)
    if load_col.button("Load", key="load_snapshot_button"):
        loaded_df, loaded_investment, loaded_strategy, _ = store.load(selected_snapshot)
        st.session_state.portfolio_allocation = loaded_df
        st.session_state.loaded_snapshot_investment = loaded_investment
        st.session_state.loaded_snapshot_strategy = loaded_strategy
        st.sidebar.success(f"Loaded '{selected_snapshot}'")
        st.rerun()
    if del_col.button("Delete", key="delete_snapshot_button"):
        store.delete(selected_snapshot)
        st.sidebar.success(f"Deleted '{selected_snapshot}'")
        st.rerun()

# Main content area - Asset Selection
st.header("Asset Selection")

# Create tabs for different asset types in the main area
asset_tabs = st.tabs(["ETFs", "European Stocks", "US Stocks", "Custom Tickers"])

# ETF selection
with asset_tabs[0]:
    st.subheader("📈 ETFs")
    
    # Create columns for better layout
    cols = st.columns(3)
    selected_etfs = []
    
    for i, ticker in enumerate(ETF_TICKERS):
        col_idx = i % 3
        if cols[col_idx].checkbox(f"{ticker} - {TICKER_DESCRIPTIONS[ticker]}", value=True, key=f"etf_{ticker}"):
            selected_etfs.append(ticker)

# European stocks selection
with asset_tabs[1]:
    st.subheader("🇪🇺 European Stocks")
    
    # Create columns for better layout
    cols = st.columns(3)
    selected_eu_stocks = []
    
    for i, ticker in enumerate(EU_STOCK_TICKERS):
        col_idx = i % 3
        if cols[col_idx].checkbox(f"{ticker} - {TICKER_DESCRIPTIONS[ticker]}", value=True, key=f"eu_{ticker}"):
            selected_eu_stocks.append(ticker)

# US stocks selection
with asset_tabs[2]:
    st.subheader("🇺🇸 US Stocks")
    
    # Create columns for better layout
    cols = st.columns(3)
    selected_us_stocks = []
    
    for i, ticker in enumerate(US_STOCK_TICKERS):
        col_idx = i % 3
        if cols[col_idx].checkbox(f"{ticker} - {TICKER_DESCRIPTIONS[ticker]}", value=True, key=f"us_{ticker}"):
            selected_us_stocks.append(ticker)

# Custom ticker selection
with asset_tabs[3]:
    st.subheader("➕ Add Custom Tickers")
    
    # Initialize session state for custom tickers if not exists
    if 'custom_tickers' not in st.session_state:
        st.session_state.custom_tickers = []
        st.session_state.custom_ticker_types = {}
        st.session_state.custom_ticker_descriptions = {}
    
    # Input for new ticker
    col1, col2, col3 = st.columns([2, 2, 1])
    
    new_ticker = col1.text_input("Ticker Symbol (e.g., AAPL, MSFT.US)", key="new_ticker_input")
    ticker_type = col2.selectbox(
        "Asset Type", 
        ["ETF", "European Stock", "US Stock"],
        key="new_ticker_type"
    )
    ticker_description = col1.text_input("Description (optional)", key="new_ticker_description")
    
    # Add button
    if col3.button("Add Ticker", key="add_ticker_button"):
        if new_ticker and new_ticker not in st.session_state.custom_tickers and new_ticker not in ETF_TICKERS + EU_STOCK_TICKERS + US_STOCK_TICKERS:
            st.session_state.custom_tickers.append(new_ticker)
            st.session_state.custom_ticker_types[new_ticker] = ticker_type
            st.session_state.custom_ticker_descriptions[new_ticker] = ticker_description or f"Custom {ticker_type}"
            st.success(f"Added {new_ticker} as {ticker_type}")
        elif not new_ticker:
            st.error("Please enter a ticker symbol")
        elif new_ticker in st.session_state.custom_tickers or new_ticker in ETF_TICKERS + EU_STOCK_TICKERS + US_STOCK_TICKERS:
            st.error(f"Ticker {new_ticker} already exists")
    
    # Display and select custom tickers
    if st.session_state.custom_tickers:
        st.subheader("Your Custom Tickers")
        
        # Create columns for better layout
        cols = st.columns(3)
        selected_custom_tickers = []
        
        for i, ticker in enumerate(st.session_state.custom_tickers):
            col_idx = i % 3
            description = st.session_state.custom_ticker_descriptions.get(ticker, "")
            ticker_display = f"{ticker} - {description}" if description else ticker
            
            if cols[col_idx].checkbox(ticker_display, value=True, key=f"custom_{ticker}"):
                selected_custom_tickers.append(ticker)
            
            # Add a remove button for each custom ticker
            if cols[col_idx].button("Remove", key=f"remove_{ticker}"):
                st.session_state.custom_tickers.remove(ticker)
                if ticker in st.session_state.custom_ticker_types:
                    del st.session_state.custom_ticker_types[ticker]
                if ticker in st.session_state.custom_ticker_descriptions:
                    del st.session_state.custom_ticker_descriptions[ticker]
                st.rerun()
    else:
        st.info("No custom tickers added yet. Add tickers above.")

# Combine all selected tickers
all_selected_tickers = selected_etfs + selected_eu_stocks + selected_us_stocks
if 'selected_custom_tickers' in locals():
    all_selected_tickers += selected_custom_tickers

# Manual weight input if selected
manual_weights = {}
if allocation_strategy == "Manual Weights" and all_selected_tickers:
    st.header("Manual Weight Assignment")
    st.markdown("Set weights for each asset (will be normalized to sum to 100%)")
    
    # Create columns for better layout
    weight_cols = st.columns(3)
    total_weight = 0
    
    for i, ticker in enumerate(all_selected_tickers):
        col_idx = i % 3
        weight = weight_cols[col_idx].slider(
            f"{ticker} - {TICKER_DESCRIPTIONS.get(ticker, st.session_state.custom_ticker_descriptions.get(ticker, ''))}",
            min_value=0.0,
            max_value=100.0,
            value=100.0 / len(all_selected_tickers),
            step=1.0,
            format="%.1f%%",
            key=f"weight_{ticker}"
        )
        manual_weights[ticker] = weight / 100.0
        total_weight += weight
    
    # Display total weight
    st.markdown(f"**Total weight: {total_weight:.1f}%**")
    if abs(total_weight - 100.0) > 0.1:
        st.warning("Total weight is not 100%. Weights will be normalized.")

# Main content area
if update_data_button:
    with st.spinner("Updating market data..."):
        market_data.update_data(ETF_TICKERS + EU_STOCK_TICKERS + US_STOCK_TICKERS)
        fx_converter._cache.clear()
        try:
            os.remove(fx_converter.cache_file)
        except OSError:
            pass
    cached_history.clear()
    st.success("Market data updated successfully!")

if load_sample_button:
    with st.spinner("Loading sample data..."):
        market_data.load_sample_data()
    st.success("Sample data loaded successfully! You can now calculate allocation without relying on Yahoo Finance API.")

# Initialize session state for portfolio allocation
if 'portfolio_allocation' not in st.session_state:
    st.session_state.portfolio_allocation = None

# Reactive computation: rerun on every widget change, store latest result.
if all_selected_tickers:
    with st.spinner("Computing allocation..."):
        try:
            calculation_etfs = list(selected_etfs)
            calculation_eu_stocks = list(selected_eu_stocks)
            calculation_us_stocks = list(selected_us_stocks)

            if 'selected_custom_tickers' in locals() and selected_custom_tickers:
                for ticker in selected_custom_tickers:
                    ticker_type = st.session_state.custom_ticker_types.get(ticker, "ETF")
                    if ticker_type == "ETF":
                        calculation_etfs.append(ticker)
                    elif ticker_type == "European Stock":
                        calculation_eu_stocks.append(ticker)
                    elif ticker_type == "US Stock":
                        calculation_us_stocks.append(ticker)

            if allocation_strategy == "Default Strategy":
                allocation_df = allocator.allocate_default_strategy(
                    calculation_etfs, calculation_eu_stocks, calculation_us_stocks,
                    initial_investment,
                )
            else:
                normalized_weights = np.array(
                    [manual_weights[t] for t in all_selected_tickers], dtype=float,
                )
                normalized_weights = normalized_weights / normalized_weights.sum()
                allocation_df = allocator.allocate_custom(
                    all_selected_tickers, normalized_weights, initial_investment,
                )

            allocation_df['asset_type'] = allocation_df['ticker'].apply(
                lambda x: st.session_state.custom_ticker_types.get(x, TICKER_CATEGORIES.get(x, "Cash"))
                if x != "CASH" else "Cash"
            )
            allocation_df['description'] = allocation_df['ticker'].apply(
                lambda x: st.session_state.custom_ticker_descriptions.get(x, TICKER_DESCRIPTIONS.get(x, ""))
                if x != "CASH" else "Cash (EUR)"
            )
            st.session_state.portfolio_allocation = allocation_df
        except Exception as exc:
            st.error(f"Could not compute allocation: {exc}")
else:
    st.session_state.portfolio_allocation = None

# Display portfolio allocation if available
if st.session_state.portfolio_allocation is not None:
    allocation_df = st.session_state.portfolio_allocation
    
    # Display allocation summary
    st.header("Portfolio Allocation Summary")
    
    # Derive totals from the allocation itself so the summary stays consistent
    # whether the data came from a fresh calculation or a loaded snapshot.
    displayed_investment = allocation_df['amount'].sum()
    allocated_amount = allocation_df[allocation_df['ticker'] != 'CASH']['amount'].sum()
    cash_amount = (
        allocation_df[allocation_df['ticker'] == 'CASH']['amount'].sum()
        if 'CASH' in allocation_df['ticker'].values
        else 0
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Investment", f"{sym}{displayed_investment:,.2f}")
    with col2:
        st.metric("Allocated Amount", f"{sym}{allocated_amount:,.2f}")
    with col3:
        st.metric("Cash", f"{sym}{cash_amount:,.2f}")

    # Display allocation table
    st.subheader("Allocation Details")

    # Format the allocation table for display. Prices and market caps are
    # already converted to the base currency; raw_price is shown next to it.
    display_df = allocation_df.copy()
    if 'raw_price' not in display_df.columns:
        display_df['raw_price'] = display_df['price']
    if 'currency' not in display_df.columns:
        display_df['currency'] = base_currency
    display_df['weight'] = display_df['weight'].apply(lambda x: f"{x*100:.2f}%")
    display_df['amount'] = display_df['amount'].apply(lambda x: f"{sym}{x:,.2f}")
    display_df['price'] = display_df['price'].apply(
        lambda x: f"{sym}{x:,.2f}" if not pd.isna(x) else "N/A"
    )
    display_df['native_price'] = display_df.apply(
        lambda row: f"{currency_symbol(row['currency'])}{row['raw_price']:,.2f}"
        if not pd.isna(row['raw_price']) else "N/A",
        axis=1,
    )
    display_df['market_cap'] = display_df['market_cap'].apply(
        lambda x: f"{sym}{x/1e9:,.2f}B" if not pd.isna(x) and x > 0 else "N/A"
    )

    display_df = display_df[['ticker', 'description', 'asset_type', 'weight',
                             'amount', 'shares', 'price', 'native_price', 'market_cap']]
    display_df.columns = ['Ticker', 'Description', 'Asset Type', 'Weight',
                          'Amount', 'Shares', f'Price ({base_currency})', 'Native Price',
                          f'Market Cap ({base_currency})']
    
    st.dataframe(display_df, use_container_width=True)
    
    # Create visualization tabs
    viz_tabs = st.tabs(["Pie Chart", "Bar Chart", "Weight Chart", "Risk Metrics", "Backtest"])

    with viz_tabs[0]:
        st.plotly_chart(visualizer.create_allocation_pie_chart(allocation_df), use_container_width=True)

    with viz_tabs[1]:
        st.plotly_chart(visualizer.create_allocation_bar_chart(allocation_df), use_container_width=True)

    with viz_tabs[2]:
        st.plotly_chart(visualizer.create_weight_chart(allocation_df), use_container_width=True)

    with viz_tabs[3]:
        st.markdown("Historical volatility, drawdown, Sharpe ratio, and asset correlations.")
        risk_col1, risk_col2 = st.columns([1, 1])
        period = risk_col1.selectbox(
            "History window", ["1y", "3y", "5y"], index=1, key="risk_period"
        )
        risk_free_pct = risk_col2.number_input(
            "Risk-free rate (annual %)", min_value=0.0, max_value=15.0, value=2.0, step=0.25,
            key="risk_free_pct",
        )
        risk_free_rate = risk_free_pct / 100.0

        risk_assets = allocation_df[
            (allocation_df["ticker"] != "CASH") & (allocation_df["amount"] > 0)
        ]
        if risk_assets.empty:
            st.info("No invested assets to analyze.")
        else:
            tickers = tuple(risk_assets["ticker"].tolist())
            with st.spinner("Fetching historical prices..."):
                prices = cached_history(tickers, period)

            if prices.empty:
                st.warning(
                    "Could not fetch historical price data. Yahoo Finance may be rate-limiting; "
                    "try again later or switch the period."
                )
            else:
                weights = dict(zip(risk_assets["ticker"], risk_assets["amount"]))
                portfolio = risk.portfolio_metrics(prices, weights, risk_free_rate)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Return",
                          f"{portfolio['total_return']*100:.2f}%" if not np.isnan(portfolio['total_return']) else "N/A")
                m2.metric("Volatility (ann.)",
                          f"{portfolio['volatility']*100:.2f}%" if not np.isnan(portfolio['volatility']) else "N/A")
                m3.metric("Max Drawdown",
                          f"{portfolio['max_drawdown']*100:.2f}%" if not np.isnan(portfolio['max_drawdown']) else "N/A")
                m4.metric("Sharpe Ratio",
                          f"{portfolio['sharpe']:.2f}" if not np.isnan(portfolio['sharpe']) else "N/A")

                st.subheader("Per-asset metrics")
                per_ticker = risk.per_ticker_metrics(prices, risk_free_rate)
                missing = [t for t in tickers if t not in per_ticker.index]
                if missing:
                    st.caption(f"No history for: {', '.join(missing)}")
                if not per_ticker.empty:
                    display_metrics = per_ticker.copy()
                    display_metrics["volatility"] = display_metrics["volatility"].apply(
                        lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A"
                    )
                    display_metrics["max_drawdown"] = display_metrics["max_drawdown"].apply(
                        lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A"
                    )
                    display_metrics["total_return"] = display_metrics["total_return"].apply(
                        lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A"
                    )
                    display_metrics["sharpe"] = display_metrics["sharpe"].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                    )
                    display_metrics.columns = ["Volatility", "Max Drawdown", "Sharpe", "Total Return"]
                    st.dataframe(display_metrics, use_container_width=True)

                st.subheader("Correlation matrix")
                corr = risk.correlation_matrix(prices)
                st.plotly_chart(
                    visualizer.create_correlation_heatmap(corr), use_container_width=True
                )

    with viz_tabs[4]:
        st.markdown("How would this allocation have performed historically vs. a benchmark?")
        bt_col1, bt_col2 = st.columns([1, 1])
        bt_period = bt_col1.selectbox(
            "Backtest window", ["1y", "3y", "5y"], index=1, key="bt_period"
        )
        benchmark = bt_col2.text_input(
            "Benchmark ticker", value="SPY", key="bt_benchmark",
            help="Ticker to compare against (e.g. SPY, URTH, ^GSPC, VWCE.DE)",
        ).strip()

        bt_assets = allocation_df[
            (allocation_df["ticker"] != "CASH") & (allocation_df["amount"] > 0)
        ]
        if bt_assets.empty:
            st.info("No invested assets to back-test.")
        else:
            bt_tickers = tuple(bt_assets["ticker"].tolist())
            with st.spinner("Building backtest..."):
                bt_prices = cached_history(bt_tickers, bt_period)
                bench_prices = cached_history((benchmark,), bt_period) if benchmark else None

            if bt_prices.empty:
                st.warning("Could not fetch portfolio history. Try a different window or update market data.")
            else:
                weights = dict(zip(bt_assets["ticker"], bt_assets["amount"]))
                portfolio_path = risk.cumulative_returns(bt_prices, weights)
                benchmark_path = (
                    risk.benchmark_cumulative(bench_prices)
                    if bench_prices is not None and not bench_prices.empty
                    else pd.Series(dtype=float)
                )

                if portfolio_path.empty:
                    st.warning("No overlapping price history for the selected assets.")
                else:
                    final_portfolio = float(portfolio_path.iloc[-1] - 1.0)
                    final_benchmark = (
                        float(benchmark_path.iloc[-1] - 1.0) if not benchmark_path.empty else None
                    )
                    bt_m1, bt_m2, bt_m3 = st.columns(3)
                    bt_m1.metric("Portfolio return", f"{final_portfolio*100:.2f}%")
                    if final_benchmark is not None:
                        bt_m2.metric(f"{benchmark} return", f"{final_benchmark*100:.2f}%")
                        bt_m3.metric(
                            "Alpha (port. - bench.)",
                            f"{(final_portfolio - final_benchmark)*100:.2f}%",
                        )
                    elif benchmark:
                        bt_m2.warning(f"Could not fetch '{benchmark}' history.")

                    st.plotly_chart(
                        visualizer.create_backtest_chart(
                            portfolio_path,
                            benchmark_path if not benchmark_path.empty else None,
                            benchmark_label=benchmark or "Benchmark",
                        ),
                        use_container_width=True,
                    )

    # Save / export
    st.subheader("Save & Export")
    save_col1, save_col2 = st.columns([3, 1])
    snapshot_name = save_col1.text_input(
        "Snapshot name", key="snapshot_name_input", placeholder="e.g. core-2026-05"
    )
    overwrite = save_col2.checkbox("Overwrite", key="snapshot_overwrite")
    if st.button("Save Portfolio", key="save_snapshot_button"):
        try:
            store.save(
                snapshot_name,
                allocation_df,
                initial_investment,
                allocation_strategy,
                overwrite=overwrite,
            )
            st.success(f"Saved '{snapshot_name.strip()}'")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            if "UNIQUE constraint" in str(exc):
                st.error(
                    f"A snapshot named '{snapshot_name.strip()}' already exists. "
                    "Check 'Overwrite' to replace it."
                )
            else:
                st.error(f"Could not save snapshot: {exc}")

    # Create a download button for CSV export
    csv = allocation_df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"portfolio_allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    # Display instructions if no allocation has been calculated yet
    st.info("Select your assets and click 'Calculate Allocation' to see your portfolio details.")

# Add footer
st.markdown("---")
st.markdown("Portfolio Builder App | Created with Streamlit")
