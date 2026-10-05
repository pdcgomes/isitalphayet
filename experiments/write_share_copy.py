"""Draft the launch posts from the site data, so every number matches the evidence. Edit the output freely.

Usage: uv run python experiments/write_share_copy.py   # writes share/copy.md
"""

from __future__ import annotations

import json
import re

from lab.data import REPO_ROOT

SITE_DATA = REPO_ROOT / "site" / "src" / "data" / "site.json"
OUT = REPO_ROOT / "share" / "copy.md"
HOST = "isitalphayet.com"
X_LIMIT = 280
X_URL_LENGTH = 23  # X counts every link as 23 characters


def money(v: float) -> str:
    return f"${v:,.0f}"


def short(v: float) -> str:
    for size, unit in ((1e6, "M"), (1e3, "K")):
        if v >= size:
            x = v / size
            return f"${x:.0f}{unit}" if x >= 10 else f"${x:.1f}{unit}".replace(".0", "")
    return money(v)


def pct(x: float, digits: int = 0) -> str:
    return f"{x * 100:.{digits}f}%"


def a_or_an(number_text: str) -> str:
    """'an 80%' and 'an 11%', but 'a 75%'."""
    return "an" if number_text.startswith("8") or number_text.startswith(("11", "18")) else "a"


def x_length(text: str) -> int:
    return len(re.sub(r"\S+\.(com|app|org)\S*", "x" * X_URL_LENGTH, text))


def post(text: str) -> str:
    n = x_length(text)
    if n > X_LIMIT:
        raise ValueError(f"Post is {n} characters, over X's {X_LIMIT}:\n{text}")
    return f"{text}\n\n_({n} characters)_"


def main() -> None:
    d = json.loads(SITE_DATA.read_text())
    s, meta = d["story"], d["meta"]
    cheats, no_peek, real_fees = s["steps"]
    bh, hs, luck, ai, fees = s["buy_and_hold"], s["hindsight"], s["luck"], s["ai"], s["fees"]["scenarios"]
    finals = [r["final_value"] for r in luck["random"]]
    grid = next(c for c in d["claims"] if c["slug"] == "grid-bots")["families"][0]
    grid_taker = [v["cagr"]["kraken_taker"] for v in grid["variants"]]
    stars = round(s["sources"]["tradingagents_stars"] / 1000) * 1000
    coin_right = sum(ai["coin_flips"])

    main_post = [
        f"This AI trading bot turned $1,000 into ${cheats['final_value'] / 1e6:.0f} million.\n\nBacktested on real Bitcoin prices since {s['since'][:4]}. Full code.\n\nWatch to the end.",
        f"I built the trading bot everyone keeps posting. $1,000 into ${cheats['final_value'] / 1e6:.0f} million on real Bitcoin prices, {pct(cheats['win_rate'])} win rate, Sharpe {cheats['sharpe']:.2f}.\n\nHere's the code, and what it's hiding.",
        f"Every viral trading bot works the same way. We built one that turns $1,000 into ${cheats['final_value'] / 1e6:.0f} million, then switched off its four cheats one at a time.",
    ]
    reply = (
        f"Every number in that video is real: our code produced it. It also cheats four ways: it peeks at tomorrow, "
        f"pretends trading is free, was picked after the fact, and got lucky. Switch them off and it barely matches just "
        f"holding Bitcoin.\n\nCode, data, method: {HOST}"
    )
    thread = [
        ("thread-1-how-the-number-was-made.png",
         f"Cheat 1: it peeks. It traded at each morning's price using that evening's close. Without the peek, "
         f"{short(cheats['final_value'])} becomes {short(no_peek['final_value'])}.\n\nCheat 2: fantasy fees. It assumed "
         f"{pct(fees['article'], 2)} a trade; a UK retail account pays {pct(fees['kraken_taker'], 2)}. Now it's "
         f"{short(real_fees['final_value'])}. Just holding: {short(bh['final_value'])}.",
         f"Bar chart on a log scale: $1,000 grows to {short(cheats['final_value'])} with every cheat on, "
         f"{short(no_peek['final_value'])} without peeking and {short(real_fees['final_value'])} at real fees. "
         f"A dashed line marks buying and holding at {short(bh['final_value'])}."),
        ("thread-2-fees.png",
         f"All 13 strategies we tried, before and after real fees. The more a strategy trades, the more the exchange "
         f"takes.\n\nGrid bots, the \"passive income\" favourite, lost {pct(-max(grid_taker))} to {pct(-min(grid_taker))} "
         f"a year after fees.",
         "Horizontal bars of yearly growth for 13 strategies, each sliding from its result at a 0.08% fee to its result "
         "at 0.85%. Busy strategies fall furthest; grid bots and RSI rules end well below zero."),
        ("thread-3-hindsight.png",
         f"Cheat 3: hindsight. A pitch shows whichever of 13 strategies did best, which you only know afterwards.\n\n"
         f"Picked using 2017-22, then run on 2023-26: $1,000 became {money(hs['strategy_final_value'])}. Just holding "
         f"made {money(hs['buy_and_hold_final_value'])}.",
         f"Line chart from January 2023 to September 2026: the chosen strategy ends at {short(hs['strategy_final_value'])} "
         f"and buying and holding at {short(hs['buy_and_hold_final_value'])}."),
        ("thread-4-luck.png",
         f"Cheat 4: luck. {len(finals)} strategies that trade on coin flips ended anywhere from {money(min(finals))} to "
         f"{money(max(finals))}.\n\nTry enough ideas and one always looks brilliant. So we wrote our rules down and "
         f"counted every attempt before testing anything.",
         f"Thirteen thin lines for coin-flip strategies, the luckiest ending at {short(max(finals))} and the unluckiest at "
         f"{short(min(finals))}, against buying and holding at {short(bh['final_value'])}."),
        ("thread-5-ai.png",
         f"\"But mine uses AI.\" We gave TradingAgents (about {stars:,} GitHub stars) {ai['calls']} weekly calls on Bitcoin "
         f"and Ether, on dates after its models' training data ended.\n\nIt got {ai['hits']} right. A fair coin got "
         f"{coin_right}.",
         f"Two rows of {ai['calls']} dots: TradingAgents' calls with {ai['hits']} filled for right answers, and a fair "
         f"coin's flips with {coin_right} filled."),
    ]
    closer = (
        f"Why is your feed full of this? Bot posts are paid for attention, many exchanges pay referrers a cut of your fees, "
        f"and you only see the lucky winners.\n\nWe'll keep testing new claims as they go viral: {HOST}\n\nNot financial "
        f"advice."
    )

    lines = [
        "# Launch copy (draft)",
        "",
        f"Generated from `site/src/data/site.json` on {d['generated_at'][:10]}, so the numbers match the site. "
        "Edit freely; rerun `uv run python experiments/write_share_copy.py` after the data changes.",
        "",
        "## Posting notes",
        "",
        "- Upload `share/is-it-alpha-yet.mp4` natively to the main post. Put the link in the first reply: posts "
        "containing links are widely reported to reach fewer people on X.",
        "- Before posting, paste the link into a draft to check the preview card shows the \"No.\" image, not a blank.",
        "- Add the alt text below to each image.",
        "- Post when the UK and the US east coast are both awake, for example 14:00 to 16:00 UK time on a weekday.",
        "- Afterwards, quote or reply to new viral bot claims with the tracker's result, one at a time. "
        "Never buy engagement or use extra accounts.",
        "",
        "## Main post (pick one), with the video",
        "",
    ]
    for i, text in enumerate(main_post, 1):
        lines += [f"### Option {i}{' (deadpan, recommended)' if i == 1 else ''}", "", post(text), ""]
    lines += ["## First reply, with the link", "", post(reply), "", "## Thread, one image each", ""]
    for i, (image, text, alt) in enumerate(thread, 1):
        lines += [f"### {i}. `share/{image}`", "", post(text), "", f"Alt text: {alt}", ""]
    lines += ["### Closing post", "", post(closer), ""]

    lines += [
        "## X Article (long form)",
        "",
        f"**Title:** The ${cheats['final_value'] / 1e6:.0f} million trading bot, and the four cheats behind it",
        "",
        f"Every week another post promises a bot that turns pocket money into a fortune. So we built one. On real Bitcoin "
        f"prices since {s['since'][:4]}, it turns $1,000 into {money(cheats['final_value'])}: {pct(cheats['cagr'])} a "
        f"year, a Sharpe ratio of {cheats['sharpe']:.2f}, {a_or_an(pct(cheats['win_rate']))} {pct(cheats['win_rate'])} "
        f"win rate and a worst drop of only "
        f"{pct(-cheats['max_drawdown'])}. Every one of those numbers is real. Our code produced them. It also cheats in "
        "four ways, and switching them off one at a time is the fastest way to understand every trading-bot screenshot "
        "you will ever see.",
        "",
        "**Cheat 1: it peeks at tomorrow.** Each day the bot decided using that day's closing price, then traded at that "
        "morning's opening price, hours before the close existed. One line of code makes it wait for information that "
        f"actually existed. {money(cheats['final_value'])} becomes {money(no_peek['final_value'])}.",
        "",
        f"**Cheat 2: it pretends trading is free.** The code charged {pct(fees['article'], 2)} a trade, the figure a viral "
        f"\"quant stack\" article used. A small UK account at Kraken pays {pct(fees['kraken_taker'], 2)}, including "
        f"slippage. At real fees, {money(no_peek['final_value'])} becomes {money(real_fees['final_value'])}, barely ahead "
        f"of simply buying Bitcoin and holding it ({money(bh['final_value'])}). Busy strategies suffer most: grid bots, "
        f"often sold as passive income, lost {pct(-max(grid_taker))} to {pct(-min(grid_taker))} a year.",
        "",
        "**Cheat 3: it was picked after the race was run.** We tried 13 strategies, and a pitch shows whichever did best "
        "over the whole period, which nobody could have known in advance. Choose using 2017 to 2022 only, then let it "
        f"trade 2023 to September 2026, years it never saw: $1,000 became {money(hs['strategy_final_value'])}. Holding made "
        f"{money(hs['buy_and_hold_final_value'])}.",
        "",
        f"**Cheat 4: luck looks like skill.** {len(finals)} strategies that trade on coin flips ended anywhere from "
        f"{money(min(finals))} to {money(max(finals))}. Test enough ideas and one always looks brilliant. That is why we "
        f"wrote our rules down before testing and counted every attempt: allowing for all {luck['trials']}, the odds our "
        f"best strategy has a real edge come out at {pct(luck['deflated_sharpe'])}, against the 95% we required.",
        "",
        f"**\"But mine uses AI.\"** We ran TradingAgents, an open-source \"trading firm made of AI agents\" with about "
        f"{stars:,} GitHub stars, on dates after its models' training data ended. Over {ai['calls']} weekly calls on "
        f"Bitcoin and Ether it was right {ai['hits']} times. A fair coin managed {coin_right}. Each decision cost "
        f"${ai['usd_per_decision']:.3f}.",
        "",
        "**Doing nothing is not a recommendation either.** Simply holding Bitcoin did about as well as the best strategy "
        f"here over the whole period ({pct(bh['cagr'])} a year against {pct(real_fees['cagr'])}) and better than it from "
        f"2023. But at its worst it was {pct(-bh['max_drawdown'])} down, and it spent "
        f"{bh['longest_drawdown_days'] / 365:.1f} years below an earlier peak. The point is that the bots did not "
        "clearly beat even that.",
        "",
        "**Why your feed is full of this.** Posts are paid for attention, many exchanges pay referrers a cut of the fees "
        "their sign-ups pay, and you only ever see the lucky winners.",
        "",
        f"Everything is public: the code, the pre-registration, the ledger of every run and the live forward test. We'll "
        f"keep testing new claims as they go viral. {meta['claims_tested']} tested so far, {meta['claims_passed']} passed. "
        f"{HOST}",
        "",
        "Education, not financial advice.",
        "",
        "## Show HN",
        "",
        "**Title:** Show HN: Is It Alpha Yet? Pre-registered tests of viral trading-bot claims",
        "",
        f"We kept seeing posts promising AI trading bots that turn small sums into fortunes, so we tested them properly: "
        f"rules written down before any backtest ran, 13 strategy variants all counted, nine years of Bitcoin and Ether "
        f"prices, real UK retail fees, out-of-sample and walk-forward checks, plus TradingAgents on dates after its models' "
        f"cutoff. {meta['claims_tested']} claims tested, {meta['claims_passed']} passed. The site opens as a parody of a "
        f"bot pitch and switches off its cheats one at a time; the code, ledger and data are public.",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
