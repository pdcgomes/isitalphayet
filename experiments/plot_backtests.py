"""Growth of 1,000 on BTC, 2017-2026: buy-and-hold against each family's selected variant.

Usage: uv run python experiments/plot_backtests.py
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from lab.data import REPO_ROOT  # noqa: E402

RESULTS = REPO_ROOT / "experiments" / "results"


def main() -> None:
    curves = pd.read_csv(RESULTS / "growth_of_1000_weekly.csv", index_col="week", parse_dates=True)
    summary = json.loads((RESULTS / "backtest_summary.json").read_text())
    selected = [f["selected"] for f in summary["families"].values()]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    for ax, fee, title in [(axes[0], "article", "At the X article's assumed fees (0.08% per trade)"),
                           (axes[1], "kraken_taker", "At Kraken's retail taker fees (0.85% per trade)")]:
        ax.plot(curves.index, curves["buy_and_hold"], color="black", linewidth=2.2, label="Buy and hold")
        for name in selected:
            ax.plot(curves.index, curves[f"{name} | {fee}"], linewidth=1.2, label=name)
        ax.set_yscale("log")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Date")
        ax.grid(alpha=0.3, which="both")
    axes[0].set_ylabel("Value of 1,000 invested (log scale)")
    axes[1].legend(loc="upper left", fontsize=8)
    fig.suptitle("Bitcoin, Aug 2017 to Sep 2026: once real fees are paid, the best strategy only matches buying and holding",
                 fontsize=12, weight="bold")
    fig.text(0.5, 0.005, "Source: Binance BTCUSDT daily and 4-hour candles; fills at next open; "
             "strategies chosen on 2017-2022 only.", ha="center", fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(RESULTS / "growth_of_1000.png", dpi=130)
    print(RESULTS / "growth_of_1000.png")


if __name__ == "__main__":
    main()
