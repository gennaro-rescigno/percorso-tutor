# bitquery-snipers-bundles

Fonte: https://bitquery.io/investigations/pump-fun-snipers-bundles

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
- Pump.fun Devs' Bundles Made $579M+, Snipers Just $31.5M - Bitquery 
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
- New pricing plans, starting at $49/mo .
 Explore plans 

 On-chain investigation Solana Pump.fun 

# Pump.fun devs' bundles made $579M+, snipers just $31.5M 
 Many Pump.fun coins are already bought by the time anyone can see them on the site. We went through the 8.2 million launches we could check over 11 months to find out who those first buyers are and whether they make money.
 G By Gaurav Agarwal · Blockchain Intelligence On-chain figures verified October 10, 2026 15 min read 

 At a glance
 Pump.fun lets anyone launch a memecoin in a minute, and most new Solana tokens start there. From 30 October 2025 to 7 October 2026, someone other than the dev bought in block 0, the block that holds the first trade, on 38% of the 8.2 million new coins we could check. On 21% of all the coins those first buyers included the dev's wallets, packed into the launch bundle. On launches up to the end of June, devs and their bundled wallets made at least $579 million after fees on what they sold. Sniper bots were among the first buyers on 28% of the coins and made $31.5 million on what they sold, or $15.2 million counting what they could not.
 8.2 million
 New Pump.fun coins checked

 38%
 Bought by someone else in block 0

 $579M+
 Made by devs and their bundled wallets to the end of June

 65%
 Coins whose dev sold within a minute

 Key findings Each line has its own share link 
 
- 38%
 On 38% of new Pump.fun coins, a wallet other than the dev bought in block 0, the block that holds the coin's first trade.

- 21%
 On 21% of launches the dev's own wallets bought in block 0, packed into the launch bundle. They took a median 10% of all tokens.

- $579 million
 Devs and their bundled wallets made at least $579 million after fees on the part of their bundled coins they sold, for launches up to the end of June.

- $31.5 million
 Sniper bots made $31.5 million after fees on what they sold, and $15.2 million once unsold holdings count as worthless, for launches up to the end of June.

- 65%
 The dev's first sale came within a minute of launch on 65% of new coins.

## 01 · Two minutes on 15 June Who buys a Pump.fun coin before you can see it?

 Pump.fun is a website where anyone can launch a new crypto coin in about a minute. Open it and pick a coin that went on sale a minute ago. You might think you are early. Often you are not. Someone bought it before it even showed up on the site.

 Take a coin that went live on 15 June at 13:58 UTC. The wallet that created it bought a sliver, worth about $4. In the same instant, four other wallets bought 79% of all the tokens there were, for about $6,000.

 One launch, one bundle 15 June 2026, 13:58:17 UTC, five transactions in one Jito bundle 

 Four wallets bought 79% of the supply right behind the dev; the bundle then moved the coin to its trading pool and a fifth wallet bought there. Bundle record from the public Jito explorer. 
 That was enough to fill the coin's launch pool, so it moved straight to a regular trading pool in the same second, and a fifth wallet bought there. In the next 18 minutes, 1,138 other wallets bought in. By then the five early wallets had sold everything they had, for about $121,000 . They had put in about $11,000.

 Those five purchases were arranged before the coin went public. They sat in one package with the launch itself, and whoever sent that package held the launch transaction before anyone else could see it: the coin's creator, or someone working with them.

 Bitquery records Solana's DEX trades , so we went through the Pump.fun launches we could check in the 11 months to 7 October 2026, 8.2 million of them, and looked at who bought in the first moments of each one. From November on, most new tokens on Solana made their first trade there.

## 02 · The setup How does a Pump.fun launch work?

 A new Pump.fun coin starts with a fixed supply of a billion tokens and a price set by a formula that Pump.fun calls a bonding curve . Every purchase pushes the price up and every sale pushes it down, so the first buyers get the most for their money. Most launches are priced in SOL, Solana's own coin. When enough has been bought, the coin moves to a regular trading pool on PumpSwap , which Pump.fun calls graduating.

 Solana writes a new block of transactions about every 0.4 seconds. The block that holds a coin's first trade is its launch block, which traders call block 0. The wallet that created the coin is its dev, short for developer, and the dev usually makes the first purchase in the same transaction that creates the coin.

 Two kinds of buyer can get into block 0 next to the dev. Sniper bots are programs that watch for new coins and buy within a fraction of a second, on launches from many different devs. The other kind is the dev's own wallets. A dev who wants a big share of the supply cheaply can buy from several wallets at once, so that no single wallet looks large. Traders call this bundling, after the Jito bundle used to do it. A Jito bundle is a package of up to five transactions that the block producer runs together and in order, or not at all.

 Pump.fun runs a third buyer of its own. On launches whose dev switches on Mayhem mode , a Pump.fun trading agent buys and sells for the first 24 hours, using an extra billion tokens minted for it. We count it separately and leave it out of every share that follows.

## 03 · How often How many Pump.fun coins are sniped in block 0?

 On 38% of the new coins, someone other than the dev bought in block 0, and on 50% someone did within the first three blocks. The monthly share was highest in November, at 46%, and lowest in September, at 31%.

 Launches each month, and how many were bought in block 0 new Pump.fun coins by month; amber: someone other than the dev bought in block 0 

 New Pump.fun coins we could check, by month of their first trade. Amber: someone other than the dev bought in block 0 (Pump.fun's Mayhem agent not counted); the share is printed on each bar. October 2025 holds two days and October 2026 seven; May 2026 leaves out 7-26 May, when part of Pump.fun's trades are missing from the archive. 
 At the other end, nobody but the dev traded 24% of the launches in their first three days. Those coins were launched, traded by their own dev and left.

## 04 · Who they are Who buys first: sniper bots or the dev's own wallets?

 To tell the dev's wallets from strangers we used three tests. A block-0 buyer counts as the dev's own wallet if it bought inside the dev's launch transaction, if the dev paid its transaction fee, or if its purchase came in the four transactions straight after the launch.

 The third test does most of the work. A Jito bundle holds at most five transactions, so the four places after the launch transaction are exactly the room a bundle leaves. We checked 325 random early purchases against the public Jito record: 185 of the 186 in those four places sat in the launch's own bundle, and none of the 139 further down did.

 Where block-0 purchases sit purchases in the launch block, by position after the launch transaction 

 Purchases by wallets other than the dev in the launch block, 30 October 2025 to 7 October 2026. 90% of purchases by wallets that bought from fewer than 10 devs sat in positions 1 to 4; 69% of purchases by wallets that bought from 10 or more devs came 21 or more transactions later. 
 The chart shows the split. Wallets that bought from only a few devs crowd into the four places after the launch. Wallets that buy from many devs mostly land dozens or hundreds of transactions later, the time it takes a bot to see a new coin and react.

 Every other early buyer is a sniper bot if it bought in the first three blocks of launches by at least 10 different devs, and an unlinked early buyer if not.

 Dev bundles vs sniper bots share of new coins with each kind of buyer in block 0, by month 

 Share of new coins we could check with the dev's own wallets, sniper bots, or both in block 0. On most of the rest nobody but the dev bought in block 0; unlinked early buyers were there on 2% of coins. 
 By those rules, the dev's wallets were in block 0 of 21% of new coins and sniper bots in 28%. On 12% both were there. Unlinked early buyers showed up in block 0 of 2%. Pump.fun's Mayhem agent traded 19% of new coins at some point but almost never in block 0.

 Sniper bots became less common: they were in block 0 of 39% of November's launches and 22% of September's.

## 05 · The dev's bundle How much do Pump.fun devs make from bundling?

 On a launch with a bundle, the dev's wallets bought a median of 10% of all tokens in the first blocks. On 2% of bundled launches they took more than half.

 How much the bundle takes coins with a bundle, by share of the supply the dev's wallets bought in the first blocks 

 1,696,430 coins where the dev's own wallets bought in the launch block or the next two. Share of the supply bought by those wallets in that time; the dev's own first purchase is not included. 
 On bundled launches up to the end of June, the dev and the bundled wallets made at least $579 million after Pump.fun's fees, counting the part they sold. Counting unsold holdings as worthless, they made $529 million. The dev and the bundled wallets came out ahead together on 71% of bundled launches, and the best 1% of bundled launches made 65% of their total profit. The table lists the ten launches that made the most for their dev and bundled wallets.

 Day Dev Put in Profit 
 23 Apr 2026 8qNz…CX4Q $78k $3.3M 
 27 Jun 2026 CDFW…JKJq $50k $1.2M 
 25 Mar 2026 3fqT…ke51 $27k $719k 
 8 Apr 2026 4UYS…BG42 $34k $649k 
 26 Feb 2026 2o9g…RPM1 $43k $640k 
 23 Apr 2026 6s38…CK6g $25k $583k 
 30 May 2026 4ncz…j53h $25k $547k 
 5 May 2026 23CN…FeQr $31k $496k 
 13 Dec 2025 69Ms…nwWB $17k $482k 
 5 Jan 2026 GHte…jRKD $18k $473k 

 From July the picture changed. The money bundled wallets put into the coins they bundled rose from $56.4 million in June to $1.2 billion in September, and 61% of September's came in single purchases of 1,000 SOL or more, made in the trading pool within about a second of launch, on coins that had already filled their launch pool; in June there were none. Most of that money came back out through other wallets. The bundled wallets passed their tokens to other wallets, which sold them into the pool: on 98% of these launches, the dev's wallets and the wallets they fed took out at least 90% of what went in within three days. Our count follows only the dev and the wallets that bought in the launch blocks, so it shows them $703 million down in September, and the profit figures here stop at launches up to the end of June.

 Money the dev's wallets put into their own launches purchases by bundled wallets on the coins they bundled, by month, in dollars 

 Purchases by the dev's bundled wallets on the coins they bundled, in the three days from each launch day, in dollars at the day's median SOL price. Red: single purchases of 1,000 SOL or more, which start in July. October 2026 holds seven days. 
 Devs sell fast. On 65% of all launches the dev's first sale came within a minute of launch, and within a day on 90%. Many launches come from wallets that launch over and over. Wallets that paid for the first purchase of 100 coins or more account for 49% of all launches, and the busiest one did it for 103,639 coins.

 How fast the dev sells all new coins, by time from launch to the dev's first sale 

 All 8,212,568 launches we could check. Time from the first purchase to the dev's first sale, counting trades in the three days from the launch day. 

## 06 · The sniper bots Do Pump.fun sniper bots make money?

 On launches up to the end of June, we counted 25,882 wallets that sniped by our rule. Between them they spent $440 million on the launches they sniped.

 On the part of each purchase they sold, sniper bots made $31.5 million after Pump.fun's fees and network fees. That figure leaves out what they could not sell. Coins that died before a sniper got out are a loss too, and counting those as worthless, sniper bots as a group made $15.2 million.

 Who made the money profit after fees on what each group sold, launches up to 30 June 2026 

 Launches from 30 October 2025 to 30 June 2026. Profit after Pump.fun's fees and network fees on the part of each purchase that was sold, in the three days from each launch day, at the day's median SOL price. Devs and their bundles: the dev plus the bundled wallets on launches with a bundle; a floor, because wallets fed by transfer are not counted. Jito tips are not included. 
 Devs and their bundles made at least 18 times as much as the sniper bots.

 The money is concentrated. The top ten sniper wallets made $6.7 million on the part they sold, and the top hundred $13.1 million. Counting unsold holdings as worthless, 54% of sniper wallets came out ahead.

 How sniper wallets came out sniper wallets by profit after fees, SOL out minus SOL in 

 All 25,882 sniper wallets on launches up to the end of June, SOL out minus SOL in on what they sniped, after fees, with unsold holdings at zero. 
 The table lists the ten sniper wallets that made the most on their sales.

 Wallet Launches Profit on sales Out minus in 
 2ezv…w2xB 98,888 $1.4M $1.4M 
 Hugk…x6Yh 28,467 $896k $887k 
 5brv…LyAr 11,727 $835k $833k 
 EgQX…77aq 36,077 $663k $656k 
 GG6C…yEaP 4,399 $660k $658k 
 2CQg…ctFG 26,839 $417k $416k 
 Gpb9…PRS1 4,950 $367k $365k 
 CGPz…rhqi 2,199 $315k $315k 
 9ryB…XLaq 1,478 $290k $288k 
 DQAp…adxR 128,408 $272k $263k 

 Fees eat into those profits. On the launch curve of most coins, Pump.fun takes 1.25% of every purchase and every sale, so a bot that buys and sells within seconds pays 2.5% of its money each time, plus network fees. Tips that bots pay to land early, such as Jito tips, are not in these figures either. Any of the wallets in the table can be checked trade by trade through Bitquery's Solana DEX API .

## 07 · For the buyer How can you check if a Pump.fun coin is bundled?

 If you buy a Pump.fun coin in its first minute, someone may already have bought it before it existed for you. On 21% of launches that someone was the dev's own set of wallets, holding a median 10% of all tokens, bought at the launch price.

 You can check a coin before buying. Look at who bought in block 0. Several purchases right after the launch transaction, from wallets that sell within minutes, are the bundle pattern, and a public Jito bundle explorer shows whether they went out in one package with the launch. Bitquery's Pump.fun API returns the trades on a coin from its first block, and the token holder API shows who holds it now.

## 08 · Method How did we measure this?

 We used Bitquery's records of Solana DEX trades over the 11 months, and of Solana transfers for the funding test. The full history of Solana trades and transfers is also sold as files on the Bitquery Data Store , and the same trades are available through Bitquery's Solana DEX API . You can also check any launch's first buyers in Claude with the Solana MCP .

 A coin counts as new when Pump.fun was where it first traded and its first purchase was at the opening price of a fresh launch curve, which leaves out older tokens. The dev is the wallet that paid for that first purchase, and block 0 is the block it landed in. On launches where we also have the creation record, from November 2025 to early July 2026, the wallet that paid for the first purchase was the one that created the coin 98% of the time. For each coin we read the trades of its launch day and the next two days.

 We left out purchases and sales of a coin that a wallet made inside one transaction, the pattern of the volume bots that pad a coin's trading. We also left out Pump.fun's Mayhem agent, launches on 13 days when Bitquery's archive is missing 5% or more of Solana's blocks, launches from 7 to 26 May 2026, when one kind of Pump.fun trade is missing from the archive, and launches after 15:45 UTC on 7 October, when Pump.fun's newest trade format is not yet recorded.

 Profit counts only what a wallet sold. For each wallet and coin, we take the number of tokens it both bought and sold and multiply it by the gap between its average selling price and its average buying price. Prices include Pump.fun's fee of 1.25% on purchases and sales, and we subtract the network fees on the wallet's trades (fees on failed attempts are not counted) and turn SOL into dollars at the day's median price. The second measure, SOL out minus SOL in, counts coins a wallet never sold as worthless. Both leave out Jito tips and the creator fee that devs earn on trading in their coin.

 We checked the rules against the chain. The bundle test was compared with the public Jito bundle record on 6 days. Some launches, most of the ones we sampled on 15 April, did not go through Jito at all; on that day 14% of buyers in the four places after the launch had a SOL link to the dev in the day before, against 12% on 15 June, when most launches did use Jito, so the test treats both the same way. A fourth test, SOL passing between a buyer and the dev in the day before the launch or both getting their SOL from the same small wallet, would have added 0.4% to the bundled launches in the first three months, so we left it out. Pump.fun's own trade records, read from a public Solana node, confirmed the fee and that our purchase amounts match what reached the launch curve.

## 09 · Evidence Addresses and transactions cited

 What Address or transaction 
 15 June coin 7oE8o8…axpump 
 Its dev 3KMsBz…gmj7dE 
 Launch 4efCSX…FfMA 
 Bundled wallet 1 9sGVxN…ovUR8a 
 Bundled wallet 2 D1Xtme…irb89Y 
 Bundled wallet 3 DueXop…G5FQ1L 
 Bundled wallet 4 HVyrZc…xqhJ9k 
 Fifth wallet Hz8VCw…oWrj8D 
 Bundle purchase 1 B8CoDR…yjog 
 Bundle purchase 2 bkCk9j…1MtB 
 Move to the pool s7Ynqj…rA1c 
 Pool purchase 3jRnHF…Zzj6 
 Mayhem agent BwWK17…m2de6s 

## FAQ

### What is a Pump.fun sniper bot?

 A sniper bot is a program that buys a new coin within a fraction of a second of its launch, hoping to sell to slower buyers at a higher price. In our data, sniper bots are wallets that bought in the first blocks of coins from 10 or more different devs.

### What is a Pump.fun bundle or bundler?

 A bundle is a set of purchases a coin's dev makes from several wallets at the moment of launch, packed into one Jito bundle with the launch so that nobody can get in between. It lets the dev take a large share of the supply at the opening price without one wallet looking big. Tools that send these packages are called bundlers.

### What is block 0?

 Block 0 is the Solana block that holds a coin's first trade. Purchases in block 0 happen in the same 0.4 seconds as the launch, before an ordinary buyer could see the coin on the site.

### How many Pump.fun coins are sniped?

 In the 11 months we checked, a wallet other than the dev made a purchase in block 0 of 38% of new Pump.fun coins, and within the first three blocks of half of them. Sniper bots were in block 0 of 28% of launches.

### Do Pump.fun snipers make money?

 On launches up to the end of June, sniper bots made $31.5 million after fees on what they sold. Counting what they could not sell as worthless, they made $15.2 million, and 54% of sniper wallets came out ahead. The devs and their bundled wallets made far more.

### How fast do Pump.fun devs sell?

 Most sell within a minute. On 65% of the launches we checked, the dev's first sale came within a minute of launch, and on nine in ten it came within a day.

### How do you check if a Pump.fun coin is bundled?

 Look at the purchases in the coin's first block. Several purchases in the transactions right after the launch, from wallets that sell within minutes, are the signature of a bundle. A public Jito bundle explorer shows whether those purchases went out in one bundle with the launch.

 Limits on these figures
 A wallet counts as the dev's own only if it bought inside the launch transaction, had its fee paid by the dev or bought in the four transactions after the launch. Dev wallets that buy later, or in a separate block, count as sniper bots or unlinked buyers. Adding SOL links between buyer and dev would raise the count of bundled launches by 0.4% on the days we tested.
 A bundle shows that the purchases were packed together with the dev's signed launch transaction. It does not show who owns the wallets. A launch service that sends bundles for its customers would look the same.
 Sniper bots are wallets that bought early on launches by 10 or more devs. A sniper that uses a new wallet for each coin counts as an unlinked early buyer, and a dev who funds bundle wallets from an exchange is missed by the SOL-link test.
 About one coin in a hundred counted as new is an older coin whose price had gone back to the starting point. On days with creation records, 1.7% of new launches had no creation record near their first trade.
 Profit covers three days of trades from each launch day. Coins still held after that count only in the second measure, at zero.
 About one in twenty coins created on Pump.fun never traded at all, not even a first purchase by the dev, so they are not counted. We could check 8.2 million of the 9.1 million coins whose first trade was on Pump.fun in the 11 months. We left out coins launched on 13 days when Bitquery's archive is missing 5% or more of Solana's blocks, from 7 to 26 May 2026 and after 15:45 UTC on 7 October, when some Pump.fun trades are missing from the archive, and coins whose first recorded purchase was not at a new coin's opening price.
 Pump.fun's fee is 1.25% on most coins and 0.95% on the rest; we charge 1.25% throughout, so profits on the cheaper coins are slightly low. Bitquery records a Pump.fun sale on the launch curve after the fee until 8 June 2026 and before it from then on; we correct for that sale by sale.
 Profit follows only the dev and the wallets that bought in the launch blocks. Wallets that got a coin by transfer and sold it are left out: on sample days in March and June they took out between 35% and 83% as much SOL as the devs and bundled wallets made on bundled launches, so the totals for devs and bundles are a floor.

 Run it yourself

### Check who bought a Pump.fun coin first
 Every trade in this story comes from Bitquery's Solana data. The Bitquery MCP server puts that data behind an AI assistant, so you can ask who bought a coin in its first block, whether those wallets sold, or where a wallet got its SOL, without writing the query yourself. The full history of Solana trades is also sold as files on the Bitquery Data Store .

 List the first buyers of any Pump.fun coin See when the dev and the first buyers sold Trace where a wallet's SOL came from Compare a wallet's trades across launches 
 Explore Bitquery MCP → Figures measured from Pump.fun trades on Solana, 30 October 2025 to 7 October 2026, checked on 10 October 2026. 

 Legal disclaimer
 This article is provided for informational and educational purposes only and reflects analysis of publicly available on-chain data as of the dates indicated. It does not constitute legal, financial, compliance, or investment advice, and nothing in it is a recommendation to buy, sell, or hold any token or asset.
 The findings describe Pump.fun trades on Solana between 30 October 2025 and 7 October 2026. Wallets are classed as a dev's own wallets, sniper bots or other early buyers by the rules set out in the method section; the counts depend on those rules and on Bitquery's records of the chain. Wallets are described by their behaviour on the chain. None of them is attributed to a named person or group.
 Reported by Gaurav Agarwal for Bitquery Research, with AI tools; every figure was checked against the raw data.
 Nothing herein should be relied upon as a definitive determination of fact. Readers should conduct their own independent verification before taking any action. The authors and publisher accept no liability for any loss or damage arising from reliance on this material. All trademarks and company names are the property of their respective owners.

### Run the next investigation in minutes
 Ask any question of the blockchain. Bitquery's AI Investigations agent traces funds, attributes wallets, and writes auditable reports across every major chain. Prefer to do it yourself? Connect the Bitquery MCP server to your AI assistant, pull the raw datasets , or query the chain directly with the Bitquery API .
 Explore AI Investigations → Get the Solana dataset 

## Related reading
 
- Investigation Three wallets sold the old KIMCHI and bought the new one in the same minute 

- Investigation Pump.fun Mayhem mode: only 1 in 50 graduations fills the pool 

- Investigation Pump.fun's biggest wins: only 26% was real trading profit
