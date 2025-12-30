"""
QS Research - Research Layer Module

QS Research provides the research and backtesting framework for the
Quant Hedge Fund system. It includes:

- Factor calculations (momentum, value, quality)
- Preprocessing pipelines
- Backtesting engine with Zipline integration
- Strategy templates
- MLflow experiment tracking
"""

from qsresearch.backtest.run_backtest import run_backtest

__all__ = ["run_backtest"]
