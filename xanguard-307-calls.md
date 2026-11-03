# xanguard-307-calls

Fonte: https://xanguard.tech/blog/pumpfun-caller-win-rates/

We Analyzed 307 pump.fun Top-Trader Calls (2026) | Xanguard 

- 

- 

- 

- 

- 

- 

- 

- 

- 

- 

 We pulled every recent callout from pump.fun's top-12 weekly PnL wallets and computed what their public calls are actually worth. The result should rewire how you copy-trade: even the best callers on the platform see barely half their calls reach 2x — and the leaderboard's eye-popping averages are carried by a handful of lottery-ticket outliers, not repeatable skill you can mirror.

 This is the dataset behind Xanguard's caller track-record feature. Methodology at the bottom; the numbers first.

## The data: 307 calls, 12 whale wallets

 We took pump.fun's weekly PnL leaderboard (the wallets that made the most money trading this week), paged through each wallet's public callout history (up to 30 most recent calls each), and computed per-caller statistics: median multiplier, mean multiplier, and the share of calls that reached 2x or better. Data pulled September 2, 2026.

 Rank (weekly PnL) PnL (SOL) Calls Median call Mean call Calls that 2x+ 

 #1 13,289 30 2.51x 261.0x 63% 

 #2 6,317 3 2.26x 9.8x 67% 

 #3 5,650 30 2.84x 15.9x 60% 

 #4 5,118 30 1.90x 2.8x 47% 

 #5 4,859 2 2.23x 2.2x 50% 

 #6 4,741 30 1.67x 3.1x 40% 

 #7 4,422 30 1.89x 4.2x 43% 

 #8 4,003 30 1.71x 2.4x 43% 

 #9 3,907 17 1.87x 839.6x 47% 

 #10 3,623 3 2.19x 4.0x 67% 

 #11 3,095 30 2.30x 4.9x 63% 

 #12 2,950 30 1.76x 3.8x 40% 

## Finding 1: Even the best callers are a coin flip on any single call

 Median call multipliers across the top-12 weekly earners: 1.67x to 2.84x . Half of their calls do worse than that. The share of calls reaching 2x or better runs 40–67% — meaning the best traders on pump.fun , the wallets up thousands of SOL this week, post calls that fail to double 33–60% of the time.

 If your mental model is "whale called it, so it's going up" — the data says you're taking a slightly-better-than-coin-flip. That doesn't mean don't mirror callers. It means position sizing against the base rate is the entire game.

## Finding 2: The mean is a lie

 Look at the #1 wallet: 13,289 SOL in weekly PnL, and a mean call multiplier of 261x. The median call: 2.51x. The gap is the story — one or two absurd outliers (a 100x, a 1000x) drag the average to a number no follower will ever experience. Wallet #9 is the extreme case: 839.6x mean against a 1.87x median.

 Leaderboards rank on total PnL. Total PnL is made of outliers. A caller's leaderboard position tells you they got lucky at least once. Their median call tells you what happens if you copy the next one. These are not the same number, and the difference is where followers get farmed.

## Finding 3: Profitable wallet ≠ profitable caller

 PnL measures what they made trading. Callouts measure what they told the public to buy. In other weeks, a top-PnL wallet can have median public calls below 1x — actively losing money for everyone who mirrored them while their own PnL printed. This week's crop is healthier, but the structural warning stands: the wallet's trading skill and the wallet's public calls are different products, and only one of them is sold to you.

## What to do with this

- Judge callers on median and win rate, never the leaderboard rank. A 60%+ rate at 2x+ with a 2.5x median is a mirroring candidate. A 43% rate with a fat mean is a lottery ticket seller.

- Size for the base rate. If even elite callers 2x half the time, full-port apes are a donation. The Kelly-flavored version: small, repeatable, survivable entries.

- Speed still matters most. The callers who do print are front-run by their own followers within seconds — the entry you get depends on how fast you see the call, not just who's calling.

## The tooling answer

 Doing this analysis by hand means paging through callout histories and multiplying. We built it into the alert itself: every Xanguard callout alert carries the caller's win rate, median multiple, call count, and follower count — computed from their full callout history, refreshed continuously. You see whether the caller is worth mirroring in the same message that tells you what they called. Example alert (fictional caller and token):

 📢 NEW CALLOUT · $SOLCAT 

👤 example_caller called at $14.6K · token 47m old

💰 Holding 8.4M (0.84%) · $126.99 cost basis

🏆 his calls 2x+ 61% of the time (23 calls) · 12.4K followers

🪙 Curve 12.4 SOL · ATH $18.2K · bonding

 Milestone alerts (2x/5x/10x with time-to-hit) track the call after entry. Plans from $100/month, SOL, 60-second setup in @PF_Xanguard_bot with /call . Bots get the same data over WebSocket — details on the pump.fun callout alerts page .

## Methodology

 Source: pump.fun weekly PnL leaderboard (top 12 wallets by PnL, week ending 2026-09-02) and each wallet's public callout history via pump.fun's own API (up to 30 most recent callouts per wallet, 307 calls total; wallets with fewer than 30 lifetime calls analyzed as-is). Multiplier = the callout's maximum observed multiple (maxMultiplier). Win rate = share of calls with maxMultiplier ≥ 2.0. Small-sample wallets (#2, #5, #10) are marked by their call counts. This is a point-in-time snapshot — caller performance drifts week to week, which is exactly why the track record belongs inside the alert, recomputed continuously.

## Frequently Asked Questions

 What is a good win rate for a pump.fun caller?

 Based on our September 2026 analysis of 307 recent callouts from pump.fun's top-12 weekly PnL wallets, even the best callers see only 40–67% of their calls reach 2x. A caller above 60% win rate at 2x+ is elite; most profitable wallets sit at 40–50%.

 Are pump.fun leaderboard wallets good callers to copy?

 Not automatically. Our data shows the top weekly PnL wallets have median call multipliers of just 1.67x–2.84x — roughly a coin flip on any single call. Their leaderboard positions are built on rare outlier calls (mean multipliers run 2.4x–261x above their medians), not consistent calls.

 How do I check a pump.fun caller's win rate?

 Manually you'd page through their callout history on pump.fun and compute the multiples yourself. Xanguard's callout alerts include the caller's win rate, median multiple, and call count in every alert automatically — open @PF_Xanguard_bot and use /call with the caller's wallet.

 What is the median call multiplier for top pump.fun callers?

 In our dataset of pump.fun's top-12 weekly PnL wallets, median call multipliers ranged from 1.67x to 2.84x (September 2026, 307 calls analyzed). The

 ← Back to Blog 

### Related Articles

 Pump.fun Callout Alerts: Track Any Caller (2026) 
 Real-time pump.fun callout alerts: entry mcap, position, cost basis, thesis and win rate, plus 2x/5x/10x pings. Telegram...

 Best Pump.fun Alert Bots (2026): 4 Types Compared 
 Pump.fun alert bots compared: callouts with win rate, launches, livestreams and graduations. Telegram, API or WebSocket....

 Pump.fun Graduation Threshold Explained (2026) 
 A pump.fun token graduates when its bonding curve fills, at roughly $69K market cap, and moves to PumpSwap. What happens...

## See every caller's win rate in real time

 Get Telegram notifications for new tweets from any X account, in a median of ~200 ms on paid plans. Free for 1 account. Paid plans from $19 a month for 10 accounts.

 Start Free
 
 View Features
