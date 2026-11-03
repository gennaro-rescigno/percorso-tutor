# arxiv-2602.13480-memetrans-melt

Fonte: https://arxiv.org/html/2602.13480v2

MELT: A Behavioral Trace Dataset for High-Risk Memecoin Launch Detection 

- 

- 

- 

- 

- 

- 

- 
- 

- 
 
 Skip to main content 

 Title: 

 Content selection saved. Describe the issue below:

 Description: 

 License: CC BY-NC-SA 4.0

arXiv:2602.13480v2 [cs.CR] 21 May 2026

# MELT: A Behavioral Trace Dataset for High-Risk Memecoin Launch Detection

 Sihao Hu

 Selim Furkan Tekin

 Yichang Xu

 Ling Liu
 
 Affiliation:  School of Computer Science
 
 Affiliation:  Georgia Institute of Technology, Atlanta, USA
 
 Email:  {shu335,stekin6,xuyichang,ll72}@gatech.edu 

###### Abstract

 Launchpads have become the dominant mechanism for issuing memecoins, exposing investors to a new class of high-risk launches that existing rug-pull detection methods cannot capture. We argue that detecting these threats requires structured behavioral traces that underlie raw heterogeneous blockchain data, i.e. , how insiders accumulate, coordinate, and unwind positions. To enable such analysis, we introduce MELT ( ME mecoin L aunch T race), the first behavioral trace dataset for analyzing and detecting high-risk memecoin launches on Solana. MELT covers 41k+ memecoin launches with 200M+ transactions parsed into typed behavioral records that distinguish swaps, wash trades, transfers, and mints. Beyond per-account behaviors, MELT contributes bundle-trace data that links accounts controlled by the same entity, revealing that, on average, 36.5% of token supply is held by coordinated accounts, a concealment strategy that disguises the true ownership concentration from unsuspecting buyers. On top of these traces, MELT provides 122 behavioral features and risk-level annotations, enabling supervised learning at a population scale. We benchmark representative ML models on the high-risk launch detection task. Integrating their predictions into a simple memecoin selection strategy reduces investment loss significantly, demonstrating that behavioral traces can be translated into risk mitigation. Our dataset and code is available at https://github.com/git-disl/MELT .

## 1 Introduction

 On January 17, 2025, U.S. President Donald Trump launched the $TRUMP token on the Solana blockchain  ( Wikipedia, 2025 ) . Within 60 hours its market capitalization surged to roughly $15 billion, briefly congesting the Solana network and driving daily DEX trading volume to a record $39.2 billion  ( Helius Labs, 2025 ) . The event brought a niche phenomenon into public view: memecoins, digital tokens that embody Internet memes with no intrinsic utility, have nonetheless become a focus of speculative trading at a scale capable of reshaping on-chain market dynamics.

 The infrastructure behind this growth is the launchpad , a no-code interface that lets anyone create a memecoin within minutes. By October 2025, the largest launchpad, Pump.fun, had issued 12.8 million memecoins on Solana, accounting for roughly half of all tokens ever created on the chain  ( Research, 2025 ) . When created, a memecoin is automatically initialized through a launchpad sale at deterministically increasing prices. Once the sale reaches a fixed threshold, the accumulated liquidity is migrated to a Decentralized Exchange (DEX) for public trading. This automated pipeline removes the technical barriers to issuing a memecoin, including those that previously deterred fraudulent operators at scale  ( CoinDesk, 2025 ) .

 Related Work. Launchpads give rise to a new class of threats that prior detection methods are not designed to capture. Existing methods target DEX-based rug pulls  ( Cernera et al., 2023 ; Mazorra et al., 2022 ; Yaremus et al., 2025 ) , where creators directly own the liquidity pool and can withdraw its assets at will. They therefore rely on pool-level operational signals, such as token burns and sudden liquidity withdrawals. This assumption breaks in the launchpad setting: the liquidity pool is held entirely by the launchpad protocol, leaving creators with no direct control over it but with substantial first-mover and coordination advantages during the sale. As illustrated in Figure  1 , the threat instead originates during the launchpad sale itself, where insiders (developers and affiliated accounts) accumulate tokens at the lowest price tiers and unwind them after migration, draining base assets and collapsing prices for later buyers. A few recent studies have begun to examine launchpad markets  ( Voinea, 2025 ; Li et al., 2025 ) , but they offer only economic or sociological analyses without systematically detecting this new class of threats.

 The core signals for detecting these high-risk memecoins therefore lie in launchpad-stage behavioral traces. However, such traces cannot be directly read off raw on-chain data, for three reasons. First, raw transactions are heterogeneous low-level program invocations whose formats vary across interacting programs and carry no explicit semantics of higher-level user behaviors. Second, behavioral signals such as holding concentration emerge only after aggregating and engineering features over these traces. Most importantly, insiders actively obscure their coordination by operating through multiple accounts that appear to act independently, deliberately concealing cross-account coordination from on-chain analysis.

 Scopes and Contributions. To open the new problem for systematic study, we introduce MELT ( ME mecoin L aunch T race), the first behavioral trace dataset for analyzing and detecting high-risk memecoin launches on Solana. MELT is constructed over a period centered on the $TRUMP launch (Dec. 1, 2024 – Mar. 1, 2025), capturing the full memecoin market speculative cycle of growth, peak, and cooling within a single coherent period. It covers all 41,470 memecoin launches that complete a four-stage lifecycle (creation → launchpad sale → migration → DEX trading), with over 200 million on-chain transactions extracted into high-level behavioral records.

 Beyond per-account behaviors, MELT contributes bundle-trace data collected from various sources including off-chain data. These bundle traces effectively link accounts likely controlled by the same entity, revealing that 36.5% of token supply that appears to be held by independent accounts is in fact controlled by coordinated accounts with concentrated ownership. This reflects a deliberate concealment strategy that disguises true ownership concentration from unsuspecting buyers and is invisible in raw transactions.

 On top of these behavioral traces, MELT provides 122 behavioral features across five groups that characterize different aspects of a memecoin launch, paired with a configurable risk-level annotation method that labels each memecoin launch based on its post-migration market trajectory. Together, MELT enables ML models to learn the mapping from launchpad-sale behavior traces to downstream risk outcomes, supporting proactive detection and alerting of high-risk memecoins before their DEX trading begins.

 To test the practical utility of MELT, we benchmark a suite of representative ML models on the high-risk memecoin detection task and investigate whether the dataset can be translated into actionable risk mitigation signals. Experiments show that integrating the risk prediction results into trading decisions can reduce investment losses by up to 34 percentage points, confirming its practical defensive value.

## 2 Background

 Account and Transaction. Solana stores all on-chain state in accounts , each identified by a unique address  ( Solana Documentation, ) . Users own accounts that hold balances of SOL (Solana’s native cryptocurrency) and other tokens. A transaction executes one or more operations automatically, i.e. , either all operations succeed or none take effect  ( Solana Documentation, ) .

 Memecoin and Mint Address. Each memecoin on Solana is uniquely identified by a mint address , which we use throughout this paper as the global identifier of a memecoin. Throughout this paper, we use memecoin to refer to a specific token type, and token(s) to refer to the actual balances or units held by users.

 Bonding Curve. During the launchpad sale, users buy or sell tokens directly with the launchpad. The price movement follows a bonding curve algorithm: the price depends only on how many tokens have already been sold, rising in fixed steps as cumulative sales increase  ( dYdX Foundation, 2024 ) . As shown in Figure  1 , the first buyers therefore pay the lowest prices, and each subsequent tier is more expensive, an asymmetry that gives insiders a substantial cost advantage.

 Developers and Insiders. The developer of a memecoin is the account that creates it on the launchpad. We use insiders more broadly to refer to the developer together with any coordinated accounts that share informational or operational advantages. Such participants exploit the bonding curve’s first-mover advantage to acquire tokens at the lowest price tiers.

 Decentralized Exchange (DEX) and Liquidity Pool. After the launchpad sale completes, the memecoin moves to a Decentralized Exchange (DEX) for public trading with broader market exposure. DEXs trade tokens through liquidity pools  ( Uniswap Labs, 2018 ) that hold paired reserves (e.g., tokens and SOL), where the price is determined by the reserve ratio, e.g. , if the pool holds x x tokens and y y SOL, the token price is p = y / x p=y/x . As a result, selling a large amount of tokens at once can cause the price to fall sharply.

 (a) Insider accumulation and unwind. 

 (b) A real high-risk memecoin trajectory. 

 Figure 1 : Lifecycle of a memecoin. 
 (a) Insiders accumulate substantial token holdings during the launchpad sale and unwind them during DEX trading, draining base assets and causing price declines.
 (b) A market trajectory of a real memcoin: the developer pre-purchases 97.5M tokens at the earliest bonding-curve tier ( Creation ). Prices rise as later buyers enter ( Launchpad sale ). At 80% sold, the launchpad migrates remaining memecoin tokens and collected base tokens (SOL) to a DEX liquidity pool ( Migration ), opening public trading with broader exposure ( DEX trading ). As liquidity deepens, insiders unwind their holdings and collapse the price. 

 The Lifetime of a Memecoin Launch: Figure  1 illustrates the typical lifetime of a high-risk memecoin with the creation, launchpad sale, migration and DEX trading stages. Among all the memecoins, less than 2% ever reach the migration stage  ( Smithii, 2025 ) . Memecoins that fail to migrate remain confined to the launchpad with negligible trading activity, posing limited risk to the broader investor base. We therefore focus exclusively on memecoins that successfully migrate to a DEX, since they gain sufficient market exposure, making high-risk ones the primary source of financial losses.

## 3 Dataset Construction

 MELT tracks memecoins issued through Pump.fun from Dec 1, 2024 to Mar 1, 2025, centered on the high-profile launch of the $TRUMP token on Jan 17, 2025. This event-anchored design captures three market regimes within a single coherent window:
 (i) Growth phase (Dec 2024 – mid Jan 2025) : Pump.fun’s daily token creation accelerated amid post-election crypto optimism.
 (ii) Peak speculation phase (mid Jan – early Feb 2025) : anchored by the consecutive launches of $TRUMP (Jan 17) and $MELANIA (Jan 19) alongside the U.S. presidential inauguration (Jan 20), producing the highest-velocity launchpad trading activity to date.
 (iii) Cooling phase (early Feb – Mar 2025) : speculative attention gradually diffused as early insiders unwound positions. The cooling was sharply accelerated by the $LIBRA collapse on Feb 14, 2025, which extracted $4.5B market cap within hours, eroding public trust and draining liquidity from the memecoin market.

 The construction pipeline consists of five stages: (1) memecoin launch collection, (2) transaction-to-behavior extraction, (3) bundle trace identification, (4) feature engineering, and (5) risk-level annotation. We elaborate each below.

 Table 1 : Data structures for example entries of a memecoin launch, a transaction after extraction, a bundle trace, and an annotation label. 

### 3.1 Memecoin Launch Collection

 We identify memecoins that completed migration from Pump.fun to DEX by tracking transactions initiated by the Pump.fun creator account that transfer SOL to the DEX fee account , which signals the creation of a new liquidity pool on DEX (migration). From the migration logs, we extract the mint address of the memecoin and the address of the DEX pool. For each mint address, we further retrieve token metadata (name, symbol, description, image, social handles) via the Metaplex Token Metadata program-derived address. The resulting memecoin launch records are summarized in memecoin.csv (Table  1 ), with overall statistics reported in Table  2 .

### 3.2 Transaction-to-Behavior Extraction

 For each memecoin mint, we collect on-chain transactions involving the memecoin. Pre-migration transactions span from creation to migration, and post-migration transactions cover the first hour after migration. Pre-migration data is used for feature engineering, while post-migration data is reserved for risk annotation.

 Since raw transactions are heterogeneous at the function level, we introduce a parser that first identifies the interacting program (e.g., Pump.fun bonding curve, DEX liquidity pool, or aggregator routes) and counterparty addresses from transaction logs, then computes the net balance change of each involved account to determine token flow direction and magnitude. Based on these signals, we classify transaction type as create (newly minted token), buy or sell (swap between a user and a liquidity pool), wash trade (buy and sell within a single transaction), or transfer (between user accounts). Table  2 reports the structural transaction records after extraction. Among 30.8M pre-migration transactions, 73.5% are normal buy or sell, 21.4% are wash trades, and 4.9% are transfers. Notably, 98.7% of "create" events co-occur with developer buys in the same transaction, indicating pervasive first-tier inventory pre-acquisition by developers. The post-migration 1-hour transaction count is approximately six times that of the entire pre-migration period, showing that migration to a DEX drastically amplifies market exposure.

 Table 2 : Statistics of collected memecoins and transactions. 

 Memecoins 
 Overall Tx. 
 Pre-mig. Tx. 
 Post-mig. Tx. 

 Total # 
 41,470 
 218,530,716 
 30,833,503 
 187,697,213 

 Avg. # per memecoin 
 – 
 5,269 
 743 
 4,526 

 Unique account # 
 – 
 – 
 1,916,363 
 6,538,577 

### 3.3 Bundle Trace Identification

 Insiders often hold tokens across multiple accounts to mask the true holding concentration. Identifying these bundled accounts allows us to reveal the actual holding concentration. We design heuristics to identify the bundle traces from three sources:

 (1) Multi-account co-purchase : Some insiders use multiple addresses within the same transaction to purchase tokens directly. Since signing such a transaction requires the private keys of all participating accounts, we treat accounts that jointly execute buys or sells in the same transaction as belonging to the same entity.

 (2) Fund-flow relationship : On Solana, creating a new account requires an initial deposit to cover rent, so accounts funded by the same funding address likely share common ownership. We identify the funding addresses of the 1,916,363 unique accounts involved in pre-migration transactions to reconstruct this relationship. We exclude funding addresses that belong to centralized exchanges, as their outgoing transfers typically reflect user withdrawals rather than coordinated control.

 (3) Jito bundle ID : Jito is a widely used block relay on Solana that enables atomic bundled execution of transactions. Insiders frequently use Jito to bundle buy and sell transactions across multiple wallets, enabling fast, simultaneous multi-account actions. These relationships are not included in on-chain data. For 22,668,222 pre-migration transactions that are labeled as "buy" or "sell", we crawled their Jito bundle IDs from the Jito Explorer . We treat accounts whose transactions share the same Jito bundle ID as controlled by the same entity.

 Table 3 : Statistics of bundle data by source. 

 Source 
 Bundled Holder Proportion 
 Bundled Supply Proportion 

 Co-purchase 
 6.46% 
 9.16% 

 Fund-flow 
 22.57% 
 28.22% 

 Jito Bundle 
 10.39% 
 15.96% 

 All 
 28.13% 
 36.50% 

 As shown in Table  1 , a bundle trace is organized as a (user account, identifier) tuple, where the identifier can be a transaction ID, a funder address, or a Jito bundle ID. For each memecoin launch, we cluster user accounts into bundles by matching identifier values and merge overlapping bundles. Table  3 reports the share of bundled accounts among holders and their share of total token supply. Notably, 36.5% of the total token supply is held by bundled accounts at the point of migration, revealing pervasive multi-account concealment.

 Bundle traces reveal the true holding concentration that raw on-chain data conceals. For example, after merging bundled accounts, the top-10 holder share increases by 24 percentage points for high-risk memecoins, compared to only 6 points for low-risk memecoins, indicating that bundle traces provide an informative signal for high-risk detection.

### 3.4 Feature Engineering

 We construct 122 features across five categories computed
strictly from pre-migration data to prevent label leakage:
 (1) contextual information (e.g., SOL price, calendar time;
6 features);
 (2) holding concentration (developer/fast-mover/top-holder
shares; 59 features);
 (3) market activity (transaction counts, traders, volume;
22 features);
 (4) bundle statistics (concentration after bundle-account
clustering; 35 features); and
 (5) time-series (pre-migration price/volume dynamics; time_span * 5 features). Table  4 summarizes these groups along with their representative features.

 Table 4 : Summary of designed feature groups for memecoin launch. 

 Feature Group 

 Description 

 Representative Features 

 Contextual information 

 Launch-time context of the token (e.g., SOL price and calendar time). 

 SOL_price, migrate_weekday, migrate_hour, migrate_month, etc. 

 Holding concentration 

 Holding concentration of tokens among early buyers (developer, first-movers). 

 dev_hold_pct, early_top k k _pct, top k k _hold_pct, etc. 

 Market activity 

 Pre-migration trading activity, including trader participation, volume, and wash trading signals. 

 tx_num, time_span, trader_num, holder_num, buy_num, sell_num, etc. 

 Bundle statistics 

 Holding concentration and trading statistics after grouping bundled accounts. 

 bundle_hold_pct, bundle_num, bundle_account_num, top k k _hold_pct, early_top k k _hold_pct, etc. 

 Time-series 

 Price and volume time-series between the creation and migration time. 

 time_span * [open_price, end_price, avg_price, volume] 

### 3.5 Risk Level Annotation

 We annotate each memecoin launch with a risk-level label using a two-layer approach that integrates a statistical label and a manual label, both derived from post-migration data.

 Statistical label : Post-migration price movements reflect a tug-of-war between insider sell-offs and external buying pressure. However, a substantial price drop shortly after migration is most likely attributable to insiders unwinding their low-cost inventory rather than to organic market dynamics. Based on this intuition, we define min_price_ratio as the minimum token price observed within y y minutes after migration, normalized by the migration price. The choice of y y reflects a trade-off: too small a window risks missing insider sell-offs that are still in progress, while too large a window allows the natural decay of speculative attention to dominate the signal. Empirically, we find that y = 20 y=20 minutes provides a reasonable balance: as shown in Table  5 , about 73% of memecoins drop below 40% of their migration price within this window.

 Table 5 : Distribution of memecoins w.r.t. min_price_ratio . 

 Value Range 
 [ 0.0 , 0.2 ) [0.0,0.2) 
 [ 0.2 , 0.4 ) [0.2,0.4) 
 [ 0.4 , 0.6 ) [0.4,0.6) 
 [ 0.6 , 0.8 ) [0.6,0.8) 
 [ 0.8 , 1.0 ) [0.8,1.0) 
 [ 1.0 , + ∞ ) [1.0,+\infty) 

 Memecoin # 
 24,988 
 5,265 
 3,315 
 2,991 
 2,756 
 2,155 

 Percentage 
 60.26% 
 12.70% 
 7.99% 
 7.21% 
 6.65% 
 5.20% 

 Figure 2 : Examples of a low-risk memecoin and two manipulated memecoins. For memecoin (b) and (c), the price move trajectories are artificial and controlled by manipulators with pre-programmed bots, and can therefore be readily identified by humans. 

 Manual label : A short time window allows min_price_ratio to capture unambiguous insider sell-offs that occur shortly after migration, but is insufficient to capture cases where the dump unfolds over a longer horizon. A typical example is that insiders actively control prices to keep price artificially high through recurring sell-buy cycles, as illustrated in Figure  2 (b) and (c). To capture these cases that the statistical indicator alone cannot cover, we introduce a second layer of manual annotation: for each memecoin with min_price_ratio ≥ \geq 0.5, we use the memecoin trading interface GMGN to inspect each memecoin’s full post-migration price-volume trajectory and screen whether it is manipulated. Among 9,471 such memecoins, 37.5% are labeled as manipulated.

 This two-layer design balances annotation effort with coverage: the statistical indicator captures the bulk of clearly high-risk memecoins at scale, leaving only the ambiguous cases for human inspection. Finally, we introduce a default risk-level categorization, which can be easily configured depending on what level of risks that researchers aim to detect:

 Table  6 reports the label distribution, from which we observe that the majority of tokens (84.13%) fall into the high-risk region.

 Table 6 : Statistics of annotation. 

 Risk Level 
 High 
 Medium 
 Low 

 Memecoin # 
 34,890 
 4,702 
 1,878 

 Percentage 
 84.13% 
 11.34% 
 4.53% 

### 3.6 Findings

 Based on the collected dataset, we observe that high-risk memecoins exhibit distinct patterns during the launchpad sale.

 Concentrated early accumulation: First, as shown in Figure  3 (e) and (f), the first buyers of high-risk tokens accumulated a much larger share of the supply than medium- and low-risk memecoins. According to statistics, the first 10 and 20 buyers of high-risk tokens hold 17 and 19 percentage points more of the supply than those of low-risk tokens. Consequently, when they reach the migration point, high-risk tokens tend to exhibit more concentrated holding distributions, as shown in Figure  3 (g).

 Faster, thinner sales: Second, since a substantial portion of the high-risk token supply has already been acquired by early buyers, it is easier and faster for high-risk tokens to reach the migration requirement. As a result, high-risk memecoin launches tend to have shorter time spans, as shown in Figure  3 (a), and fewer buy transactions as shown in Figure  3 . Meanwhile, the average buy volume of high-risk memecoins is much larger than that of low-risk memecoins, shown in Figure  3 (d), and the number of holders at the migration point is smaller, as shown in Figure  3 (b).

 Bundle-revealed concealment: Finally, in Figure  3 (h), we re-calculate the top-10 holding percentage after grouping shares into bundled accounts controlled by same users. Comparing Figure  3 (g) and (h), we observe that the median holding percentages increase by 24, 9, and 6 percentage points for high-, medium-, and low-risk tokens, respectively. This suggests that insiders of high-risk tokens are more likely to use bundled accounts to conceal their true holding concentration.

 Figure 3 : High-risk memecoins exhibit shorter launchpad sale durations (a), fewer holders (b), and fewer buy transactions (c), while each buy involves larger token volumes (d). These statistics results from early buyers accumulating a large share of the token supply (e, f), highly concentrated holdings, which is more pronounced after bundle identification (g, h). 

## 4 High-Risk Memecoin Detection

 We introduce a new detection task that predicts whether a newly migrated memecoin is high risk after migration. For this task, we label high-risk memecoins as category 1, and medium- and low-risk memecoins as category 0 for binary classification. In our experiments, we exclude memecoins with a launchpad sale duration shorter than one minute or fewer than 100 holders. The rule filters out 19,835 (47.8%) memecoins with 95% of them flagged as high-risk. This filtering mirrors simple screening rules commonly used by traders to discard very low-quality memecoins, and also helps mitigate class imbalance. Table  7 summarizes the statistics of the dataset used in our task.

 Objective function : We use a class-weighted binary cross-entropy loss:

 ℒ ( θ ) = − ∑ i = 1 N [ w 1 y i log p θ ( x i ) + w 0 ( 1 − y i ) log ( 1 − p θ ( x i ) ) ] , \mathcal{L}(\theta)=-\sum_{i=1}^{N}\big[w_{1}\,y_{i}\log p_{\theta}(x_{i})+w_{0}\,(1-y_{i})\log(1-p_{\theta}(x_{i}))\big], 

 where w 1 w_{1} and w 0 w_{0} are class weights chosen to be inversely proportional to the number of samples in each class. This ensures that the minority class receives proportionally more weight during training, preventing the model from being dominated by the majority class.

 Table 7 : Statistics of the subsampled dataset for experiments 

 Risk Level 
 Memecoin # 
 Percentage 
 Label 

 High 
 16,048 
 74.18% 
 1 

 Normal 
 5,587 
 25.82% 
 0 

### 4.1 Experimental Setup

 We split the dataset chronologically by each memecoin’s creation time into training and testing sets at a 7:3 ratio. For all the approaches, we tune hyperparameters using five-fold cross-validation on the training set, and report the average test performance over five independent runs.

 Metrics: We adopt precision, recall, and F1 scores for both classes and macro averaging to provide an overall view of model performance. Since accuracy is unreliable under class imbalance, we employ the Area Under the Precision-Recall Curve (AUPRC) to evaluate the model’s ability to distinguish high-risk from non-high-risk tokens under class imbalance. A higher AUPRC indicates that the model maintains high precision and recall simultaneously under skewed class distributions.

 Baselines: We evaluate two model families: (i) tabular models on Groups 1–4, including Logistic Regression (LR), Random Forest (RF)  ( Breiman, 2001 ) , LightGBM  ( Ke et al., 2017 ) , XGBoost  ( Chen and Guestrin, 2016 ) , and Multi-Layer Perceptron (MLP); and (ii) time-series model on Group 5 (time-series), including TCN  ( Bai, 2018 ) , LSTM  ( Hochreiter and Schmidhuber, 1997 ) , GRU  ( Cho et al., 2014 ) and Transformer encoder  ( Vaswani et al., 2017 ) . Hyperparameters are in Appendix  A.2 .

 We do not adopt graph models because our task is memecoin-level detection, not account-level tasks such as Sybil detection. Although bundle traces are relational at the account level (forming fully connected subgraphs), we have distilled them into memecoin-level statistical features (feature group 4) that reveal the true holding concentration. The ablation in Section  4.3 confirms that this distillation captures the predictive signal in bundle structure.

 Table 8 : Performance comparison on high-risk memecoin detection. 

 Model 
 AUPRC 
 Label=0 (normal) 
 Label=1 (high-risk) 
 Macro 

 Precision 
 Recall 
 F1 
 Precision 
 Recall 
 F1 
 Precision 
 Recall 
 F1 

 Random 
 0.2589 
 0.2589 
 0.2589 
 0.2589 
 0.7411 
 0.7411 
 0.7411 
 0.5000 
 0.5000 
 0.5000 

 LR 
 0.5338 
 0.5122 
 0.5441 
 0.5277 
 0.8358 
 0.8175 
 0.8265 
 0.6740 
 0.6808 
 0.6771 

 RF 
 0.5688 
 0.5444 
 0.5766 
 0.5600 
 0.8477 
 0.8300 
 0.8387 
 0.6960 
 0.7033 
 0.6994 

 XGBoost 
 0.5636 
 0.5264 
 0.5482 
 0.5371 
 0.8385 
 0.8263 
 0.8323 
 0.6824 
 0.6872 
 0.6847 

 LGBM 
 0.5642 
 0.5360 
 0.5452 
 0.5406 
 0.8388 
 0.8337 
 0.8363 
 0.6874 
 0.6895 
 0.6884 

 MLP 
 0.5729 
 0.5450 
 0.5695 
 0.5570 
 0.8459 
 0.8325 
 0.8391 
 0.6954 
 0.7010 
 0.6981 

 GRU 
 0.4972 
 0.4913 
 0.5186 
 0.5046 
 0.8270 
 0.8108 
 0.8189 
 0.6567 
 0.6680 
 0.6613 

 LSTM 
 0.5023 
 0.4895 
 0.5393 
 0.5132 
 0.8317 
 0.8019 
 0.8165 
 0.6606 
 0.6706 
 0.6649 

 TCN 
 0.4844 
 0.4847 
 0.5074 
 0.4958 
 0.8236 
 0.8100 
 0.8167 
 0.6542 
 0.6587 
 0.6563 

 Transformer 
 0.4841 
 0.4658 
 0.4920 
 0.4786 
 0.8174 
 0.8013 
 0.8093 
 0.6416 
 0.6466 
 0.6439 

 MLP+RF 
 0.5804 
 0.5572 
 0.5701 
 0.5636 
 0.8473 
 0.8404 
 0.8438 
 0.7023 
 0.7052 
 0.7037 

 MLP+LGBM 
 0.5821 
 0.5561 
 0.5683 
 0.5622 
 0.8467 
 0.8402 
 0.8435 
 0.7014 
 0.7043 
 0.7028 

 MLP+LSTM 
 0.5827 
 0.5490 
 0.5730 
 0.5607 
 0.8466 
 0.8427 
 0.8446 
 0.6958 
 0.7079 
 0.7027 

 Table 9 : Feature ablation study. Group 1, 2, 3, 4 corresponds to contextual information (Ctx), holding concentration (Hold), market activity (Mkt), and bundle statistics (Bnd). 

 Feature 
 AUPRC 
 Label=0 
 Label=1 
 Macro 

 Prec. 
 Rec. 
 F1 
 Prec. 
 Rec. 
 F1 
 Prec. 
 Rec. 
 F1 

 Full 
 0.5729 
 0.5450 
 0.5695 
 0.5570 
 0.8459 
 0.8325 
 0.8391 
 0.6954 
 0.7010 
 0.6981 

 – Ctx 
 0.5567 
 0.5216 
 0.5565 
 0.5385 
 0.8400 
 0.8202 
 0.8300 
 0.6808 
 0.6883 
 0.6842 

 – Hold 
 0.5693 
 0.5358 
 0.5582 
 0.5468 
 0.8420 
 0.8296 
 0.8358 
 0.6889 
 0.6939 
 0.6913 

 – Mkt 
 0.5369 
 0.5165 
 0.5452 
 0.5305 
 0.8366 
 0.8202 
 0.8283 
 0.6766 
 0.6827 
 0.6794 

 – Bnd 
 0.5451 
 0.5251 
 0.5492 
 0.5369 
 0.8349 
 0.8287 
 0.8318 
 0.6800 
 0.6890 
 0.6844 

 – Hold&Bnd 
 0.5268 
 0.5048 
 0.5257 
 0.5151 
 0.8304 
 0.8183 
 0.8243 
 0.6676 
 0.6720 
 0.6697 

### 4.2 Performance Comparison

 We evaluate existing approaches and report their performance in Table  8 , where we make several observations: (i) Tabular feature-based models achieve better performance compared with time-series models, suggesting that designed features are more informative for detecting high-risk memecoins than pure time-series of price and trading volumes. (ii) Among the tabular models, MLP achieves the best performance, likely due to its ability to implicitly combine multiple features and capture higher-order interactions beyond the original feature set. (iii) Among time-series models, more complex architectures such as Transformers do not achieve the best performance, whereas LSTM performs the best. We conjecture that this is because the short and noisy trading sequences lack the long-range dependencies that Transformers are designed to exploit.

### 4.3 Feature Ablation Study

 To measure the contribution of features, we iteratively remove each feature group and report the results in Table  9 . We first observe that removing any feature group results in a performance drop, indicating that the designed features provide complementary information. Second, removing Group 3 (market activity) leads to the largest performance degradation. This observation is consistent with the feature importance scores obtained from the RF model (see Figure  4 in Appendix  A.1 ), where features in the market activity group receive the highest importance values. Moreover, groups 2 and 4 both capture holding concentration, but Group 4 is computed after leveraging bundle traces to reveal true ownership concentration. Consequently, removing Group 4 results in a larger performance drop than removing Group 2. Since these groups capture complementary aspects of holding concentration, removing both leads to a substantial performance degradation.

### 4.4 Application: Memecoin Selection

 To assess whether risk detection models can reduce financial loss in practice, we simulate a simple memecoin selection strategy by ranking tokens based on predicted risk scores in descending order and selecting the top- k k candidates. For each selected memecoin, we use the price at migration as the purchase price and compute the average loss by randomly sampling 100 selling timestamps within the following hour. We evaluate this strategy on the test set and report the results in Table  10 . Precision measures the proportion of non-high-risk memecoins among the selected tokens, while loss denotes the percentage loss incurred when investing one unit of capital. As shown, random selection leads to losses exceeding 60%, whereas model-guided selection reduces losses to around 30%, despite the models not being optimized for loss minimization. Among all approaches, MLP achieves the best performance, reducing financial loss by 34 percentage points. These results demonstrate that MELT provides practical value for real-world loss mitigation.

 Table 10 : Performance of memecoin selection. 

 Model 
 Top-100 
 Top-200 

 Precision 
 Loss (%) 
 Precision 
 Loss (%) 

 w.o. model 
 0.2540 
 60.71 
 0.2650 
 64.84 

 LR 
 0.7000 
 34.06 
 0.6200 
 36.50 

 RF 
 0.7600 
 30.34 
 0.7300 
 33.72 

 XGBoost 
 0.7500 
 31.45 
 0.7400 
 33.15 

 LGBM 
 0.7400 
 31.99 
 0.7250 
 34.15 

 MLP 
 0.8000 
 26.64 
 0.7550 
 31.47 

## 5 Related Work

 Rug Pull Schemes. Rug pull refers to an exit scam pattern on blockchain, where token creators initially provide liquidity to a token pair on a DEX, attract investor trading activity, and later abruptly remove the liquidity, draining the pool of valuable assets and rendering the token worthless. The attack is achieved via the creator’s full control over liquidity pool tokens. Rug pulls have been the subject of extensive analysis in the blockchain security community. Cernera et al.  ( Cernera et al., 2023 ) conduct a longitudinal analysis of over 1.3 million tokens on Ethereum and BNB Smart Chain, introducing the notion of 1-day rug pulls, where a token is listed and drained within 24 hours. Their methodology relies on liquidity pool event patterns and identifies sniper bots that assist in early exploitation. Mazorra et al.  ( Mazorra et al., 2022 ) build a supervised classifier using blockchain and social features, showing that most rug pulls are initiated by wallets with prior history of creating disposable tokens. Yaremus et al.  ( Yaremus et al., 2025 ) construct a taxonomy of exit scams and propose an automated labeling pipeline based on on-chain liquidity events. Other datasets like SolRPDS  ( Alhaidari et al., 2024 ) provide curated rug pull samples on Solana to facilitate model training.

 Pump-and-dump Schemes. Pump-and-dump campaigns coordinate buying to create a short-lived price spike that enables early insiders to sell at inflated prices  ( Hu et al., 2023a ; Li et al., 2021 ; Xu and Livshits, 2019 ; La Morgia et al., 2021 ) . Prior work has mainly studied such behavior in centralized exchanges (CEXs) or order-book markets, where transaction-level traces are not publicly accessible and holdings are custodial rather than address-based, making it difficult to reconstruct fine-grained trading traces or analyze multi-account behaviors  ( Kamps and Kleinberg, 2018 ; Hu et al., 2023a ) . Moreover, order-book price dynamics are driven by buy orders lifting the ask side and subsequent sell orders consuming liquidity. In contrast, launchpad-based memecoin markets sell tokens via a bonding-curve program and then migrate liquidity to a DEX pool, which confers a much stronger first-mover advantage to early buyers and can amplify post-migration losses when these low-cost positions unwind.

## 6 Discussion

 Limitations. Our study focuses on memecoins that successfully migrated to a DEX. While migrated memecoins attract the vast majority of trading attention, unmigrated memecoins can still draw retail buyers during the launchpad sale and cause financial losses at smaller scales. Extending MELT to cover the long tail of unmigrated launches is left as future work.

 Utility Outlook. Beyond studying high-risk memecoins, MELT offers broader utility in the crypto ecosystem. For example, the bundle trace data enables research on linking accounts belonging to the same entities, revealing hidden coordination behaviors on-chain such as Sybil or money laundering detection  ( Hu et al., 2025 ; Hu et al., 2023b ; Béres et al., 2021 ) . Both the dataset and the released data science pipeline can be extended to continuously collect newly launched memecoins, perform large-scale transaction collection and parsing, and identify bundled or coordinated accounts. The rapid rise of the Solana ecosystem introduces new research challenges in large-scale memecoin markets, making MELT a timely resource for future research and the ML community.

## 7 Conclusion

 The rise of launchpads has transformed how memecoins are issued, and also created a new class of threat whose signals lie deep within early trading behaviors. To open this problem to systematic study, we presented MELT, a behavioral trace dataset that uncovers and reconstructs launchpad-stage behavioral traces from heterogeneous on-chain and off-chain signals, and connects them to the post-migration risk level exhibited by a memecoin once it enters the public DEX. Experiments show that incorporating prediction signals learned from MELT substantially reduces investment loss, confirming it carries practical defensive value. We hope MELT contributes to the ML community as a resource for studying complex, adversarial user behaviors in real-world on-chain markets.

## References

- Alhaidari et al. (2024) 
 A. Alhaidari, B. Kalal, B. Palanisamy, and S. Sural 
 
 SolRPDS: a dataset for analyzing rug pulls in solana decentralized finance .
 
 In Proceedings of the Fifteenth ACM Conference on Data and Application Security and Privacy ,
 
 pp. 293–298 .
 
 Cited by: §5 .

- Bai (2018) 
 S. Bai 
 
 An empirical evaluation of generic convolutional and recurrent networks for sequence modeling .
 
 arXiv preprint arXiv:1803.01271 .
 
 Cited by: §4.1 .

- Béres et al. (2021) 
 F. Béres, I. A. Seres, A. A. Benczúr, and M. Quintyne-Collins 
 
 Blockchain is watching you: profiling and deanonymizing ethereum users .
 
 In 2021 IEEE international conference on decentralized applications and infrastructures (DAPPS) ,
 
 pp. 69–78 .
 
 Cited by: §6 .

- Breiman (2001) 
 L. Breiman 
 
 Random forests .
 
 Machine learning 45 ( 1 ), pp. 5–32 .
 
 Cited by: §4.1 .

- Cernera et al. (2023) 
 F. Cernera, M. La Morgia, A. Mei, and F. Sassi 
 
 Token spammers, rug pulls, and sniper bots: an analysis of the ecosystem of tokens in ethereum and in the binance smart chain ( { \{ { \{ { \{ { \{ { \{ bnb } \} } \} } \} } \} } \} ) .
 
 In 32nd USENIX Security Symposium (USENIX Security 23) ,
 
 pp. 3349–3366 .
 
 Cited by: §1 ,
 §5 .

- Chen and Guestrin (2016) 
 T. Chen and C. Guestrin 
 
 Xgboost: a scalable tree boosting system .
 
 In Proceedings of the 22nd acm sigkdd international conference on knowledge discovery and data mining ,
 
 pp. 785–794 .
 
 Cited by: §4.1 .

- Cho et al. (2014) 
 K. Cho, B. Van Merriënboer, C. Gulcehre, D. Bahdanau, F. Bougares, H. Schwenk, and Y. Bengio 
 
 Learning phrase representations using rnn encoder-decoder for statistical machine translation .
 
 arXiv preprint arXiv:1406.1078 .
 
 Cited by: §4.1 .

- CoinDesk (2025) 
 CoinDesk 
 
 Pump.fun hits back at report that claimed 98% of memecoins on the platform are fraudulent .
 
 CoinDesk .
 
 Note: Accessed: 2025-11-09 
 
 External Links: Link 
 
 Cited by: §1 .

- dYdX Foundation (2024) 
 dYdX Foundation 
 
 What are bonding curves, and how do they work? .
 
 Note: https://www.dydx.xyz/crypto-learning/bonding-curve Accessed: 2025-12-08 
 
 Cited by: §2 .

- Helius Labs (2025) 
 Helius Labs 
 
 $TRUMP’s historic weekend on solana: records, trends & insights .
 
 Note: https://www.helius.dev/blog/trump-solana-memecoin-records-trends-insights Accessed: 2025-12-01 
 
 Cited by: §1 .

- Hochreiter and Schmidhuber (1997) 
 S. Hochreiter and J. Schmidhuber 
 
 Long short-term memory .
 
 Neural computation 9 ( 8 ), pp. 1735–1780 .
 
 Cited by: §4.1 .

- Hu et al. (2025) 
 S. Hu, T. Huang, F. Ilhan, S. F. Tekin, G. Eisenhauer, M. L. Loper, and L. Liu 
 
 Matching accounts on blockchain via pseudo fine-tuning of language models .
 
 ACM Transactions on Intelligent Systems and Technology .
 
 Cited by: §6 .

- Hu et al. (2023a) 
 S. Hu, Z. Zhang, S. Lu, B. He, and Z. Li 
 
 Sequence-based target coin prediction for cryptocurrency pump-and-dump .
 
 Proceedings of the ACM on Management of Data 1 ( 1 ), pp. 1–19 .
 
 Cited by: §5 .

- Hu et al. (2023b) 
 S. Hu, Z. Zhang, B. Luo, S. Lu, B. He, and L. Liu 
 
 Bert4eth: a pre-trained transformer for ethereum fraud detection .
 
 In Proceedings of the ACM Web Conference 2023 ,
 
 pp. 2189–2197 .
 
 Cited by: §6 .

- Kamps and Kleinberg (2018) 
 J. Kamps and B. Kleinberg 
 
 To the moon: defining and detecting cryptocurrency pump-and-dumps .
 
 Crime Science 7 ( 1 ), pp. 1–18 .
 
 Cited by: §5 .

- Ke et al. (2017) 
 G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T. Liu 
 
 Lightgbm: a highly efficient gradient boosting decision tree .
 
 Advances in neural information processing systems 30 .
 
 Cited by: §4.1 .

- La Morgia et al. (2021) 
 M. La Morgia, A. Mei, F. Sassi, and J. Stefa 
 
 The doge of wall street: analysis and detection of pump and dump cryptocurrency manipulations .
 
 arXiv preprint arXiv:2105.00733 .
 
 Cited by: §5 .

- Li et al. (2021) 
 T. Li, D. Shin, and B. Wang 
 
 Cryptocurrency pump-and-dump schemes .
 
 Available at SSRN 3267041 .
 
 Cited by: §5 .

- Li et al. (2025) 
 Y. Li, N. Yao, Y. Huo, and W. Cai 
 
 Trust dynamics and bot-driven responses: an approach to rug pulls in solana meme coin markets .
 
 In Proceedings of the 17th ACM Web Science Conference 2025 ,
 
 pp. 106–116 .
 
 Cited by: §1 .

- Mazorra et al. (2022) 
 B. Mazorra, V. Adan, and V. Daza 
 
 Do not rug on me: zero-dimensional scam detection .
 
 arXiv preprint arXiv:2201.07220 .
 
 Cited by: §1 ,
 §5 .

- Research (2025) 
 G. Research 
 
 The state of memecoins .
 
 Note: Accessed: 2025-11-07 
 
 External Links: Link 
 
 Cited by: §1 .

- Smithii (2025) 
 Smithii 
 
 How to graduate token on pumpfun: everything you need to know .
 
 Note: https://smithii.io/en/graduate-token-pump-fun/ Accessed: 2025-12-01 
 
 Cited by: §2 .

- [23] 
 Solana Documentation 
 
 Accounts — solana core concepts .
 
 Note: https://solana.com/docs/core/accounts Accessed: 2025-12-08 
 
 Cited by: §2 .

- [24] 
 Solana Documentation 
 
 Transactions — solana core concepts .
 
 Note: https://solana.com/docs/core/transactions Accessed: 2025-12-08 
 
 Cited by: §2 .

- Uniswap Labs (2018) 
 Uniswap Labs 
 
 Uniswap v1 protocol overview .
 
 Note: https://docs.uniswap.org/contracts/v1/overview Accessed: 2025-12-08 
 
 Cited by: §2 .

- Vaswani et al. (2017) 
 A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and I. Polosukhin 
 
 Attention is all you need .
 
 Advances in neural information processing systems 30 .
 
 Cited by: §4.1 .

- Voinea (2025) 
 D. V. Voinea 
 
 Pump. fun and meme-coins: a case study in the legal commodification of ponzi-like tokenomics .
 
 Annals of the University of Craiova for Journalism, Communication and Management 11 ( 1 ), pp. 15–38 .
 
 Cited by: §1 .

- Wikipedia (2025) 
 Wikipedia 
 
 $Trump (cryptocurrency) .
 
 Note: https://en.wikipedia.org/wiki/$Trump Accessed: 2025-12-01 
 
 Cited by: §1 .

- Xu and Livshits (2019) 
 J. Xu and B. Livshits 
 
 The anatomy of a cryptocurrency { \{ pump-and-dump } \} scheme .
 
 In 28th USENIX Security Symposium (USENIX Security 19) ,
 
 pp. 1609–1625 .
 
 Cited by: §5 .

- Yaremus et al. (2025) 
 D. Yaremus, J. Li, A. Kalacheva, I. Vodolazov, and Y. Yanovich 
 
 Detecting rug pulls in decentralized exchanges: machine learning evidence from the ton blockchain .
 
 arXiv preprint arXiv:2509.01168 .
 
 Cited by: §1 ,
 §5 .

## Appendix A Technical appendices and supplementary material

### A.1 Feature Importance Study

 In Figure  4 , we report the importance scores of the 122 features produced by the RF model. As shown, features from Group 3 (market activity) and Group 4 (bundle statistics), highlighted in green and red, account for the highest importance, which is consistent with the feature ablation results in Table  9 . 

 Figure 4: Feature importance score calculated by the RF model. Blue marks the contextual information features, orange marks holding concentration features, green marks market activity features, and red marks the bundle statistic features. 

### A.2 Hyper-parameter Settings

 For the high-risk detection task, competitors are configured as follows: LR serves as a linear baseline with L2 regularization and a fixed regularization strength of 1.0. For tree-based models, RF is implemented with 800 trees and a maximum depth of 16, while other parameters follow standard practice. XGBoost uses 800 trees with a maximum depth of 6 and a learning rate of 0.05. LightGBM is trained with 2000 boosting iterations and a learning rate of 0.02, with the maximum number of leaves set to 64 and subsampling applied to control model complexity. MLP consists of two fully connected hidden layers with 512 and 256 units, respectively. For time-series models, both GRU, LSTM and Transformer classifiers are configured with two stacked layers and a hidden dimension of 256. The TCN consists of 8 dilated convolutional blocks (kernel size 9, dilations [1, 2, 4, …, 128]. For all neural networks, each layer is followed by batch normalization, ReLU activation, and dropout with a rate of 0.2.
