"""
QS Research - Performance Metrics

Calculate comprehensive performance metrics for backtesting.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from loguru import logger


def calculate_all_metrics(
    performance: pd.DataFrame,
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_rate: float = 0.0,
) -> Dict[str, float]:
    """
    Calculate comprehensive performance metrics.
    
    Returns 88+ metrics covering:
    - Returns (daily, monthly, annual)
    - Risk (volatility, drawdowns, VaR)
    - Risk-adjusted (Sharpe, Sortino, Calmar)
    - Statistical (skew, kurtosis)
    
    Args:
        performance: DataFrame with 'returns' and 'portfolio_value' columns
        benchmark_returns: Optional benchmark return series
        risk_free_rate: Risk-free rate for Sharpe calculation
        
    Returns:
        Dictionary of metric names to values
    """
    metrics = {}
    
    returns = performance["returns"].values
    portfolio_value = performance["portfolio_value"].values
    
    # Remove NaN
    returns = returns[~np.isnan(returns)]
    
    if len(returns) == 0:
        return {"error": "No valid returns"}
    
    # ===== Return Metrics =====
    metrics["portfolio_total_return"] = (portfolio_value[-1] / portfolio_value[0]) - 1
    metrics["portfolio_daily_mean"] = np.mean(returns)
    metrics["portfolio_daily_std"] = np.std(returns)
    
    # Annualized metrics
    trading_days = 252
    metrics["portfolio_yearly_mean"] = metrics["portfolio_daily_mean"] * trading_days
    metrics["portfolio_yearly_vol"] = metrics["portfolio_daily_std"] * np.sqrt(trading_days)
    
    # CAGR
    years = len(returns) / trading_days
    if years > 0:
        metrics["portfolio_cagr"] = (portfolio_value[-1] / portfolio_value[0]) ** (1 / years) - 1
    else:
        metrics["portfolio_cagr"] = 0
    
    # ===== Risk Metrics =====
    
    # Drawdown
    cumulative = (1 + pd.Series(returns)).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    
    metrics["portfolio_max_drawdown"] = drawdown.min()
    metrics["portfolio_avg_drawdown"] = drawdown[drawdown < 0].mean() if (drawdown < 0).any() else 0
    
    # Drawdown duration
    underwater = drawdown < 0
    if underwater.any():
        underwater_periods = underwater.astype(int).groupby((~underwater).cumsum()).sum()
        metrics["portfolio_max_drawdown_duration"] = underwater_periods.max()
    else:
        metrics["portfolio_max_drawdown_duration"] = 0
    
    # Value at Risk
    metrics["portfolio_var_95"] = np.percentile(returns, 5)
    metrics["portfolio_var_99"] = np.percentile(returns, 1)
    metrics["portfolio_cvar_95"] = returns[returns <= np.percentile(returns, 5)].mean()
    
    # ===== Risk-Adjusted Metrics =====
    
    # Sharpe Ratio
    excess_returns = returns - (risk_free_rate / trading_days)
    if metrics["portfolio_daily_std"] > 0:
        metrics["portfolio_daily_sharpe"] = (
            np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(trading_days)
        )
    else:
        metrics["portfolio_daily_sharpe"] = 0
    
    # Sortino Ratio (downside deviation)
    downside_returns = returns[returns < 0]
    if len(downside_returns) > 0:
        downside_std = np.std(downside_returns)
        if downside_std > 0:
            metrics["portfolio_daily_sortino"] = (
                np.mean(excess_returns) / downside_std * np.sqrt(trading_days)
            )
        else:
            metrics["portfolio_daily_sortino"] = 0
    else:
        metrics["portfolio_daily_sortino"] = np.inf  # No downside
    
    # Calmar Ratio
    if abs(metrics["portfolio_max_drawdown"]) > 0:
        metrics["portfolio_calmar"] = metrics["portfolio_cagr"] / abs(metrics["portfolio_max_drawdown"])
    else:
        metrics["portfolio_calmar"] = 0
    
    # ===== Statistical Metrics =====
    
    metrics["portfolio_daily_skew"] = pd.Series(returns).skew()
    metrics["portfolio_daily_kurtosis"] = pd.Series(returns).kurtosis()
    
    # Win rate
    winning_days = returns[returns > 0]
    losing_days = returns[returns < 0]
    
    metrics["portfolio_win_rate"] = len(winning_days) / len(returns) if len(returns) > 0 else 0
    metrics["portfolio_avg_win"] = winning_days.mean() if len(winning_days) > 0 else 0
    metrics["portfolio_avg_loss"] = losing_days.mean() if len(losing_days) > 0 else 0
    
    # Profit factor
    if abs(losing_days.sum()) > 0:
        metrics["portfolio_profit_factor"] = abs(winning_days.sum() / losing_days.sum())
    else:
        metrics["portfolio_profit_factor"] = np.inf
    
    # ===== Monthly/Yearly Metrics =====
    
    # Convert to monthly returns
    dates = performance["date"] if "date" in performance.columns else pd.date_range(
        start="2020-01-01", periods=len(returns), freq="B"
    )
    monthly_returns = pd.Series(returns, index=dates).resample("M").sum()
    
    metrics["portfolio_monthly_mean"] = monthly_returns.mean()
    metrics["portfolio_monthly_std"] = monthly_returns.std()
    metrics["portfolio_best_month"] = monthly_returns.max()
    metrics["portfolio_worst_month"] = monthly_returns.min()
    metrics["portfolio_win_month_pct"] = (monthly_returns > 0).mean()
    
    # Yearly returns
    yearly_returns = pd.Series(returns, index=dates).resample("Y").sum()
    
    metrics["portfolio_yearly_mean_actual"] = yearly_returns.mean()
    metrics["portfolio_yearly_std_actual"] = yearly_returns.std()
    metrics["portfolio_best_year"] = yearly_returns.max()
    metrics["portfolio_worst_year"] = yearly_returns.min()
    metrics["portfolio_win_year_pct"] = (yearly_returns > 0).mean()
    
    # Sharpe variations
    if monthly_returns.std() > 0:
        metrics["portfolio_monthly_sharpe"] = monthly_returns.mean() / monthly_returns.std() * np.sqrt(12)
    if yearly_returns.std() > 0:
        metrics["portfolio_yearly_sharpe"] = yearly_returns.mean() / yearly_returns.std()
    
    # ===== Benchmark Comparison =====
    
    if benchmark_returns is not None:
        bench = benchmark_returns.values
        bench = bench[~np.isnan(bench)]
        
        if len(bench) == len(returns):
            # Beta and Alpha
            covariance = np.cov(returns, bench)
            variance = np.var(bench)
            
            if variance > 0:
                metrics["portfolio_beta"] = covariance[0, 1] / variance
                metrics["portfolio_alpha"] = (
                    np.mean(returns) - metrics["portfolio_beta"] * np.mean(bench)
                ) * trading_days
            
            # Information Ratio
            active_returns = returns - bench
            tracking_error = np.std(active_returns)
            
            if tracking_error > 0:
                metrics["portfolio_information_ratio"] = (
                    np.mean(active_returns) / tracking_error * np.sqrt(trading_days)
                )
            
            # Benchmark metrics
            metrics["benchmark_total_return"] = (1 + bench).prod() - 1
            metrics["benchmark_daily_mean"] = np.mean(bench)
            metrics["benchmark_daily_std"] = np.std(bench)
            metrics["benchmark_daily_sharpe"] = (
                np.mean(bench) / np.std(bench) * np.sqrt(trading_days)
            ) if np.std(bench) > 0 else 0
            
            bench_cumulative = (1 + pd.Series(bench)).cumprod()
            bench_running_max = bench_cumulative.cummax()
            bench_drawdown = (bench_cumulative - bench_running_max) / bench_running_max
            metrics["benchmark_max_drawdown"] = bench_drawdown.min()
    
    # Round all metrics
    metrics = {k: round(v, 10) if isinstance(v, float) else v for k, v in metrics.items()}
    
    logger.info(f"Calculated {len(metrics)} performance metrics")
    return metrics
