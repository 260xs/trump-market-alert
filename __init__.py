"""Trump Market Alert package.

The package provides a scheduled scanner that checks legal public sources,
extracts market-related Donald Trump mentions, deduplicates them in Postgres,
and sends Telegram alerts.
"""

__all__ = ["__version__"]
__version__ = "1.0.0"
