import yfinance as yf
import pandas as pd
from typing import List


class Tools:
    def __init__(self):
        pass

    def scan_market_ranges(self, tickers: List[str]) -> str:
        """
        Analyzes historical 6-month ranges and trends for a provided list of stock tickers.
        :param tickers: A list of stock symbols to analyze (e.g., ['AAPL', 'MSFT', 'JPM']).
        """
        if not tickers:
            return "No tickers provided for analysis."

        all_results = []

        for ticker_str in tickers:
            # Clean ticker string (remove underscores or formatting from notes)
            ticker_clean = ticker_str.replace("_", "").strip()
            try:
                data = yf.download(
                    ticker_clean, period="6mo", interval="1d", progress=False
                )

                if data.empty:
                    all_results.append(
                        {"Ticker": ticker_clean, "Status": "No Data Found"}
                    )
                    continue

                high_6mo = data["High"].max().item()
                low_6mo = data["Low"].min().item()
                latest_price = float(data["Close"].iloc[-1].item())

                if len(data["Close"]) < 30:
                    trend_status = "Insufficient Data"
                else:
                    baseline_price = float(data["Close"].iloc[-31].item())
                    if latest_price > baseline_price * 1.02:
                        trend_status = "Positive Momentum"
                    elif latest_price < baseline_price * 0.98:
                        trend_status = "Negative Momentum"
                    else:
                        trend_status = "Neutral"

                high_flag = "1" if latest_price >= high_6mo * 0.98 else "0"
                low_flag = "1" if latest_price <= low_6mo * 1.02 else "0"

                all_results.append(
                    {
                        "Ticker": ticker_clean,
                        "Price": f"{latest_price:.2f}",
                        "6M High": f"{high_6mo:.2f}",
                        "6M Low": f"{low_6mo:.2f}",
                        "Trend": trend_status,
                        "High Flag": high_flag,
                        "Low Flag": low_flag,
                        "Status": "Success",
                    }
                )

            except Exception as e:
                all_results.append(
                    {"Ticker": ticker_clean, "Status": f"Error: {str(e)}"}
                )

        df = pd.DataFrame(all_results)
        return df.to_markdown(index=False)