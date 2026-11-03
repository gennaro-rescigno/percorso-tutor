# pumpfundata-graduation-rate

Fonte: https://pumpfundata.com/blog/pumpfun-graduation-rate-analysis

- 
- 
- 
- Pump.fun Graduation Rate: Only 0.84% of Tokens Succeed (April 2026 Data) | PumpFunData 
- 
- 
 All posts July 16, 2026

# Pump.fun Graduation Rate: Only 0.84% of Tokens Succeed
 Every day in April, about 25,000 new tokens launched on Pump.fun. By the month's end, that added up to 763,350 tokens. Only 6,379 of them graduated to the AMM, which works out to one in every 119 launches making it through. The dataset behind this analysis covers 73 million on-chain events from every hour of April 2026, and the patterns that emerge are surprisingly clean.
 Only 0.84% of Pump.fun tokens ever graduate to the AMM. 
## The graduation rate is nearly constant
 On April 9, over 40,000 tokens launched in a single day. On the quietest weekends, the number dropped to around 20,000. Through all of that, the graduation rate barely changed. It sat between 0.7% and 1.4% for the entire month, averaging 0.84%.
 What makes this striking is that doubling the supply of tokens did not change the odds. More tokens launching meant more tokens graduating, but the percentage stayed flat. The rate appears to be a property of the ecosystem itself rather than something that fluctuates with market conditions or individual token quality.
 April 2 had the highest daily rate at 1.44%. April 24 had the lowest at 0.74%. Even the extremes stayed within a narrow band.
 
## Nearly 1 in 4 token graduations were engineered
 Of the 6,379 tokens that graduated in April, 1,513 bonded in under 60 seconds. 735 of those bonded in the same block they were created, without forming any community or finding any buyers. The creator wallet filled the entire bonding curve alone, and the token hit the AMM before a single real trade happened.
 These bot-launched graduates had a median of 6 unique buyers and 8 total trades. Real graduates had 312 buyers and 853 trades. The two groups have nothing in common. Any graduated token with fewer than 20 buyers was almost certainly a bot.
 Once you remove them, only 4,866 real graduates remain out of 763,350 launches. Every number in the sections below is based on this filtered set.
 Around 24% of daily graduations are bot-driven. 
## Graduation is fast, or it does not happen
 If a token is going to graduate, it almost always happens in the first few minutes. The median organic graduate bonded in 9.8 minutes, and 62% of all organic graduates made it within 10 minutes. Push that window to one hour, and you capture 85%.
 Most organic tokens graduate within 10 minutes. After the first hour, the probability drops sharply. Only 975 tokens graduated after the one-hour mark, and just 182 took longer than a full day. The slowest graduate in the dataset took 24.5 days to bond, but tokens like that are extreme outliers in a distribution that is overwhelmingly front-loaded.
 The pattern makes intuitive sense. A token either builds enough buying momentum in its first minutes to fill the bonding curve, or interest fades and the curve stalls. This creates a narrow window for traders. By the time you have strong confirmation that graduation is likely, the bonding curve is already close to full.
 There is one more group outside this distribution. An additional 1,419 tokens bonded in April but were created before the month started, meaning they took weeks or months to finally graduate. These slow-burning tokens prove that while graduation is almost always fast, it is not exclusively fast.
 
## It costs about 281 SOL in volume to graduate a token
 The median real graduate absorbed 281 SOL in total buy volume before bonding. The middle 50% ranged from 163 SOL to 461 SOL. That is the collective cost that buyers pay to push a token through the bonding curve.
 Every graduated token has net buy inflow — buy volume consistently exceeds sell volume. On the sell side, the median graduate saw 199 SOL in sell volume before bonding, meaning significant profit-taking happens even before graduation. The median buyer-to-seller ratio was 1.57, so for every seller there were roughly 1.6 buyers. The middle 50% ranged from 1.31 to 2.17.
 Every single real graduate in the dataset had higher buy volume than sell volume before bonding. This is mechanically required since graduation needs net buy pressure, but the degree of imbalance tells you about the trading dynamic. A ratio near 1.3 means active two-sided trading with heavy profit-taking. A ratio above 2.0 means the token ran to graduation with relatively little selling resistance.
 
## Not all token types are equal
 Of the 6,379 tokens that graduated in April, 3,953 were standard launches, 1,811 were cashback tokens (since the upgrade), and 746 were mayhem mode tokens. The graduation rates across these types are not close.
 The token graduation funnel by launch type. Standard tokens graduated at the highest rate, pulling the overall average up. Cashback tokens bonded at 0.65%, below the 0.84% average despite making up a significant portion of launches. Mayhem mode tokens performed worst at 0.37%, less than half the baseline rate.
 
## What this means for traders
 The data suggests a few actionable patterns. First, if a token hasn't graduated within 10 minutes, the odds drop dramatically. Second, any graduated token with fewer than 20 unique buyers is likely bot-driven and should be treated with skepticism. Third, standard launches have meaningfully better odds than cashback or mayhem mode tokens.
 If you want to run your own analysis on this data, our API provides hourly Parquet files with every event. You can filter for bonding_complete events, join with create events by token_mint , and compute time-to-graduation, buyer counts, and volume metrics yourself.
 
## Run your own analysis
 PumpFunData has every Pump.fun event since February 2026 in hourly Parquet files. Build your own models on 73M+ events per month.
 Get an API key Read the docs
