# Investor
# Portfolio Management Tool

A Streamlit application for building and managing investment portfolios with customizable allocation strategies.

## Features

- **Portfolio Builder**: Create portfolios with ETFs, European stocks, and US stocks
- **Default Allocation Strategy**: 
  - 50% for ETFs (equal weight for each ETF)
  - 40% for European stocks weighted by market cap
  - 10% for US stocks with inverted market cap weighting
- **Custom Allocation**: Manually select assets and assign weights
- **Portfolio Visualization**: Interactive charts to visualize your portfolio
- **Market Data**: Automatic fetching of latest prices and market cap data
- **Export Functionality**: Download your portfolio as CSV

## Getting Started

### Installation

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the App

```
streamlit run app.py
```

## Project Structure

- `app.py` - Main Streamlit application
- `data/` - Data handling and market data retrieval
- `portfolio/` - Portfolio allocation strategies
- `visualization/` - Plot generation
