# madeonsol-pumpswap

Fonte: https://madeonsol.com/blog/what-is-pumpswap

- 
- 
- 
- 

 Powered by: 

 What Is PumpSwap? How Pump.fun's DEX Works After Bonding (2026) 
- 
- 
- 
- 
- 
- 

- 
 Disclosure: This article contains affiliate links. If you sign up through them, MadeOnSol may earn a commission at no extra cost to you. This never affects our rankings, ratings, or reviews.
 
 The data behind this article
 Everything we track — real-time KOL trades, Pump.fun deployer reputation, and the all-DEX firehose — is available as an API. REST, WebSocket, and webhooks. Free key: 200 requests/day.

 See API pricing 
 Tools mentioned

## Compare features and read reviews.
 Live health scores, average ratings, and direct links on MadeOnSol.

### Pump.fun
 Launch a memecoin on Solana in under a minute

### Memecoin Observatory MCP
 AI-powered memecoin analysis, trend tracking, whale monitoring, and cultural analysis for Solana via MCP

 Build a deployer sniper bot

 Access deployer alerts, bonding stats, and tier data via API. Free tier: 200 requests/day.

 Start free 
 import { MadeOnSol } from "madeonsol";

const client = new MadeOnSol({ apiKey: "msk_your_key" });

// Elite deployer alerts with KOL buy enrichment
const { alerts } = await client.deployer.alerts({ limit: 5 });

// Top deployers by bonding rate
const { deployers } = await client.deployer.leaderboard({ tier: "elite" }); 
 npm install madeonsol Full API docs 

 Keep reading

## More from the blog.

 All Guides 
 
 Guides

### What Is Pump.fun Revenue Sharing? How PumpSwap Fees Work for Token Creators (2026)
 Understand how pump.fun's revenue sharing model works after tokens graduate to PumpSwap. Bonding curve fees, PumpSwap swap fees, creator revenue splits, and realistic earning estimates for token deployers.
 7 min May 25, 2026 

 Education

### Inside Our Deployer Intelligence: How We Score 10,600+ Pump.fun Deployers
 How MadeOnSol classifies pump.fun deployers into tiers, tracks bonding rates, and surfaces the 34 elite deployers whose tokens graduate at 71% — versus the 1-2% baseline.

 Enjoyed this article?

## Explore the live data.
 Real-time KOL trades, Pump.fun deployer intel, and 1,200+ ranked Solana & Robinhood Chain tools — free to explore.
 Open the KOL Tracker 
 API reference Start free Browse all articles 

 Explore more
 Top 10 Trading Bots Top 10 DEXs & Swaps Deployer Hunter KOL Tracker Compare Yields Solana Glossary 

## PumpSwap 's Impact on the Solana Ecosystem

### For Pump.fun 

 PumpSwap transforms Pump.fun from a token launchpad into a full-stack DeFi platform. Instead of handing off tokens to Raydium after graduation, Pump.fun now controls the entire token lifecycle. The protocol fees from PumpSwap trading generate revenue for Pump.fun beyond just the bonding curve phase.

### For Raydium

 PumpSwap directly competes with Raydium for Pump.fun-graduated token volume. Since Pump.fun tokens represented a significant portion of Raydium's memecoin trading volume , this shift has redirected some liquidity and fees. However, Raydium remains Solana's largest AMM overall, with deep liquidity on major pairs and established token pools.

### For Jupiter 

 PumpSwap is just another liquidity source for Jupiter to route through. Jupiter indexes PumpSwap pools alongside Raydium, Orca , Meteora , and every other Solana DEX. For Jupiter users, PumpSwap's existence generally means better prices because there's more total liquidity available across the ecosystem.

### For Traders

 Traders benefit from:

- Lower costs — No migration fee means more liquidity in pools

- Faster access — Instant graduation means no trading gaps

- More competition — PumpSwap competing with Raydium puts downward pressure on fees

- Seamless experience — Jupiter makes the backend DEX choice invisible

## Advanced: Understanding PumpSwap Pool Mechanics

### Initial Pool State

 When a token graduates to PumpSwap, the pool is created with:

- All SOL collected during the bonding curve (~85 SOL, now minus zero migration fee)

- The remaining unsold tokens from the 1 billion supply

- An initial price that continues from the bonding curve's final price

 This creates a seamless transition — the last price on the bonding curve approximately equals the first price on PumpSwap.

### Price Impact

 Like all constant-product AMMs, the price impact of a trade on PumpSwap depends on the trade size relative to pool liquidity. Freshly graduated tokens have relatively small pools (~85 SOL), which means:

- Small trades ($10–$100) have minimal price impact

- Medium trades ($500–$1,000) can move the price noticeably

- Large trades ($5,000+) can have significant slippage 

 13 min May 26, 2026 

 Guides

### How to Get pump.fun Token Trades via API: the Per-Mint Trade Tape (2026)
 One GET returns every buy and sell on a pump.fun token, newest first, with the executed price, the pool price at that slot, the wallet and the early-buyer rank. Cursor paging, buy/sell and wallet filters, and what the coverage block tells you before you trust the numbers.
 9 min September 5, 2026 

 Analytics

### Pump.fun Surge Alerts, Day 1: 138 Fires and What Happened an Hour Later
 First live day of surge alerts, 28 Aug 2026: 138 pump.fun surges on 104 mints. Fires with no risk flag were above their fire price an hour later 60% of the time; fires flagged early_buyers_exiting, 6%.
 10 min August 28, 2026 

 Analytics

### Pump.fun Deployer Stats — August 2026: 1.03M Launches, 18,202 Graduations, a 1.8% Bond Rate
 August 1–28, 2026: 1,032,440 launchpad deploys from 223,339 wallets, 18,202 graduations (1.8%), median time to bond 1 minute, median graduate peak $31K. 1,170 wallets minted 40% of the month's tokens.
 10 min August 28, 2026 

 Trading

### hood.fun Explained: Robinhood Chain's Bonding-Curve Launchpad
 hood.fun is the pump.fun-style token launchpad on Robinhood Chain. Here's how its bonding curve works, the graduation mechanics into a Uniswap pool, the key numbers, and how it compares to pump.fun on Solana.
 4 min July 14, 2026 

 If you've traded memecoins on Solana, you've probably used Pump.fun — the platform where anyone can launch a token on a bonding curve . But what happens after a token completes its bonding curve? That's where PumpSwap comes in.

 PumpSwap is Pump.fun 's native decentralized exchange (DEX), launched in March 2025. It replaced the previous system where graduated tokens migrated to Raydium , keeping the entire lifecycle — from token creation to open-market trading — within the Pump.fun ecosystem.

 This guide explains how PumpSwap works, why Pump.fun built its own DEX, and what it means for traders and liquidity providers.

## The Problem PumpSwap Solves

 Before PumpSwap, every Pump.fun token that completed its bonding curve had to migrate to Raydium . This migration process had several issues:

 Migration fees. Creating a Raydium pool cost approximately 6 SOL, which was deducted from the bonding curve's collected liquidity. This was a significant cost that reduced the available liquidity for the token.

 Delay. The migration process wasn't instant. There was a gap between bonding completion and Raydium pool creation — sometimes minutes, sometimes longer. During this window, trading was effectively paused, and price discovery was disrupted.

 Fragmented experience. Traders had to switch from Pump.fun's interface to Raydium or Jupiter after graduation. The user experience was disjointed.

 Dependency on a third party. Pump.fun's entire post-graduation infrastructure depended on Raydium, a separate protocol with its own priorities, fees, and potential issues.

 PumpSwap solves all of this by handling graduation internally.

## How PumpSwap Works

### The Graduation Process

 When a Pump.fun token's bonding curve reaches its target (~85 SOL deposited; the threshold is SOL-denominated, so the USD market cap floats with SOL price), here's what happens:

- Bonding curve completes. The final buy pushes the curve past the threshold.

- Instant migration. Unlike the old Raydium migration, PumpSwap creates a liquidity pool immediately — no delay, no waiting period.

- Liquidity deposited. The SOL collected during the bonding curve phase is paired with remaining tokens and deposited into a PumpSwap AMM pool.

- Zero migration fee. PumpSwap eliminated the ~6 SOL migration fee entirely. All collected liquidity goes into the pool.

- Trading continues. The token is immediately tradeable on PumpSwap, and Jupiter indexes the pool for aggregated routing.

### PumpSwap's AMM Design

 PumpSwap uses a constant-product AMM (x * y = k), the same fundamental design as Uniswap v2 and Raydium's standard pools. This means:

- Simple and predictable pricing. The price moves along a smooth curve based on supply and demand.

- Full- range liquidity. Liquidity is spread across all possible prices (unlike concentrated liquidity systems like Orca Whirlpools).

- Anyone can LP. After graduation, anyone can add liquidity to a PumpSwap pool and earn a share of trading fees.

### Fee Structure

 PumpSwap charges a 0.25% fee on every swap:

 Fee Component Percentage Recipient 
 LP fee 0.20% Liquidity providers 
 Protocol fee 0.05% Pump.fun protocol 
 
 This is competitive with Raydium's standard pool fees and significantly cheaper than the 1% fee charged during the bonding curve phase on Pump.fun itself.

### Creator Revenue Sharing

 One of PumpSwap's most significant features is creator revenue sharing. A portion of the protocol fees earned from trading can be directed to the token's original creator. This gives token creators a financial incentive to grow their token's trading activity long-term, rather than just dumping at graduation.

 The revenue share model is designed to align incentives — creators benefit from sustained volume, not just from selling their initial holdings.

## PumpSwap vs Raydium Migration

 Understanding the differences between PumpSwap and the old Raydium migration helps explain why this change matters.

 Feature PumpSwap Raydium Migration (Old) 
 Migration fee 0 SOL ~6 SOL 
 Migration speed Instant Minutes (sometimes longer) 
 Liquidity preserved 100% of bonding curve SOL Minus ~6 SOL fee 
 Trading downtime None Brief gap during migration 
 LP opportunities Open to anyone Open to anyone 
 Jupiter integration Yes (indexed automatically) Yes 
 Swap fee 0.25% 0.25% (standard pools) 
 Creator revenue share Yes No 
 Pool type Constant product AMM Constant product AMM 

### What This Means for Traders

 More liquidity at graduation. Without the ~6 SOL migration fee, graduated tokens start with more liquidity in their pool. This means slightly better execution prices and lower slippage right after bonding.

 No trading gaps. The instant migration eliminates the awkward period where a token has bonded but isn't yet tradeable. You can buy and sell continuously through the graduation transition.

 Same aggregator access. Jupiter routes through PumpSwap pools just like it routes through Raydium. If you're using Jupiter for swaps (which you should be for best pricing), the backend change from Raydium to PumpSwap is mostly invisible — you still get the best available price.

## How to Trade on PumpSwap

### Option 1: Via Jupiter (Recommended for Best Price)

 The easiest way to trade PumpSwap tokens is through Jupiter :

- Go to jup.ag and connect your wallet

- Search for the token by name or paste the contract address

- Enter your swap amount and execute

 Jupiter automatically finds the best route, which may include PumpSwap pools, Raydium pools, or a combination.

### Option 2: Via Pump.fun Directly

 After graduation, the token's page on Pump.fun shows a link to trade on PumpSwap. You can swap directly through the Pump.fun interface.

### Option 3: Via Trading Terminals

 Advanced trading tools like Axiom , BullX, and Photon support PumpSwap pools. These platforms offer additional features like limit orders , auto-sells, and portfolio tracking that the native PumpSwap interface doesn't provide.

### Option 4: Direct on PumpSwap

 Navigate to PumpSwap's interface directly to browse available pools, swap tokens, and manage LP positions.

## Providing Liquidity on PumpSwap

 PumpSwap opens a new opportunity for liquidity providers on Solana. Here's what you need to know.

### How to Add Liquidity

- Find the token's pool on PumpSwap

- Deposit an equal value of SOL and the token

- Receive LP tokens representing your share of the pool

- Earn 0.20% of every swap executed in the pool

### LP Considerations

 Impermanent loss is real. Memecoin prices are extremely volatile. If you provide liquidity and the token price moves significantly in either direction, you may end up with less total value than if you'd simply held. This is especially pronounced with memecoins that can 10x or crash 90%.

 Volume is key. Your LP earnings depend on trading volume . High-volume tokens generate significant fees; dead tokens generate almost nothing. Focus on tokens with active communities and sustained interest.

 No concentrated liquidity. PumpSwap uses full-range AMM pools, meaning your capital is spread across all prices. This is simpler to manage than concentrated liquidity (like Orca Whirlpools) but less capital efficient.

 Rug pull risk. If you provide liquidity for a memecoin that gets abandoned or rug-pulled, you'll be left holding worthless tokens. Only LP for tokens you've thoroughly researched.

## Which Tokens Use PumpSwap vs Raydium?

 The landscape has evolved over time:

 Most new Pump.fun graduations → PumpSwap. Since PumpSwap's launch, the majority of newly graduating tokens migrate to PumpSwap by default.

 Older tokens → Raydium. Tokens that graduated before PumpSwap launched remain on Raydium. These include many established memecoins with deep liquidity.

 Some tokens have both. A token can have liquidity on both PumpSwap and Raydium (and other DEXs). Jupiter aggregates across all of them, so as a trader using Jupiter, you automatically get the best price regardless of where liquidity sits.

### How to Check Where a Token Trades

- Birdeye — Shows all pools for a token across every DEX

- DexScreener — Displays pool-level data including which DEX each pool is on

- Jupiter — Automatically routes to the best available pool

 As more liquidity is added by LPs and the pool grows, price impact decreases.

### Monitoring PumpSwap Pools

 Use these tools to track PumpSwap pool data:

- DexScreener — Real-time charts, volume, and liquidity for PumpSwap pools

- Birdeye — Analytics, holder data, and multi-DEX pool views

- GMGN — Wallet-level analysis and smart money tracking on PumpSwap

- Deployer Hunter — Track which deployers consistently produce tokens that graduate and hold value

## Frequently Asked Questions

 What is PumpSwap? 
PumpSwap is Pump.fun's native decentralized exchange (DEX) on Solana. It handles the trading of tokens after they complete their bonding curve on Pump.fun. Instead of migrating to Raydium (the old system), graduated tokens now get their own liquidity pool on PumpSwap instantly and with zero migration fees.

 Is PumpSwap the same as Pump.fun? 
Not exactly. Pump.fun is the token creation and bonding curve platform. PumpSwap is the DEX where tokens trade after graduation. They're part of the same ecosystem but serve different functions — Pump.fun handles the launch phase, PumpSwap handles post-graduation trading.

 Can I trade PumpSwap tokens on Jupiter? 
Yes. Jupiter indexes PumpSwap pools and routes trades through them automatically. When you swap on Jupiter, it may route through PumpSwap, Raydium, or both — whichever gives you the best price. You don't need to interact with PumpSwap directly.

 What are PumpSwap's fees? 
PumpSwap charges 0.25% per swap — 0.20% goes to liquidity providers and 0.05% goes to the protocol. This is the same as Raydium's standard pool fees and significantly lower than the 1% fee during Pump.fun's bonding curve phase.

 Do all Pump.fun tokens go to PumpSwap now? 
Most new Pump.fun graduations migrate to PumpSwap. Tokens that graduated before PumpSwap launched remain on Raydium. Some tokens may have liquidity on both platforms.

 Can I provide liquidity on PumpSwap? 
Yes. After a token graduates, you can add liquidity to its PumpSwap pool by depositing equal values of SOL and the token. You'll earn a share of the 0.20% LP fee on every swap. Be aware of impermanent loss risks, especially with volatile memecoins.

 Is PumpSwap better than Raydium? 
For Pump.fun-graduated tokens, PumpSwap offers clear advantages: zero migration fees, instant graduation, and creator revenue sharing. For the broader Solana ecosystem, Raydium still has deeper liquidity on major pairs and offers concentrated liquidity (CLMM) pools. They serve different purposes, and Jupiter aggregates both.

 What happened to the Raydium migration fee? 
The old Raydium migration cost ~6 SOL per token graduation. PumpSwap eliminated this entirely — migration is free. This means more of the bonding curve's collected SOL goes directly into the trading pool as liquidity.

 How does creator revenue sharing work? 
A portion of PumpSwap's protocol fees (from the 0.05% protocol cut) can be shared with the token's original creator. This gives creators an ongoing financial incentive to build and maintain their token's community, rather than profiting solely from selling tokens early.

## The Bottom Line

 PumpSwap represents a natural evolution for Pump.fun — from token launchpad to full-lifecycle DeFi platform. By handling both the launch (bonding curve) and post-graduation trading (PumpSwap DEX) in-house, Pump.fun eliminates friction, reduces costs, and creates a smoother experience for both token creators and traders.

 For most traders, the change is almost invisible — if you use Jupiter for swaps, it automatically routes through PumpSwap when that offers the best price. The biggest practical benefit is that graduated tokens now start with more liquidity (no migration fee) and there's zero downtime during the graduation transition.

 Whether you're trading memecoins, providing liquidity, or launching your own token, understanding PumpSwap helps you navigate the Solana memecoin ecosystem more effectively.

 Learn how to use Pump.fun from scratch in our complete Pump.fun guide . Compare Solana DEXs in our Raydium vs Jupiter vs Orca breakdown . Discover more Solana tools on MadeOnSol . 

## FAQ

### What is PumpSwap?

 PumpSwap is Pump.fun's own decentralized exchange where tokens trade after they graduate from the bonding curve. Instead of migrating graduated tokens to Raydium, Pump.fun now keeps them trading on PumpSwap, an automated market maker (AMM) it controls.

### How is PumpSwap different from the old Raydium migration?

 Previously a graduated Pump.fun token migrated to a Raydium pool, which cost a migration fee. With PumpSwap, graduation moves the token to Pump.fun's own AMM instead — no Raydium migration fee, trading continues seamlessly, and liquidity and fees stay within the Pump.fun ecosystem. Tokens still appear on aggregators like Jupiter.

### Does PumpSwap have fees?

 PumpSwap charges swap fees like any AMM, and it introduced a creator revenue-sharing model where a token's creator earns a share of the trading fees on its pool. Exact percentages can change, so check current Pump.fun documentation.

### Can I still trade graduated tokens on Jupiter and other aggregators?

 Yes. PumpSwap pools are on-chain and publicly accessible, so aggregators like Jupiter route through them automatically when they offer the best price. You don't have to use the Pump.fun interface to trade a graduated token.

### What does PumpSwap mean for snipers and bots?

 Bots that previously watched for Raydium pool creation at graduation now need to detect PumpSwap pool creation instead. Most major Solana trading bots and snipers have already integrated PumpSwap support.
