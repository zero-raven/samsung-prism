"""
FinSight Skill 4 — Portfolio Impact Mapping
=============================================
Maps causal chain impacts to user's specific holdings.

═══════════════════════════════════════════════════════
INPUT:
    - data/portfolio/holdings.yaml          → User's portfolio
    - data/analysis/chain_<event_id>.yaml   → Causal chains from Skill 3

OUTPUT:
    - data/analysis/impact_<event_id>.yaml  → Portfolio-specific impact report
    - data/logs/portfolio.log               → Processing log

TRIGGERS:
    - After Skill 3 (finsight-hypothesize) writes analysis
    - Portfolio commands from Telegram (add/remove/show)
    - Can be run manually: python portfolio.py
═══════════════════════════════════════════════════════
"""

import sys
import os
import glob
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config_loader import (
    load_config, get_workspace_path, read_yaml, write_yaml, append_to_log
)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════
# PORTFOLIO MANAGEMENT
# ═══════════════════════════════════════════════════════════

def get_portfolio_path() -> str:
    return get_workspace_path("portfolio", "holdings.yaml")


def load_portfolio() -> list:
    """
    Load user's portfolio holdings.

    OUTPUT: list of holding dicts [{ticker, name, sector, quantity, avg_cost}]
    """
    path = get_portfolio_path()
    data = read_yaml(path)

    if not data or not data.get("holdings"):
        # Initialize from config defaults
        config = load_config()
        defaults = config.get("portfolio", {}).get("default_holdings", [])
        if defaults:
            write_yaml(path, {"holdings": defaults, "last_updated": datetime.datetime.now().isoformat()})
            return defaults
        return []

    return data.get("holdings", [])


def save_portfolio(holdings: list):
    """Save portfolio holdings to YAML."""
    write_yaml(get_portfolio_path(), {
        "holdings": holdings,
        "last_updated": datetime.datetime.now().isoformat(),
    })


def add_holding(ticker: str, name: str, sector: str, quantity: int, avg_cost: float):
    """
    Add or update a holding in the portfolio.

    INPUT: ticker, name, sector, quantity, avg_cost
    OUTPUT: Updated holdings.yaml
    """
    holdings = load_portfolio()

    # Check if ticker already exists
    for h in holdings:
        if h["ticker"] == ticker:
            h["quantity"] = quantity
            h["avg_cost"] = avg_cost
            h["name"] = name
            h["sector"] = sector
            save_portfolio(holdings)
            return f"Updated {ticker}: {quantity} shares @ ₹{avg_cost}"

    holdings.append({
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "quantity": quantity,
        "avg_cost": avg_cost,
    })
    save_portfolio(holdings)
    return f"Added {ticker}: {quantity} shares @ ₹{avg_cost}"


def remove_holding(ticker: str) -> str:
    """
    Remove a holding from the portfolio.

    INPUT: ticker symbol
    OUTPUT: Confirmation message
    """
    holdings = load_portfolio()
    original_count = len(holdings)
    holdings = [h for h in holdings if h["ticker"] != ticker]

    if len(holdings) == original_count:
        return f"Ticker {ticker} not found in portfolio."

    save_portfolio(holdings)
    return f"Removed {ticker} from portfolio."


def get_current_prices(tickers: list) -> dict:
    """
    Fetch current prices for a list of NSE tickers via yfinance.

    INPUT:  list of ticker symbols (e.g., ["RELIANCE.NS", "TCS.NS"])
    OUTPUT: dict mapping ticker → current_price
    """
    prices = {}
    if not YFINANCE_AVAILABLE:
        return prices

    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="2d")
            if not hist.empty:
                prices[ticker_symbol] = round(float(hist.iloc[-1]["Close"]), 2)
        except Exception:
            pass

    return prices


# ═══════════════════════════════════════════════════════════
# IMPACT MAPPING
# ═══════════════════════════════════════════════════════════

def map_portfolio_impact(chain_analysis: dict) -> dict:
    """
    Map a causal chain analysis to the user's portfolio.

    INPUT:
        chain_analysis — dict from Skill 3 with keys: event_id, causal_chain
            causal_chain.affected_sectors: [{sector, direction, magnitude}]

    OUTPUT:
        dict — Portfolio impact report with exposure scores

    STEPS:
        1. Load portfolio holdings
        2. Get current prices
        3. Calculate total portfolio value
        4. Find holdings in affected sectors
        5. Calculate exposure score
    """
    event_id = chain_analysis.get("event_id", "unknown")
    causal_chain = chain_analysis.get("causal_chain", {})
    affected_sectors = causal_chain.get("affected_sectors", [])

    # Step 1: Load portfolio
    holdings = load_portfolio()
    if not holdings:
        return {
            "event_id": event_id,
            "error": "No portfolio holdings found.",
            "portfolio_exposure": {"total_portfolio_value": 0, "affected_value": 0, "exposure_pct": 0},
        }

    # Step 2: Get current prices
    tickers = [h["ticker"] for h in holdings]
    current_prices = get_current_prices(tickers)

    # Step 3: Calculate portfolio values
    total_value = 0
    for h in holdings:
        price = current_prices.get(h["ticker"], h.get("avg_cost", 0))
        h["_current_price"] = price
        h["_value"] = price * h.get("quantity", 0)
        total_value += h["_value"]

    # Step 4: Map affected sectors
    affected_sector_names = {s.get("sector", "").lower() for s in affected_sectors}
    sector_impact_map = {}
    for s in affected_sectors:
        sector_impact_map[s.get("sector", "").lower()] = {
            "direction": s.get("direction", "neutral"),
            "magnitude": s.get("magnitude", "low"),
            "reasoning": s.get("reasoning", ""),
        }

    affected_holdings = []
    affected_value = 0

    for h in holdings:
        holding_sector = h.get("sector", "").lower()
        if holding_sector in affected_sector_names:
            impact = sector_impact_map.get(holding_sector, {})
            holding_value = h["_value"]
            affected_value += holding_value

            affected_holdings.append({
                "ticker": h["ticker"],
                "name": h.get("name", h["ticker"]),
                "sector": h.get("sector"),
                "current_price": h["_current_price"],
                "quantity": h.get("quantity", 0),
                "holding_value": round(holding_value, 2),
                "pct_of_portfolio": round((holding_value / total_value * 100) if total_value > 0 else 0, 2),
                "impact_direction": impact.get("direction", "neutral"),
                "impact_magnitude": impact.get("magnitude", "low"),
                "impact_reasoning": impact.get("reasoning", ""),
            })

    # Step 5: Build report
    exposure_pct = round((affected_value / total_value * 100) if total_value > 0 else 0, 2)

    # Determine overall direction
    directions = [ah["impact_direction"] for ah in affected_holdings]
    if all(d == "positive" for d in directions):
        overall_direction = "positive"
    elif all(d == "negative" for d in directions):
        overall_direction = "negative"
    elif directions:
        overall_direction = "mixed"
    else:
        overall_direction = "neutral"

    impact_report = {
        "event_id": event_id,
        "event_summary": chain_analysis.get("event_summary", ""),
        "portfolio_exposure": {
            "total_portfolio_value": round(total_value, 2),
            "affected_value": round(affected_value, 2),
            "exposure_pct": exposure_pct,
            "direction": overall_direction,
        },
        "affected_holdings": affected_holdings,
        "unaffected_holdings_count": len(holdings) - len(affected_holdings),
        "mapped_at": datetime.datetime.now().isoformat(),
    }

    return impact_report


def show_portfolio() -> str:
    """
    Generate a formatted portfolio summary string.

    OUTPUT: str — Human-readable portfolio summary with current prices
    """
    holdings = load_portfolio()
    if not holdings:
        return "📊 Portfolio is empty. Use /portfolio add to add holdings."

    tickers = [h["ticker"] for h in holdings]
    prices = get_current_prices(tickers)

    lines = ["📊 *Your Portfolio*\n"]
    total_value = 0
    total_invested = 0

    for h in holdings:
        price = prices.get(h["ticker"], h.get("avg_cost", 0))
        value = price * h.get("quantity", 0)
        invested = h.get("avg_cost", 0) * h.get("quantity", 0)
        pnl = value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0

        emoji = "🟢" if pnl >= 0 else "🔴"
        lines.append(
            f"{emoji} *{h.get('name', h['ticker'])}* ({h['ticker']})\n"
            f"   {h.get('quantity', 0)} shares | ₹{price:,.2f} | "
            f"P&L: {'+' if pnl >= 0 else ''}₹{pnl:,.2f} ({pnl_pct:+.1f}%)"
        )
        total_value += value
        total_invested += invested

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    lines.append(f"\n💰 *Total*: ₹{total_value:,.2f} | P&L: {'+' if total_pnl >= 0 else ''}₹{total_pnl:,.2f} ({total_pnl_pct:+.1f}%)")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════

def run_portfolio_mapping():
    """
    Process all unprocessed causal chains and map to portfolio.

    STEP 1: Find chain analysis files without matching impact files
    STEP 2: For each, run portfolio impact mapping
    STEP 3: Write impact reports
    """
    print("=" * 60)
    print("[Skill 4] FinSight Portfolio Impact Mapping Starting...")
    print("=" * 60)

    analysis_dir = get_workspace_path("analysis")
    chain_files = sorted(glob.glob(os.path.join(analysis_dir, "chain_evt_*.yaml")))

    if not chain_files:
        print("[Skill 4] No causal chains to process.")
        return []

    unprocessed = []
    for cf in chain_files:
        basename = os.path.basename(cf)
        event_id = basename.replace("chain_", "").replace(".yaml", "")
        impact_path = os.path.join(analysis_dir, f"impact_{event_id}.yaml")
        if not os.path.exists(impact_path):
            unprocessed.append(cf)

    if not unprocessed:
        print("[Skill 4] All chains already mapped to portfolio.")
        return []

    print(f"[Skill 4] Processing {len(unprocessed)} causal chains...")
    reports = []

    for cf in unprocessed:
        chain = read_yaml(cf)
        event_id = chain.get("event_id", "unknown")
        print(f"\n[Skill 4] Mapping: {chain.get('event_summary', 'Unknown')[:60]}...")

        report = map_portfolio_impact(chain)
        impact_path = get_workspace_path("analysis", f"impact_{event_id}.yaml")
        write_yaml(impact_path, report)
        reports.append(report)

        exposure = report.get("portfolio_exposure", {})
        print(f"  → Exposure: {exposure.get('exposure_pct', 0)}% ({exposure.get('direction', 'neutral')})")
        print(f"  → Affected holdings: {len(report.get('affected_holdings', []))}")

    print(f"\n[Skill 4] Done. Mapped {len(reports)} events to portfolio.")
    return reports


if __name__ == "__main__":
    from shared.config_loader import ensure_workspace
    ensure_workspace()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true", help="Show current portfolio")
    parser.add_argument("--add", nargs=5, metavar=("TICKER", "NAME", "SECTOR", "QTY", "COST"),
                        help="Add a holding")
    parser.add_argument("--remove", help="Remove a holding by ticker")
    args = parser.parse_args()

    if args.show:
        print(show_portfolio())
    elif args.add:
        ticker, name, sector, qty, cost = args.add
        print(add_holding(f"{ticker}.NS", name, sector, int(qty), float(cost)))
    elif args.remove:
        print(remove_holding(args.remove))
    else:
        run_portfolio_mapping()
