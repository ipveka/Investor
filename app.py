import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime

# Import our custom modules
from data.market_data import MarketData
from portfolio.allocation import PortfolioAllocator
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
    allocator = PortfolioAllocator(market_data)
    visualizer = PortfolioVisualizer()
    return market_data, allocator, visualizer

market_data, allocator, visualizer = load_resources()

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

# Initial investment input
initial_investment = st.sidebar.number_input(
    "Initial Investment (€)",
    min_value=1000.0,
    max_value=10000000.0,
    value=10000.0,
    step=1000.0,
    format="%.2f"
)

# Actions section (moved above allocation strategy)
st.sidebar.subheader("Actions")

# Action buttons in vertical layout, one after another
load_sample_button = st.sidebar.button("Load Sample Data")
update_data_button = st.sidebar.button("Update Market Data")
calculate_button = st.sidebar.button("Calculate Allocation", type="primary")

# Allocation strategy selection
st.sidebar.subheader("Allocation Strategy")
allocation_strategy = st.sidebar.radio(
    "Choose allocation strategy",
    ["Default Strategy", "Manual Weights"],
    index=0
)

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
                st.experimental_rerun()
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
    st.success("Market data updated successfully!")

if load_sample_button:
    with st.spinner("Loading sample data..."):
        market_data.load_sample_data()
    st.success("Sample data loaded successfully! You can now calculate allocation without relying on Yahoo Finance API.")

# Initialize session state for portfolio allocation
if 'portfolio_allocation' not in st.session_state:
    st.session_state.portfolio_allocation = None

# Calculate allocation when button is clicked
if calculate_button:
    if not all_selected_tickers:
        st.error("Please select at least one asset.")
    else:
        with st.spinner("Calculating allocation..."):
            # Add custom tickers to the appropriate lists for allocation calculation
            calculation_etfs = selected_etfs.copy()
            calculation_eu_stocks = selected_eu_stocks.copy()
            calculation_us_stocks = selected_us_stocks.copy()
            
            # Add custom tickers to the appropriate category
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
                # Use default strategy
                allocation_df = allocator.allocate_default_strategy(
                    calculation_etfs,
                    calculation_eu_stocks,
                    calculation_us_stocks,
                    initial_investment
                )
            else:
                # Use manual weights
                normalized_weights = [manual_weights[ticker] for ticker in all_selected_tickers]
                normalized_weights = np.array(normalized_weights) / sum(normalized_weights)
                
                allocation_df = allocator.allocate_custom(
                    all_selected_tickers,
                    normalized_weights,
                    initial_investment
                )
            
            # Add asset type information
            allocation_df['asset_type'] = allocation_df['ticker'].apply(
                lambda x: st.session_state.custom_ticker_types.get(x, TICKER_CATEGORIES.get(x, "Cash")) if x != "CASH" else "Cash"
            )
            
            # Add description information
            allocation_df['description'] = allocation_df['ticker'].apply(
                lambda x: st.session_state.custom_ticker_descriptions.get(x, TICKER_DESCRIPTIONS.get(x, "")) if x != "CASH" else "Cash (EUR)"
            )
            
            # Store in session state
            st.session_state.portfolio_allocation = allocation_df
            
            st.success("Portfolio allocation calculated successfully!")

# Display portfolio allocation if available
if st.session_state.portfolio_allocation is not None:
    allocation_df = st.session_state.portfolio_allocation
    
    # Display allocation summary
    st.header("Portfolio Allocation Summary")
    
    # Create columns for metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Investment", f"€{initial_investment:,.2f}")
    with col2:
        allocated_amount = allocation_df[allocation_df['ticker'] != 'CASH']['amount'].sum()
        st.metric("Allocated Amount", f"€{allocated_amount:,.2f}")
    with col3:
        cash_amount = allocation_df[allocation_df['ticker'] == 'CASH']['amount'].sum() if 'CASH' in allocation_df['ticker'].values else 0
        st.metric("Cash", f"€{cash_amount:,.2f}")
    
    # Display allocation table
    st.subheader("Allocation Details")
    
    # Format the allocation table for display
    display_df = allocation_df.copy()
    display_df['weight'] = display_df['weight'].apply(lambda x: f"{x*100:.2f}%")
    display_df['amount'] = display_df['amount'].apply(lambda x: f"€{x:,.2f}")
    display_df['price'] = display_df['price'].apply(lambda x: f"€{x:,.2f}" if not pd.isna(x) else "N/A")
    display_df['market_cap'] = display_df['market_cap'].apply(
        lambda x: f"€{x/1e9:,.2f}B" if not pd.isna(x) and x > 0 else "N/A"
    )
    
    # Reorder columns for better display
    display_df = display_df[['ticker', 'description', 'asset_type', 'weight', 'amount', 'shares', 'price', 'market_cap']]
    display_df.columns = ['Ticker', 'Description', 'Asset Type', 'Weight', 'Amount', 'Shares', 'Price', 'Market Cap']
    
    st.dataframe(display_df, use_container_width=True)
    
    # Create visualization tabs
    viz_tabs = st.tabs(["Pie Chart", "Bar Chart", "Weight Chart"])
    
    with viz_tabs[0]:
        st.plotly_chart(visualizer.create_allocation_pie_chart(allocation_df), use_container_width=True)
    
    with viz_tabs[1]:
        st.plotly_chart(visualizer.create_allocation_bar_chart(allocation_df), use_container_width=True)
    
    with viz_tabs[2]:
        st.plotly_chart(visualizer.create_weight_chart(allocation_df), use_container_width=True)
    
    # Add export functionality
    st.subheader("Export Portfolio")
    
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
