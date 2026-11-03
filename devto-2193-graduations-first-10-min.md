# devto-2193-graduations-first-10-min

Fonte: https://dev.to/launchtape/what-2193-pumpfun-graduations-did-in-their-first-10-minutes-and-what-it-means-for-your-bot-4f70

What 2,193 pump.fun graduations did in their first 10 minutes (and what it means for your bot) - DEV Community 

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
 
- 
 
- 

- 

- 

- 

- 

- 

 Add reaction

 Like

 Unicorn

 Exploding Head

 Raised Hands

 Fire

 Jump to Comments

 Save

 Boost

 Pick as gem 

 Copy link 

 Copied to Clipboard

 Share to X

 Share to LinkedIn

 Share to Facebook

 Share to Mastodon

 Share Post via... 

 Report Abuse 

 Correction (Oct 14): an earlier version called a 40% fall from the high a "crash of 80%+". Numbers below are corrected. 

 A lot of people are building Solana trading bots with ChatGPT or Claude right now. I was one of them. The bot part turns out to be easy. Knowing whether it would actually make money is the hard part, because almost every test runs on made-up or smoothed-over data.

 So we started recording everything. Every pump.fun coin that graduates to a PumpSwap pool, every trade in its first 30 minutes, who was behind the launch, and how it ended. Here's what three days of that tape show: 2,193 graduates, October 10 to 12, 2026 (UTC). 

## 

 1. Most graduates fall hard, and fast

 Every move here is measured from the price 10 seconds after graduation, within the first 10 minutes.

- 
 38.1% touched -80% at some point (835 of 2,193).

- 
 62.9% fell 40% or more from a high (1,380). The first version of this post called this an 80% drop.

- 
 15.0% touched 2x (330), and only 5.3% touched 3x (117).

 "Graduated" sounds like a finish line. For the median coin, the lowest point in those 10 minutes was 50% below its price 10 seconds after graduation.

## 

 2. You get about two minutes

 When a big holder dumps (a single sale big enough to crater the pool), the median time was 2.2 minutes after graduation (894 coins had one). Almost half of those dumps came inside the first 2 minutes.

 If your bot polls an API every 30 seconds, sends a transaction, and waits for confirmation, a big part of that window is already gone. Test your bot's real reaction time, not just its logic.

## 

 3. The popular "bundle = rug" rule didn't hold up

 A lot of filters treat a bonding curve that fills in seconds as a bundled rug and skip it. Oct 10-12, 2,187 graduates with a launch record:

- Curve filled in under 5 seconds (1,384 coins): 38.4% touched -80% within 10 minutes.

- 
 Slower fills (803 coins): 37.6% touched -80%.

 About the same. Slower fills did fall 40% or more from a high more often (85.6% vs 50.0%), but they also touched 2x three times as often (26.3% vs 8.5%): they swing more both ways. Three days isn't enough to call it a law. It's enough to say: check your filters against the outcome you actually trade on.

## 

 4. Watch the dev wallet

 Oct 10-12, 1,913 graduates with holder data:

- Dev still holding more than 5% of supply at graduation (1,310 coins): 33.6% touched -80% (49.3% fell 40% or more from a high).

- Dev already sold down to 5% or less (603 coins): 47.4% touched -80% (81.8% fell 40% or more from a high).

 The sold-down group also touched 2x far more often (28.0% vs 7.0%), so it swings more both ways too.

## 

 What this means if you're building a bot

- 
 Paper results lie unless your fills are honest. Use the next trade's price, not the one you saw. Add fees (they're bigger than you think on small pools).

- 
 Test on what actually happened. Random-walk or candle data hides the two-minute collapse completely.

- 
 Size for the 95% that never 3x. "Sell at 3x" strategies look great until you count the coins that never get there.

- 
 Write your gaps down. If your recorder drops for a minute, mark it. Silent gaps make stats look better than they are.

## 

 Try it yourself

 There's a free 2-hour sample (every dataset, Oct 10 14:00-16:00 UTC) on Kaggle and Hugging Face . Loading it is a few lines:

 import gzip , json 
 import pandas as pd 

 def load ( path ): 
 with gzip . open ( path , " rt " ) as f : 
 return pd . DataFrame ( json . loads ( line ) for line in f ) 

 trades = load ( " gradtrades-2026-10-10-1400-1600utc.jsonl.gz " ) 
 grads = trades [ trades . type == " grad " ] 
 print ( len ( grads ), " graduations, " , ( trades . type == " trade " ). sum (), " trades " ) 

 Or pip install launchtape for a small helper that downloads and reads the files.

 The full daily data (every graduate, every day since Oct 3, plus who's behind each launch, other launchpads and Meteora pool minutes) is at launchtape.io , from $10 a month.

 Questions about how any number was measured: ask in the comments, happy to show the method.

 Create template
 
 Templates let you quickly answer FAQs or store snippets for re-use.

 Submit 
 Preview 
 Dismiss 

 Are you sure you want to hide this comment? It will become hidden in your post, but will still be visible via the comment's permalink .

 Hide child comments as well

 Confirm

 For further actions, you may consider blocking this person and/or reporting abuse 

 Launch Tape

 Follow 

 Daily Solana launch data for bot builders: every pump fun graduate's first 30 min, trade by trade. launchtape.io

- 
 
 Joined

 Oct 13, 2026 

 Your AI code reviewer isn't a second opinion. It may be the first opinion again.
 
 # codereview 
 # security 
 # ai 
 # discuss 

 Something I wanted to see on DEV.to organizations is now a reality. 🚀
 
 # discuss 
 # devto 
 # webdev 
 # programming 

 After the Knock: The night you didn't choose is still happening
 
 # devchallenge 
 # hf26challenge 
 # gamedev 
 # ai 

 We're a place where coders share, stay up-to-date and grow their careers.

 Log in

 Create account
