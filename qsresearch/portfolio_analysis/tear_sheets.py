"""
QS Research - Performance Tear Sheets

Generate professional tear sheet reports for backtest analysis.
Based on the pyfolio-style tear sheets used in production.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from loguru import logger

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def generate_returns_tear_sheet(
    performance: pd.DataFrame,
    benchmark_returns: Optional[pd.Series] = None,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate a returns tear sheet HTML report.
    
    Args:
        performance: DataFrame with returns and portfolio_value columns
        benchmark_returns: Optional benchmark returns series
        output_path: Path to save HTML file
        
    Returns:
        HTML string of the tear sheet
    """
    if not PLOTLY_AVAILABLE:
        return "<p>Plotly not available for tear sheet generation</p>"
    
    returns = performance["returns"].values
    portfolio_value = performance["portfolio_value"].values
    dates = performance["date"] if "date" in performance.columns else pd.date_range(
        start="2020-01-01", periods=len(returns), freq="B"
    )
    
    # Create figure with subplots
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "Cumulative Returns",
            "Rolling Sharpe (6M)",
            "Monthly Returns Heatmap",
            "Return Distribution",
            "Drawdown",
            "Rolling Volatility (6M)",
        ),
        vertical_spacing=0.08,
        horizontal_spacing=0.08,
    )
    
    # 1. Cumulative Returns
    cumulative = (1 + pd.Series(returns)).cumprod() - 1
    fig.add_trace(
        go.Scatter(x=dates, y=cumulative, name="Strategy", line=dict(color="#00ff88")),
        row=1, col=1
    )
    
    if benchmark_returns is not None:
        bench_cum = (1 + benchmark_returns).cumprod() - 1
        fig.add_trace(
            go.Scatter(x=dates, y=bench_cum, name="Benchmark", line=dict(color="#888888", dash="dash")),
            row=1, col=1
        )
    
    # 2. Rolling Sharpe
    rolling_sharpe = pd.Series(returns).rolling(126).apply(
        lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
    )
    fig.add_trace(
        go.Scatter(x=dates, y=rolling_sharpe, name="Rolling Sharpe", line=dict(color="#1f77b4")),
        row=1, col=2
    )
    
    # 3. Monthly Returns Heatmap (simplified bar chart)
    monthly_returns = pd.Series(returns, index=dates).resample("M").sum()
    colors = ["#ff4444" if r < 0 else "#00ff88" for r in monthly_returns]
    fig.add_trace(
        go.Bar(x=monthly_returns.index, y=monthly_returns, marker_color=colors, name="Monthly"),
        row=2, col=1
    )
    
    # 4. Return Distribution
    fig.add_trace(
        go.Histogram(x=returns, nbinsx=50, name="Returns", marker_color="#1f77b4"),
        row=2, col=2
    )
    
    # 5. Drawdown
    cum_returns = (1 + pd.Series(returns)).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns - running_max) / running_max
    fig.add_trace(
        go.Scatter(x=dates, y=drawdown, fill="tozeroy", name="Drawdown", 
                   line=dict(color="#ff4444"), fillcolor="rgba(255,68,68,0.3)"),
        row=3, col=1
    )
    
    # 6. Rolling Volatility
    rolling_vol = pd.Series(returns).rolling(126).std() * np.sqrt(252)
    fig.add_trace(
        go.Scatter(x=dates, y=rolling_vol, name="Rolling Vol", line=dict(color="#ff7f0e")),
        row=3, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=900,
        showlegend=False,
        template="plotly_dark",
        title_text="Returns Tear Sheet",
        title_x=0.5,
    )
    
    html = fig.to_html(include_plotlyjs="cdn")
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(html)
        logger.info(f"Returns tear sheet saved to {output_path}")
    
    return html


def generate_factor_tear_sheet(
    factor_data: pd.DataFrame,
    factor_column: str,
    returns_column: str = "forward_return_21d",
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate a factor analysis tear sheet.
    
    Args:
        factor_data: DataFrame with factor values and forward returns
        factor_column: Name of the factor column
        returns_column: Name of the forward returns column
        output_path: Path to save HTML file
        
    Returns:
        HTML string of the tear sheet
    """
    if not PLOTLY_AVAILABLE:
        return "<p>Plotly not available for tear sheet generation</p>"
    
    # Create figure
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Factor vs Forward Returns",
            "Quintile Returns",
            "Factor Distribution",
            "IC Time Series",
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
    )
    
    # 1. Scatter plot of factor vs returns
    fig.add_trace(
        go.Scatter(
            x=factor_data[factor_column],
            y=factor_data[returns_column],
            mode="markers",
            marker=dict(size=3, opacity=0.5, color="#1f77b4"),
            name="Factor vs Returns",
        ),
        row=1, col=1
    )
    
    # 2. Quintile returns
    factor_data["quintile"] = pd.qcut(factor_data[factor_column], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    quintile_returns = factor_data.groupby("quintile")[returns_column].mean()
    
    colors = ["#ff4444", "#ff8844", "#ffff44", "#88ff44", "#00ff88"]
    fig.add_trace(
        go.Bar(
            x=quintile_returns.index.astype(str),
            y=quintile_returns.values,
            marker_color=colors,
            name="Quintile Returns",
        ),
        row=1, col=2
    )
    
    # 3. Factor distribution
    fig.add_trace(
        go.Histogram(x=factor_data[factor_column], nbinsx=50, marker_color="#1f77b4", name="Factor"),
        row=2, col=1
    )
    
    # 4. IC time series (Information Coefficient)
    if "date" in factor_data.columns:
        ic_series = factor_data.groupby("date").apply(
            lambda x: x[factor_column].corr(x[returns_column])
        )
        fig.add_trace(
            go.Scatter(x=ic_series.index, y=ic_series.values, name="IC", line=dict(color="#00ff88")),
            row=2, col=2
        )
    
    # Update layout
    fig.update_layout(
        height=700,
        showlegend=False,
        template="plotly_dark",
        title_text=f"Factor Tear Sheet: {factor_column}",
        title_x=0.5,
    )
    
    html = fig.to_html(include_plotlyjs="cdn")
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(html)
        logger.info(f"Factor tear sheet saved to {output_path}")
    
    return html


def generate_transactions_tear_sheet(
    transactions: pd.DataFrame,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate a transactions analysis tear sheet.
    
    Args:
        transactions: DataFrame with transaction data
        output_path: Path to save HTML file
        
    Returns:
        HTML string of the tear sheet
    """
    if not PLOTLY_AVAILABLE:
        return "<p>Plotly not available for tear sheet generation</p>"
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Daily Transaction Count",
            "Transaction Value Distribution",
            "Cumulative Turnover",
            "Position Changes Over Time",
        ),
    )
    
    # Placeholder visualizations
    fig.update_layout(
        height=600,
        template="plotly_dark",
        title_text="Transactions Tear Sheet",
        title_x=0.5,
    )
    
    html = fig.to_html(include_plotlyjs="cdn")
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(html)
    
    return html


def generate_all_tear_sheets(
    performance: pd.DataFrame,
    output_dir: Path,
    factor_data: Optional[pd.DataFrame] = None,
    factor_column: Optional[str] = None,
) -> Dict[str, Path]:
    """
    Generate all tear sheets and save to output directory.
    
    Args:
        performance: Performance DataFrame
        output_dir: Directory to save tear sheets
        factor_data: Optional factor DataFrame
        factor_column: Optional factor column name
        
    Returns:
        Dictionary of tear sheet names to file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    paths = {}
    
    # Returns tear sheet
    returns_path = output_dir / "returns_tear_sheet.html"
    generate_returns_tear_sheet(performance, output_path=returns_path)
    paths["returns"] = returns_path
    
    # Factor tear sheet
    if factor_data is not None and factor_column is not None:
        factor_path = output_dir / "factor_tear_sheet.html"
        generate_factor_tear_sheet(factor_data, factor_column, output_path=factor_path)
        paths["factor"] = factor_path
    
    # Transactions tear sheet
    transactions_path = output_dir / "transactions_tear_sheet.html"
    generate_transactions_tear_sheet(pd.DataFrame(), output_path=transactions_path)
    paths["transactions"] = transactions_path
    
    logger.info(f"Generated {len(paths)} tear sheets in {output_dir}")
    
    return paths
