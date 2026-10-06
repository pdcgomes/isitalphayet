# Launch copy (draft)

Generated from `site/src/data/site.json` on 2026-10-06, so the numbers match the site. Edit freely; rerun `uv run python experiments/write_share_copy.py` after the data changes.

## Posting notes

- Upload `share/is-it-alpha-yet.mp4` natively to the main post. Put the link in the first reply: posts containing links are widely reported to reach fewer people on X.
- Before posting, paste the link into a draft to check the preview card shows the "No." image, not a blank.
- Add the alt text below to each image.
- Post when the UK and the US east coast are both awake, for example 14:00 to 16:00 UK time on a weekday.
- Afterwards, quote or reply to new viral bot claims with the tracker's result, one at a time. Never buy engagement or use extra accounts.

## Main post (pick one), with the video

### Option 1 (deadpan, recommended)

This AI trading bot turned $1,000 into $296 million.

Backtested on real Bitcoin prices since 2017. Full code.

Watch to the end.

_(129 characters)_

### Option 2

I built the trading bot everyone keeps posting. $1,000 into $296 million on real Bitcoin prices, 80% win rate, Sharpe 3.23.

Here's the code, and what it's hiding.

_(163 characters)_

### Option 3

Every viral trading bot works the same way. We built one that turns $1,000 into $296 million, then switched off its four cheats one at a time.

_(142 characters)_

## First reply, with the link

Every number in that video is real: our code produced it. It also cheats four ways: it peeks at tomorrow, pretends trading is free, was picked after the fact, and got lucky. Switch them off and it barely matches just holding Bitcoin.

Code, data, method: isitalphayet.com

_(278 characters)_

## Thread, one image each

### 1. `share/thread-1-how-the-number-was-made.png`

Cheat 1: it peeks. It traded at each morning's price using that evening's close. Without the peek, $296M becomes $84K.

Cheat 2: fantasy fees. It assumed 0.08% a trade; a UK retail account pays 0.85%. Now it's $22K. Just holding: $19K.

_(235 characters)_

Alt text: Bar chart on a log scale: $1,000 grows to $296M with every cheat on, $84K without peeking and $22K at real fees. A dashed line marks buying and holding at $19K.

### 2. `share/thread-2-fees.png`

All 13 strategies we tried, before and after real fees. The more a strategy trades, the more the exchange takes.

Grid bots, the "passive income" favourite, lost 25% to 39% a year after fees.

_(191 characters)_

Alt text: Horizontal bars of yearly growth for 13 strategies, each sliding from its result at a 0.08% fee to its result at 0.85%. Busy strategies fall furthest; grid bots and RSI rules end well below zero.

### 3. `share/thread-3-hindsight.png`

Cheat 3: hindsight. A pitch shows whichever of 13 strategies did best, which you only know afterwards.

Picked using 2017-22, then run on 2023-26: $1,000 became $2,900. Just holding made $5,055.

_(194 characters)_

Alt text: Line chart from January 2023 to September 2026: the chosen strategy ends at $2.9K and buying and holding at $5.1K.

### 4. `share/thread-4-luck.png`

Cheat 4: luck. 13 strategies that trade on coin flips ended anywhere from $996 to $16,705.

Try enough ideas and one always looks brilliant. So we wrote our rules down and counted every attempt before testing anything.

_(218 characters)_

Alt text: Thirteen thin lines for coin-flip strategies, the luckiest ending at $17K and the unluckiest at $996, against buying and holding at $19K.

### 5. `share/thread-5-ai.png`

"But mine uses AI." We gave TradingAgents (about 110,000 GitHub stars) 34 weekly calls on Bitcoin and Ether, on dates after its models' training data ended.

It got 16 right. A fair coin got 20.

_(194 characters)_

Alt text: Two rows of 34 dots: TradingAgents' calls with 16 filled for right answers, and a fair coin's flips with 20 filled.

### Closing post

Why is your feed full of this? Bot posts are paid for attention, many exchanges pay referrers a cut of your fees, and you only see the lucky winners.

We'll keep testing new claims as they go viral: isitalphayet.com

Not financial advice.

_(245 characters)_

## X Article (long form)

**Title:** The $296 million trading bot, and the four cheats behind it

Every week another post promises a bot that turns pocket money into a fortune. So we built one. On real Bitcoin prices since 2017, it turns $1,000 into $296,080,470: 298% a year, a Sharpe ratio of 3.23, an 80% win rate and a worst drop of only 19%. Every one of those numbers is real. Our code produced them. It also cheats in four ways, and switching them off one at a time is the fastest way to understand every trading-bot screenshot you will ever see.

**Cheat 1: it peeks at tomorrow.** Each day the bot decided using that day's closing price, then traded at that morning's opening price, hours before the close existed. One line of code makes it wait for information that actually existed. $296,080,470 becomes $84,465.

**Cheat 2: it pretends trading is free.** The code charged 0.08% a trade, the figure a viral "quant stack" article used. A small UK account at Kraken pays 0.85%, including slippage. At real fees, $84,465 becomes $21,616, barely ahead of simply buying Bitcoin and holding it ($19,458). Busy strategies suffer most: grid bots, often sold as passive income, lost 25% to 39% a year.

**Cheat 3: it was picked after the race was run.** We tried 13 strategies, and a pitch shows whichever did best over the whole period, which nobody could have known in advance. Choose using 2017 to 2022 only, then let it trade 2023 to September 2026, years it never saw: $1,000 became $2,900. Holding made $5,055.

**Cheat 4: luck looks like skill.** 13 strategies that trade on coin flips ended anywhere from $996 to $16,705. Test enough ideas and one always looks brilliant. That is why we wrote our rules down before testing and counted every attempt: allowing for all 13, the odds our best strategy has a real edge come out at 20%, against the 95% we required.

**"But mine uses AI."** We ran TradingAgents, an open-source "trading firm made of AI agents" with about 110,000 GitHub stars, on dates after its models' training data ended. Over 34 weekly calls on Bitcoin and Ether it was right 16 times. A fair coin managed 20. Each decision cost $0.045.

**Doing nothing is not a recommendation either.** Simply holding Bitcoin did about as well as the best strategy here over the whole period (38% a year against 40%) and better than it from 2023. But at its worst it was 83% down, and it spent 2.9 years below an earlier peak. The point is that the bots did not clearly beat even that.

**Why your feed is full of this.** Posts are paid for attention, many exchanges pay referrers a cut of the fees their sign-ups pay, and you only ever see the lucky winners.

Everything is public: the code, the pre-registration, the ledger of every run and the live forward test. We'll keep testing new claims as they go viral. 8 tested so far, 0 passed. isitalphayet.com

Education, not financial advice.

## Show HN

**Title:** Show HN: Is It Alpha Yet? Pre-registered tests of viral trading-bot claims

We kept seeing posts promising AI trading bots that turn small sums into fortunes, so we tested them properly: rules written down before any backtest ran, 13 strategy variants all counted, nine years of Bitcoin and Ether prices, real UK retail fees, out-of-sample and walk-forward checks, plus TradingAgents on dates after its models' cutoff. 8 claims tested, 0 passed. The site opens as a parody of a bot pitch and switches off its cheats one at a time; the code, ledger and data are public.
