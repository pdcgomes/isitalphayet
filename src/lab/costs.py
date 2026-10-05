"""Per-side trading costs, including slippage, as a fraction of traded notional."""

FEE_SCENARIOS = {
    "article": 0.0008,  # 5 bps fee + 3 bps slippage per side, as in the X article
    "kraken_maker": 0.0040 + 0.0005,  # Kraken Pro tier 1 maker (checked Oct 2026) + slippage
    "kraken_taker": 0.0080 + 0.0005,  # Kraken Pro tier 1 taker + slippage
}

GATE_SCENARIO = "kraken_taker"
