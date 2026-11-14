"""
ECOSG quant factor model.

This package is a hedge-fund-style multi-factor stock model -- Value,
Quality, Momentum, Growth, and Low-Volatility -- ported into ECOSG from a
standalone project so the platform can show *both* halves of its mission
side by side: the same kind of factor-driven "which stocks would a
return-focused quant fund pick" signal a hedge fund screens on, next to
ECOSG's own ESG accountability score for the same company.

factors.py, scoring.py, portfolio.py, and backtest.py started as the original
project's modules; v0.2 fixed several metric and backtest defects and adopted
better-evidenced methods (see the "v0.2 changes and sources" section of
docs/QUANT_RESEARCH.md). config.py keeps the same knobs with
portfolio-construction defaults rescaled for ECOSG's ~25-name mock universe
(see its docstring). data.py is new: the original project's data.py talked
to yfinance directly; this one is a drop-in replacement that reads the same
shape of data (fundamentals + price history) from ECOSG's own database
instead -- exactly the swap the original project's data.py docstring
describes as its intended extension point ("swap yfinance for ... by
rewriting this file alone").

See docs/QUANT_RESEARCH.md for the full methodology writeup (how hedge
funds actually do this, and how each piece of this package implements it).
"""
