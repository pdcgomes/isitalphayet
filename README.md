<h1 align="center">Is It Alpha Yet?</h1>

<p align="center"><strong>Viral trading-bot claims, tested honestly.</strong><br>
<a href="https://isitalphayet.com">isitalphayet.com</a></p>

<p align="center">
  <img src="docs/images/film-preview.gif" width="360" alt="The 53-second film: a bot that turned $1,000 into $296 million, then each cheat behind the number removed">
  <br><sub><a href="share/is-it-alpha-yet.mp4">The full film</a> (53 s, MP4, 4:5 for X)</sub>
</p>

As of 5 October 2026: five viral claims tested, none passed. The best strategy we tried only matched simply holding
Bitcoin after real fees, and lost to it on years it had never seen. An open-source AI trading agent called the market
right 16 times out of 34; a fair coin managed 20.

Education, not financial advice.

## The story

The site opens as one more winning-bot pitch. Every number on its dashboard is real, produced by our code from real
Bitcoin prices. Then it takes the number apart, one cheat at a time.

<p align="center"><img src="docs/images/story-1-pitch.png" width="720" alt="A parody dashboard: an AI trading bot turned $1,000 into $296,080,470"></p>

<table>
  <tr>
    <td width="50%"><img src="docs/images/story-2-peek.png" alt="Cheat 1: it peeks at tomorrow. Without the peek, $296 million becomes $84,465"><br>
      <sub><strong>It peeks at tomorrow.</strong> Trading on a price before it exists turns $84,465 into $296 million.</sub></td>
    <td width="50%"><img src="docs/images/story-3-all-fees.png" alt="All 13 strategies before and after real fees; holding made 38% a year"><br>
      <sub><strong>Fantasy fees.</strong> At a UK retail fee of 0.85% a trade, the busiest strategies give most of it to the exchange.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/images/story-4-hindsight.png" alt="Cheat 3: picked after the race was run. On unseen years $1,000 became $2,900; holding made $5,055"><br>
      <sub><strong>Picked in hindsight.</strong> Chosen on 2017 to 2022, the best strategy lost to holding on the years after.</sub></td>
    <td><img src="docs/images/story-5-luck.png" alt="Cheat 4: 13 coin-flip strategies ended anywhere from $996 to $16,705"><br>
      <sub><strong>Luck looks like skill.</strong> Thirteen coin-flip strategies, no skill at all, ended between $996 and $16,705.</sub></td>
  </tr>
</table>

<p align="center"><img src="docs/images/story-6-ai.png" width="720" alt="TradingAgents got 16 of 34 weekly calls right; a fair coin got 20"></p>

## The tracker

Every claim gets its own page with the evidence: the claim in its own words, what we tested, the four tests, every
variant and the walk-forward results. New claims are added as they spread.

<table>
  <tr>
    <td width="50%"><img src="docs/images/page-claims.png" alt="The claims tracker: 5 claims tested, 0 passed"></td>
    <td width="50%"><img src="docs/images/page-claim.png" alt="A claim page: trend and momentum signals, with the equity chart and the four tests"></td>
  </tr>
  <tr>
    <td colspan="2"><img src="docs/images/page-live.png" alt="The live test: TradingAgents' weekly calls and a paper trade on Kraken prices"><br>
      <sub><strong>The live test.</strong> Backtests can be fooled; next week can't. Weekly AI calls and a paper trade, scored as they happen.</sub></td>
  </tr>
</table>

Built for phones first, since that's where the posts are read:

<p align="center">
  <img src="docs/images/phone-pitch.png" width="230" alt="The pitch on a phone">
  <img src="docs/images/phone-all-fees.png" width="230" alt="The fees chart on a phone">
  <img src="docs/images/phone-verdict.png" width="230" alt="The verdict on a phone: No.">
</p>

## How the testing works

1. **Rules first.** [experiments/preregistration.md](experiments/preregistration.md) was written, and its SHA-256 logged
   to [experiments/trials.jsonl](experiments/trials.jsonl), before any backtest ran. Later edits are logged, not hidden.
2. **Every attempt counts.** Every run is appended to the ledger, and the deflated Sharpe ratio uses the full trial count.
3. **Real prices, real fees.** Binance BTC and ETH candles since August 2017, a fill at the next bar's open, and Kraken's
   retail fee of 0.85% a trade including slippage. The 0.08% a viral article assumed is shown for comparison.
4. **Four gates.** Beat holding on 2023 to 2026, which the strategy never saw; survive the luck test (deflated Sharpe of
   at least 0.95); make money in most six-month walk-forward periods; work unchanged on Ether.
5. **AI on unseen dates.** TradingAgents was only run on dates after its models' training data ended, plus a live
   weekly forward test.

## What's where

- `src/lab/`: data download and checks, the simulator, fee scenarios, metrics, deflated Sharpe, walk-forward and gates, the trials ledger
- `experiments/`: the pre-registration and every experiment, results in `experiments/results/`
- `experiments/tradingagents/`: the TradingAgents runner (cost tracking, $35 hard stop) and scorer
- `claims/`: one TOML file per claim on the site
- `content/site.toml`: site copy that isn't a lab output (gates, limitations, corrections, source facts)
- `paper/`: the paper trader and its append-only ledger
- `site/`: the website (Vite, React and hand-made SVG charts; every number comes from `site/src/data/site.json`)
- `share/`: the film, share images and generated launch copy
- `docs/images/`: the images in this README

## Reproduce it

Needs Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m lab.data                      # download and check nine years of candles into data/
uv run python experiments/run_backtests.py     # the pre-registered backtests and gates
uv run python experiments/hype_waterfall.py    # the viral pitch's numbers, cheat by cheat
uv run python experiments/article_audit.py     # the "$200K quant stack" article's code, as published
uv run python experiments/export_site_data.py  # everything the site shows
uv run pytest
```

TradingAgents needs your own OpenAI key in a `.env` file at the repo root (`OPENAI_API_KEY=...`, never committed). It
costs about $0.05 per decision.

```bash
cd experiments/tradingagents
curl -sSL -o ta.tar.gz https://github.com/TauricResearch/TradingAgents/archive/refs/tags/v0.6.0.tar.gz
mkdir -p vendor && tar -xzf ta.tar.gz -C vendor && rm ta.tar.gz
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python ./vendor/TradingAgents-0.6.0 python-dotenv
cd ../..
experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py grid
uv run python experiments/tradingagents/score.py
```

## Add a new claim

1. Copy a file in `claims/` and describe the claim, its source and what you will test.
2. If it needs a new test, append a dated section to the pre-registration before running anything. Then add the variants
   to `src/lab/strategies.py`. The trial count, and with it the bar for the luck test, rises automatically.
3. Run the experiment and `experiments/export_site_data.py`, check the site, and push.

## Weekly update

Every Monday until 23 November 2026:

```bash
experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py forward
uv run python paper/paper_trader.py              # daily is better, just after 00:00 UTC
uv run python experiments/tradingagents/score.py
uv run python experiments/export_site_data.py
git commit -am "Weekly update" && git push       # Vercel redeploys
```

## The site

```bash
cd site && npm install && npm run dev
```

Routes:

- `/`: the story
- `/claims` and `/claims/<slug>`: the tracker and one page per claim
- `/live`: the forward test and the paper trade
- `/method`: how we tested
- `/?film=1`: the film, playing in the browser (press Play, then screen-record)
- `/?shot=<scene>`: a single still

To render the film, share images and README images (needs Google Chrome, ffmpeg and `uv sync --group render`):

```bash
cd site && npm run build && cd ..
uv run python experiments/render_site.py film    # share/is-it-alpha-yet.mp4, frame by frame
uv run python experiments/render_site.py share   # share/og.png and the thread images
uv run python experiments/render_site.py readme  # docs/images/
uv run python experiments/write_share_copy.py    # share/copy.md, with numbers from the data
```

## Deploy on Vercel

- Import the repo, set **Root Directory** to `site`. The Vite preset supplies `npm run build` and the `dist` output.
- Environment variables:
  - `VITE_REPO_URL=https://github.com/<you>/<repo>` turns on the code links and "Suggest a claim".
  - `VITE_SITE_URL` is only needed while the site lives somewhere other than isitalphayet.com, so link previews find
    their image.
- Add `isitalphayet.com` under the project's Domains and follow the DNS instructions.

## Licence

Code under the [MIT licence](LICENSE). Text, charts and data under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
