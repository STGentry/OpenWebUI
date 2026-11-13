from typing import List, Dict, Optional


class Tools:
    """Calculates profit and loss for a portfolio from raw transaction data."""

    def calculate_pnl(
        self,
        purchases: List[Dict],
        sells: List[Dict],
        holdings: List[Dict],
        prices: Dict[str, float],
    ) -> Dict:
        """Calculate per-ticker and total P&L.

        Args:
            purchases: List of {"symbol": str, "qty": float, "price": float}
            sells: List of {"symbol": str, "qty": float, "price": float}
            holdings: List of {"symbol": str, "qty": float} (current portfolio)
            prices: Dict of {"symbol": current_price}

        Returns:
            Dict with keys:
                - "tickers": list of per-ticker P&L dicts
                - "totals": dict with total_cost, total_proceeds, total_value, total_pnl, total_return_pct
                - "gainers": top 3 by P&L
                - "losers": bottom 3 by P&L
        """
        symbols = sorted(
            set(
                [p["symbol"] for p in purchases]
                + [s["symbol"] for s in sells]
                + [h["symbol"] for h in holdings]
            )
        )

        ticker_results = []
        for sym in symbols:
            # Purchases
            sym_purchases = [p for p in purchases if p["symbol"] == sym]
            total_shares_purchased = sum(p["qty"] for p in sym_purchases)
            total_cost = sum(p["qty"] * p["price"] for p in sym_purchases)

            # Sells
            sym_sells = [s for s in sells if s["symbol"] == sym]
            total_shares_sold = sum(s["qty"] for s in sym_sells)
            total_proceeds = sum(s["qty"] * s["price"] for s in sym_sells)

            # Holdings
            sym_holdings = [h for h in holdings if h["symbol"] == sym]
            shares_held = sum(h["qty"] for h in sym_holdings)

            # Current value
            current_price = prices.get(sym, 0.0)
            current_value = shares_held * current_price

            # P&L
            total_recovered = total_proceeds + current_value
            pnl = total_recovered - total_cost
            return_pct = (pnl / total_cost * 100) if total_cost > 0 else 0.0

            # Avg cost per share
            avg_cost = total_cost / total_shares_purchased if total_shares_purchased > 0 else 0.0

            ticker_results.append(
                {
                    "symbol": sym,
                    "shares_purchased": total_shares_purchased,
                    "total_cost": round(total_cost, 2),
                    "avg_cost": round(avg_cost, 4),
                    "shares_sold": total_shares_sold,
                    "sale_proceeds": round(total_proceeds, 2),
                    "shares_held": round(shares_held, 4),
                    "last_close": current_price,
                    "current_value": round(current_value, 2),
                    "pnl": round(pnl, 2),
                    "return_pct": round(return_pct, 2),
                }
            )

        # Sort by P&L descending
        ticker_results.sort(key=lambda x: x["pnl"], reverse=True)

        totals = {
            "total_cost": round(sum(t["total_cost"] for t in ticker_results), 2),
            "total_proceeds": round(sum(t["sale_proceeds"] for t in ticker_results), 2),
            "total_value": round(sum(t["current_value"] for t in ticker_results), 2),
        }
        totals["total_pnl"] = round(
            totals["total_proceeds"] + totals["total_value"] - totals["total_cost"], 2
        )
        totals["total_return_pct"] = (
            round(totals["total_pnl"] / totals["total_cost"] * 100, 2)
            if totals["total_cost"] > 0
            else 0.0
        )

        gainers = ticker_results[:3]
        losers = sorted(ticker_results, key=lambda x: x["pnl"])[:3]

        return {
            "tickers": ticker_results,
            "totals": totals,
            "gainers": gainers,
            "losers": losers,
        }
