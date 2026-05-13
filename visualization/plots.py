import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

class PortfolioVisualizer:
    def __init__(self):
        """Initialize the PortfolioVisualizer."""
        pass
    
    def create_allocation_pie_chart(self, allocation_df):
        """
        Create a pie chart showing the portfolio allocation.
        
        Parameters:
        - allocation_df: DataFrame with allocation details
        
        Returns:
        - Plotly figure
        """
        # Group by asset type if available, otherwise use tickers directly
        if 'asset_type' in allocation_df.columns:
            fig = px.pie(
                allocation_df, 
                values='amount', 
                names='asset_type', 
                title='Portfolio Allocation by Asset Type',
                hover_data=['ticker', 'weight', 'amount'],
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
        else:
            fig = px.pie(
                allocation_df, 
                values='amount', 
                names='ticker', 
                title='Portfolio Allocation by Ticker',
                hover_data=['weight', 'amount', 'shares'],
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
            margin=dict(t=50, b=100, l=10, r=10)
        )
        
        return fig
    
    def create_allocation_bar_chart(self, allocation_df):
        """
        Create a bar chart showing the portfolio allocation.
        
        Parameters:
        - allocation_df: DataFrame with allocation details
        
        Returns:
        - Plotly figure
        """
        # Sort by amount descending
        sorted_df = allocation_df.sort_values('amount', ascending=False)
        
        fig = px.bar(
            sorted_df,
            x='ticker',
            y='amount',
            title='Portfolio Allocation by Amount',
            hover_data=['weight', 'shares', 'price'],
            color='ticker',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        
        fig.update_layout(
            xaxis_title='Ticker',
            yaxis_title='Amount',
            legend_title='Ticker',
            showlegend=False,
            margin=dict(t=50, b=50, l=10, r=10)
        )
        
        return fig
    
    def create_weight_chart(self, allocation_df, target_weights=None):
        """
        Create a chart comparing actual weights vs target weights.
        
        Parameters:
        - allocation_df: DataFrame with allocation details
        - target_weights: Dictionary mapping tickers to target weights
        
        Returns:
        - Plotly figure
        """
        if target_weights is None:
            # If no target weights provided, just show actual weights
            sorted_df = allocation_df.sort_values('weight', ascending=False)
            
            fig = px.bar(
                sorted_df,
                x='ticker',
                y='weight',
                title='Portfolio Weights',
                hover_data=['amount', 'shares', 'price'],
                color='ticker',
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            
            fig.update_layout(
                xaxis_title='Ticker',
                yaxis_title='Weight',
                legend_title='Ticker',
                showlegend=False,
                margin=dict(t=50, b=50, l=10, r=10)
            )
            
            return fig
        else:
            # Create a comparison chart
            comparison_data = []
            
            for ticker, row in allocation_df.iterrows():
                actual_weight = row['weight']
                target_weight = target_weights.get(ticker, 0)
                
                comparison_data.append({
                    'ticker': ticker,
                    'Actual Weight': actual_weight,
                    'Target Weight': target_weight,
                    'Difference': actual_weight - target_weight
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            sorted_df = comparison_df.sort_values('Actual Weight', ascending=False)
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=sorted_df['ticker'],
                y=sorted_df['Actual Weight'],
                name='Actual Weight',
                marker_color='rgb(55, 83, 109)'
            ))
            
            fig.add_trace(go.Bar(
                x=sorted_df['ticker'],
                y=sorted_df['Target Weight'],
                name='Target Weight',
                marker_color='rgb(26, 118, 255)'
            ))
            
            fig.update_layout(
                title='Actual vs Target Weights',
                xaxis_title='Ticker',
                yaxis_title='Weight',
                barmode='group',
                margin=dict(t=50, b=50, l=10, r=10)
            )

            return fig

    def create_backtest_chart(self, portfolio_series, benchmark_series=None, benchmark_label="Benchmark"):
        """Cumulative return chart for a portfolio, optionally against a benchmark.

        Both inputs are pandas Series indexed by date, starting near 1.0.
        """
        fig = go.Figure()
        if portfolio_series is not None and not portfolio_series.empty:
            fig.add_trace(go.Scatter(
                x=portfolio_series.index, y=portfolio_series.values,
                mode='lines', name='Portfolio',
                line=dict(color='rgb(26, 118, 255)', width=2),
            ))
        if benchmark_series is not None and not benchmark_series.empty:
            fig.add_trace(go.Scatter(
                x=benchmark_series.index, y=benchmark_series.values,
                mode='lines', name=benchmark_label,
                line=dict(color='rgb(180, 180, 180)', width=2, dash='dash'),
            ))
        fig.update_layout(
            title='Backtest: cumulative return',
            xaxis_title='Date',
            yaxis_title='Growth of €1',
            margin=dict(t=50, b=50, l=10, r=10),
            legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
        )
        return fig

    def create_correlation_heatmap(self, correlation_df):
        """Plotly heatmap of a correlation matrix."""
        if correlation_df is None or correlation_df.empty:
            fig = go.Figure()
            fig.update_layout(
                title='Correlation Matrix (not enough data)',
                margin=dict(t=50, b=50, l=10, r=10),
            )
            return fig

        fig = px.imshow(
            correlation_df,
            x=correlation_df.columns,
            y=correlation_df.index,
            color_continuous_scale='RdBu_r',
            zmin=-1,
            zmax=1,
            aspect='auto',
            title='Asset Correlation (daily returns)',
        )
        fig.update_layout(margin=dict(t=50, b=50, l=10, r=10))
        return fig
