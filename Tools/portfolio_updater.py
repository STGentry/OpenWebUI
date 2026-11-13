import yfinance as yf
from typing import List, Dict, Optional


class Tools:
    """Fetches current/last-close stock prices and calculates portfolio values."""

    def fetch_stock_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Fetch the most recent close price for each ticker symbol.

        Args:
            tickers: A list of stock ticker symbols (e.g. ['AAPL', 'MSFT', 'JPM']).

        Returns:
            A dict mapping each ticker to its most recent close price.
            Tickers that failed to fetch will have a value of None.
        """
        results: Dict[str, Optional[float]] = {}
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                info = t.fast_info
                price = info.get("lastPrice") or info.get("previousClose")
                if price is None:
                    # Fallback: get the last row of recent history
                    hist = t.history(period="5d")
                    if not hist.empty:
                        price = float(hist["Close"].iloc[-1])
                results[ticker] = float(price) if price is not None else None
            except Exception:
                results[ticker] = None
        return results

    def calculate_portfolio_values(
        self, positions: List[Dict]
    ) -> List[Dict]:
        """Calculate last-close and total value for each portfolio position.

        Args:
            positions: A list of dicts, each with keys:
                - 'symbol' (str): ticker symbol
                - 'qty' (float): number of shares held

        Returns:
            A list of dicts with keys: 'symbol', 'qty', 'last_close', 'value'.
        """
        tickers = list({p["symbol"] for p in positions})
        prices = self.fetch_stock_prices(tickers)
        out = []
        for p in positions:
            sym = p["symbol"]
            qty = float(p["qty"])
            close = prices.get(sym)
            value = round(close * qty, 2) if close is not None else None
            out.append(
                {
                    "symbol": sym,
                    "qty": qty,
                    "last_close": close,
                    "value": value,
                }
            )
        return out
