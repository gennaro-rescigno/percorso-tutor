# arxiv-2512.11850-memecoin-phenomenon

Fonte: https://arxiv.org/html/2512.11850v3

The Memecoin Phenomenon:An In-Depth Study of Solana’s Blockchain Trends 

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

 License: arXiv.org perpetual non-exclusive license

arXiv:2512.11850v3 [cs.CY] 18 Dec 2025

# The Memecoin Phenomenon:
 An In-Depth Study of Solana’s Blockchain Trends

 Davide Mancino
 
 Affiliation:  University of Milano-Bicocca
 Department of Informatics, Systems, and Communication (DISCo) 
 Viale Sarca 336, Edificio U14, 20126 Milano, Italy 
 davide.mancino@unimib.it 

###### Abstract

 This paper analyzes the emerging memecoin phenomenon on the Solana blockchain, focusing on the Pump.fun platform during Q4 2024. Using on-chain data, it is explored how retail-focused token creation platforms are reshaping blockchain ecosystems and influencing market participation. This study finds that Pump.fun accounted for up to 71.1% of all tokens minted on Solana and contributed 40–67.4% of total DEX transactions. Despite this activity, fewer than 2% of tokens successfully transitioned to major decentralized exchanges, highlighting a highly speculative market structure. The platform experienced rapid growth, with daily active users rising from 60,000 to peaks of 260,000, underscoring strong retail adoption. This reflects a broader shift towards accessible, socially-driven market participation enabled by memecoins. However, while memecoins lower entry barriers and encourage retail engagement, they introduce significant risks. The volatile and speculative nature of these platforms raises concerns about long-term sustainability and the resilience of the blockchain ecosystem. These findings reveal the dual impact of memecoins: they democratize token creation and alter market dynamics but may jeopardize market efficiency and stability. This paper highlights the need to critically assess the implications of retail-driven speculative trading and its potential to disrupt emerging blockchain economies.

###### Index Terms: 
Solana, memecoin, speculation, blockchain, DEX, Pump.fun.

## I Introduction 

 The blockchain ecosystem has witnessed several transformative waves of innovation since its inception. DeFi protocols  [ 1 ] , Blockchain Online Social Media (BOSM)  [ 2 , 3 ] , Maximal Extractable Value (MEV) and its implications  [ 4 ] and more recently, metaverse technologies have been explored  [ 5 ] .
Against this backdrop, a new phenomenon has emerged: the rise of retail-focused token creation platforms, particularly in the memecoin sector. These platforms represent a synthesis of previous trends, combining DeFi’s accessibility, BOSM’s social dynamics, and elements of virtual world engagement. This evolution raises important questions about speculative behavior, and the democratization of blockchain-based financial instruments.

 This paper examines this phenomenon through an empirical analysis of Pump.fun , a leading memecoin platform on the Solana blockchain. By analyzing platform metrics, user behavior, and market dynamics during Q4 2024, the aim is to understand how these new platforms are reshaping blockchain ecosystems and influencing user participation in cryptocurrency markets. This research contributes to the growing body of literature on blockchain market dynamics by examining how retail-focused platforms are creating new paradigms for token creation, trading, and value extraction.

 The remainder of this paper is organized as follows: Section II provides background information on the Solana blockchain, while Section III explores the concept of memecoins and their significance. Section IV introduces Pump.fun and its role in the ecosystem. Section V presents the detailed analysis of market behavior and dynamics. Section VI examines economic implications and speculative behavior. Finally, Section VII describes related works and Section VIII concludes the article with key insights and future research directions.

## II Solana Blockchain 

 Solana’s blockchain architecture is distinguished by its high throughput and low latency, achieved through a unique consensus mechanism that combines Proof-of-History (PoH) with Proof-of-Stake (PoS). PoH serves as a cryptographic clock, allowing nodes to agree on the time order of events without extensive communication, thereby enhancing efficiency and scalability. This innovation allows Solana to process thousands of transactions per second, significantly outperforming many other blockchains  [ 6 ] .

 Positioned as a high-performance blockchain, Solana addresses scalability issues that have hindered other blockchains. Its architecture supports decentralized applications (dApps) and smart contracts, attracting a diverse range of projects and users. The low transaction fees and rapid processing times of the platform have solidified its reputation as a viable solution for various blockchain applications  [ 7 ] .

 The Solana Program Library (SPL) Token program is Solana’s on-chain standard for creating and managing tokens, both fungible and non-fungible  [ 8 ] . It provides a comprehensive framework that ensures compatibility across the Solana ecosystem, enabling high-performance and secure token operations that leverage Solana’s speed and parallel processing capabilities. A key feature of SPL tokens is their support for atomic transfers, which allows complex token interactions within a single transaction.

## III Memecoins 

 Memecoins are cryptocurrencies inspired by internet memes or trends, often characterized by their humorous nature and the enthusiastic communities that support them. Unlike traditional cryptocurrencies, which may offer specific utilities or technological advancements, memecoins typically lack inherent value or utility, relying instead on their viral appeal and community engagement.

 A notable example is Dogecoin (DOGE), created in December 2013 by software engineers Billy Markus and Jackson Palmer as a joke, inspired by the viral “Doge” meme featuring a Shiba Inu dog  [ 9 ] . Despite its origins, Dogecoin has gained a dedicated following and has been adopted as a payment method by some companies  [ 10 ] .

 Similarly, Shiba Inu (SHIB) emerged as a memecoin aiming to capitalize on the popularity of Dogecoin. It has developed a loyal community and has seen substantial market activity, with its value largely driven by social media hype and community engagement  [ 11 ] .

 In 2023, Pepe Coin (PEPE), inspired by the meme “Pepe the Frog”, gained attention in the cryptocurrency market. Embracing its identity as a memecoin, PEPE reached a market cap of $1.6 billion in mid-2023, sparking a memecoin frenzy  [ 12 ] .

 The memecoin phenomenon has been analyzed in various studies, highlighting the cultural and economic impacts of memecoins within the blockchain ecosystem. For instance, Krause (2024)  [ 13 ] examines the socio-economic implications of memecoins, emphasizing their role in digital culture and speculative investment behaviors. Long (2024)  [ 14 ] explores the multimodal nature of memecoins, analyzing how visual and textual elements contribute to their virality and market performance. Additionally, Kim (2023)  [ 15 ] investigates the influence of social media platforms, particularly Twitter, on the proliferation and market dynamics of memecoins, demonstrating the significant impact of online communities in shaping the memecoin landscape.

 These studies collectively provide a comprehensive understanding of the memecoin phenomenon, shedding light on the interplay between internet culture, social media, and cryptocurrency markets.

## IV Pump.fun: A Memecoin Platform on Solana 

 Pump.fun is a platform built on the Solana blockchain launched in January 2024 that enables users to create and trade tokens instantly. This user-friendly interface has democratized token creation, allowing anyone to launch a memecoin within minutes  [ 16 ] .

 A distinctive feature of Pump is its “graduated tokens” system. Tokens created on the platform can “graduate” to decentralized exchanges like Raydium, where they become available for broader trading. This graduation process involves meeting specific criteria, such as achieving a certain level of trading volume and community engagement, which helps filter out low-quality tokens and promotes more promising projects  [ 17 ] .

 Pump also ensures token safety by preventing rug pulls through a fair-launch mechanism. All tokens created on the platform undergo a launch process with no presale or team allocation. Users can buy tokens directly on the bonding curve (a pricing model where the token price increases as more tokens are purchased) and sell at any time to realize profits or losses. Once the market cap reaches $100k, $17k of liquidity is deposited into Raydium and permanently burned, promoting scarcity and price stability  [ 18 ] .

 Since its inception, Pump.fun has experienced significant growth. By November 2024, the platform had facilitated the creation of over 3 million tokens, averaging seven new tokens per minute, reflecting the platform’s popularity and the hype around the memecoin trend  [ 19 ] .

 Pump.fun has been a significant driver of the memecoin trend in 2024. Its ease of use and accessibility have lowered the barriers to entry for token creation, leading to an explosion of memecoins and contributing to the broader popularity of these digital assets within the cryptocurrency market  [ 20 ] .

 However, the platform has not been without controversy. In late 2024, Pump.fun faced criticism for hosting livestreams where token creators engaged in extreme actions to promote their tokens. This led to the indefinite suspension of the livestream feature following community backlash  [ 21 ] .

 Despite these challenges, Pump.fun remains a pivotal platform in the memecoin ecosystem, exemplifying the dynamic and rapidly evolving nature of blockchain-based digital assets.

## V Analysis of Memecoin Behavior and Market Dynamics 

 This section focuses on detailing the data utilized and the analyses performed.

### V-A Data Collection and Methodology 

 This research presents an analysis of Pump.fun’s market dynamics during the fourth quarter (Q4) of 2024, spanning October through December. The selection of this time period is particularly significant as it captures both the platform’s explosive growth phase and its subsequent maturation, providing valuable insights into the evolution of retail-focused token creation platforms.

 Dune [ 22 ] was chosen as the primary data source due to its comprehensive coverage of the Solana blockchain. This analysis focuses on three data tables, each offering unique perspectives on the ecosystem’s dynamics.

 The first is the tokens_solana.transfers table, which tracks all token transfer events on the Solana blockchain. Provide crucial information, including sender and receiver addresses, transaction amounts, and timestamps. This data allows us to follow the entire lifecycle of tokens, from their creation through various trading phases, and to their listing on major decentralized exchanges (DEXes).

 Next, the dex_solana.trades table, offers comprehensive details about trading activities across all decentralized exchanges on Solana. It captures key trade-level data such as exact amounts, prices, and the specific DEX programs involved.

 The third essential component is the solana.instruction_calls table. This table records all program interactions on the Solana blockchain.

### V-B Platform Dominance in Token Creation 

 This analysis aims to understand platform dominance in the creation of new tokens.
The data used in this study was extracted using SQL queries executed in the Dune Analytics Solana blockchain token transfer database. Minting transactions related to Pump.fun and Moonshot (another platform for buying and selling memecoins) [ 23 ] were identified by filtering for their respective executing accounts ( outer_executing_account ). The query aggregated the daily count of minted tokens between October 1, 2024, and December 31, 2024. Tokens minted by other platforms were gathered by excluding minting transactions associated with Pump.fun and Moonshot.
The results were combined to provide a comparative overview, underscoring Pump.fun’s dominance over competing platforms.
A thorough examination of the data, visualized in Figure  2 and Figure  2 , reveals that Pump.fun has achieved unprecedented superiority in token creation compared to its competitors, including other memecoin platforms such as Moonshot .

 The platform’s dominance is most strikingly illustrated by its peak performance of 69,046 token mints in a single day, representing an extraordinary 71.1% of all tokens minted on the Solana blockchain during that period.

 Fig. 1: Daily token creation by various platforms on Solana. 

 Fig. 2: Percentage of daily token creation by various platforms on Solana. 

### V-C DEX Transaction Analysis 

 This section investigates Pump.fun’s competitive standing within the Solana ecosystem by analyzing decentralized exchange (DEX) transaction data. Specifically, the Solana DEX platforms analyzed include Raydium [ 24 ] , Meteora [ 25 ] , Orca [ 26 ] , Lifinity [ 27 ] , Phoenix [ 28 ] , and Pump.fun.
The data, visualized in Figure  4 and Figure  4 , highlights Pump.fun’s strong market presence despite its relatively recent entry.

 The data for this analysis was extracted using SQL queries executed on the Dune Analytics Solana blockchain DEX trade database. The query identifies DEX trades conducted between October 1, 2024, and Decemebre 31, 2024, aggregating the daily number of transactions by project.

 Pump.fun consistently accounts for 15% to 25% of total DEX activity, a notable achievement considering the competition from long-established exchanges.

 Daily transactions serves as a critical indicator of Pump.fun’s market penetration, with the platform consistently processing between 2 and 4 million transactions each day. This level of activity further solidifies its position among the top-tier exchanges within the Solana ecosystem.

 Fig. 3: DEX daily transactions. 

 Fig. 4: Percentage of DEX daily transactions. 

### V-D Pump.fun Related Transactions 

 To comprehensively assess Pump.fun’s impact on the Solana ecosystem, a metric was employed that encompasses all transactions involving tokens initially created on Pump.fun, irrespective of their current trading platform, as depicted in Figure  6 and Figure  6 .

 The methodology for this metric involves:

- 1. 
 
 Maintaining a comprehensive registry of all tokens created on Pump.fun by analyzing mint instructions in the blockchain data.

- 2. 
 
 Tracking these tokens across all decentralized exchanges (DEXs) by matching token addresses in trade events.

- 3. 
 
 Aggregating transaction data by distinguishing between tokens generated on Pump.fun and those created elsewhere.

 Fig. 5: Daily transaction trades of tokens created on Pump.fun. 

 Fig. 6: Percentage of daily DEX transactions involving Pump.fun-created tokens. 

 This analysis reveals that transactions involving Pump.fun-created tokens constitute between 40% and 67.4% of daily DEX transactions. This significant proportion indicates substantial secondary market activity for tokens originating from Pump.fun, underscoring the platform’s considerable influence within the Solana ecosystem.

### V-E Volume Analysis and Retail Focus 

 The volume analysis of the Pump.fun related transactions reveals a dichotomy between transaction counts and trading volumes. As illustrated in Figure  8 and Figure  8 , Pump.fun-related volume demonstrates distinctive characteristics that provide deep insights into the platform’s market position and user base composition.

 Fig. 7: Daily trading volume of tokens created on Pump.fun (log scale, USD). 

 Fig. 8: Percentage of daily trading volume of tokens created on Pump.fun. 

 When examining the raw volume data, it is observed that Pump.fun-related trading rarely exceeds 50% of total DEX volume, despite the platform’s dominant position in transaction counts. This apparent discrepancy illuminates a fundamental characteristic of the platform’s market position: its pronounced retail orientation.

### V-F Token Graduation Analysis 

 The analysis of token graduation rates provides critical insights into the quality and sustainability of tokens created on Pump.fun.
The SQL query used to analyze token graduation rates identifies tokens created on Pump.fun and tracks their progression to Raydium. It first selects tokens minted on Pump.fun between October 1, 2024, and December 31, 2024. Then, it identifies tokens that have been withdrawn from Pump.fun, indicating their graduation to Raydium. The query aggregates this data to determine the daily number of tokens created on Pump.fun and the daily number of tokens that have graduated to Raydium, calculating the graduation percentage for each day.
By examining graduation events, as visualized in Figures  10 and  10 , patterns in token lifecycle dynamics and platform efficiency are uncovered.

 The graduation process itself merits detailed examination. As discussed in Section IV , for a token to graduate to Raydium, it must meet the successful completion of the bonding curve, demonstrating sufficient demand and liquidity.

 Fig. 9: Daily graduated tokens on Pump.fun. 

 Fig. 10: Percentage of daily graduated tokens relative to daily created tokens on Pump.fun. 

 The analysis of token graduation rates reveals that only a small fraction of tokens created on Pump.fun successfully meet the criteria for listing on Raydium. Specifically, the graduation rate peaks at less than 2%, indicating that only a limited number of tokens generated on Pump.fun manage to attract sufficient demand and liquidity.

### V-G User Engagement and Platform Growth 

 The query used for this analysis tracks the daily count of unique user signers for transactions on Pump.fun.
As shown in Figure  11 , the platform’s user base demonstrated extraordinary growth, with unique trading addresses rising from around 60,000 in early October to remarkable peaks of 260,000 in November and 224,000 in December. This figure highlight a significant increase in user activity, suggesting a growing adoption and engagement with the platform. The consistent rise in users over the study period reflects the platform’s increasing popularity, making it an increasingly important player in the Solana ecosystem.

 Fig. 11: Daily User growth on Pump.fun. 

## VI Economic Implications and Speculative Behavior 

 The analysis of Pump.fun’s ecosystem during Q4 2024 reveals striking patterns of speculative behavior, showcasing the significant influence the platform has had on Solana’s blockchain market. The dominance of Pump.fun in token creation, reaching peaks of 71% of all Solana tokens minted, signals a major shift in retail trader participation in cryptocurrency markets. This level of engagement suggests that platforms like Pump.fun have democratized the process of token creation, enabling a larger pool of retail investors to engage in speculative activities that were previously dominated by more sophisticated actors.

 A key finding in this study is the graduation rate of tokens, with fewer than 2% reaching sufficient market capitalization for listing on Raydium. This low graduation rate highlights a speculative market structure, where tokens are frequently minted and traded but struggle to achieve long-term sustainability. Despite high transaction frequencies, the relatively low trading volumes suggest that many traders are prioritizing short-term opportunities over long-term value creation. This trend is indicative of a retail-driven market where traders focus on quick profits rather than evaluating the intrinsic value of the tokens they trade. The ecosystem is largely driven by speculative behavior, which thrives on the volatility and uncertainty inherent to the memecoin sector.

 Moreover, Pump.fun’s ability to influence 40-67.4% of all decentralized exchange (DEX) transactions on Solana, even when considering other platforms, underscores how speculation within niche sectors like memecoins can drive broader market dynamics. The platform’s growth, reflected in the substantial increase in daily unique users from 60,000 to 260,000, reveals the mass appeal of speculative opportunities, even when the underlying assets often lack long-term value. These patterns suggest that the platform has capitalized on a growing trend of social coordination among traders, where collective market actions—driven by rumors, trends, and speculation—outweigh traditional market fundamentals.

 This retail-driven speculative behavior presents a stark contrast to more traditional forms of blockchain value extraction, such as the MEV (Maximal Extractable Value) strategies analyzed in the Ethereum ecosystem [ 29 ] . While MEV relies on technical sophistication, automated systems, and precise transaction ordering to extract value, memecoin speculation through platforms like Pump.fun represents a more accessible, socially-driven form of value extraction. Instead of competing on computational resources and algorithmic efficiency as in MEV scenarios, memecoin traders compete through social coordination, rapid information dissemination, and collective market movements. This fundamental difference highlights how blockchain ecosystems can support diverse forms of speculative activity, each adapted to different participant skillsets and resources.

## VII Related Work 

 This work represents the first comprehensive analysis of a memecoin creation platform and its impact on blockchain market dynamics. While previous research has explored various aspects of memecoins, including their socio-economic implications [ 13 ] and social media influence [ 15 ] , no study has directly investigated platforms dedicated to memecoin creation. The analysis builds upon research in blockchain market dynamics [ 4 ] and DeFi protocols [ 1 ] , extending these frameworks to examine how retail-focused platforms are reshaping cryptocurrency market participation through accessible token creation and trading mechanisms.

## VIII Conclusion 

 This research offers a comprehensive examination of the evolving landscape of retail-driven speculative trading on blockchain platforms, with a particular focus on Pump.fun during Q4 2024. The platform’s substantial influence in token creation—accounting for up to 71% of all tokens minted on Solana—highlights the growing trend of memecoin proliferation within the cryptocurrency markets. Retail participants now have greater access to token creation and trading. However, this shift towards accessibility raises important questions about the sustainability of the value being created.

 While the platform excels at generating initial trading activity, its low graduation rate—below 2%—suggests that the ecosystem predominantly supports short-term speculation rather than long-term value creation. This imbalance, coupled with high transaction counts but low trading volumes, indicates that the market structure is driven by frequent, smaller trades, often without sufficient regard for the fundamental value of the tokens involved. This reliance on rapid trading and speculative behavior may present risks to long-term market stability and investor confidence.

 The broader implications of this retail-driven speculative behavior are twofold. On the one hand, the growth in unique users and the high number of Pump.fun-related transactions indicate a shift towards more social, crowd-driven forms of market participation. On the other hand, this speculative frenzy risks creating a volatile market that may undermine the broader Solana ecosystem.

 Ultimately, the success of Pump.fun in fostering market engagement raises concerns about the long-term impact of platforms focused on short-term speculation. While such platforms may offer new opportunities for retail investors, the risks of market manipulation, volatility, and the creation of low-quality assets must be carefully considered.

 The challenges posed by platforms like Pump.fun highlight the broader risks within blockchain-based financial ecosystems. These risks include speculative bubbles, market instability, and the potential for retail investors to be left holding assets that ultimately lack long-term value. As the popularity of such platforms grows, it becomes crucial to develop regulatory and technical frameworks that safeguard against the dangers of unchecked speculation while encouraging responsible market participation.

## References

- [1] 
 
P. K. Ozili, “Decentralized finance research and developments around the world,” Journal of Banking and Financial Technology , vol. 6, no. 2, pp. 117–133, 2022. [Online]. Available: https://doi.org/10.1007/s42786-022-00044-x

- [2] 
 
B. Guidi and A. Michienzi, “The decentralization of social media through the blockchain technology,” in Companion Publication of the 13th ACM Web Science Conference 2021 , ser. WebSci ’21 Companion. New York, NY, USA: Association for Computing Machinery, 2021, p. 138–139. [Online]. Available: https://doi.org/10.1145/3462741.3466680

- [3] 
 
D. Mancino, B. Guidi, A. Michienzi, and M. Viviani, “Striking the balance: Evaluating content quality and reward dynamics in blockchain online social media,” IEEE Access , vol. 13, pp. 21 927–21 945, 2025.

- [4] 
 
D. Mancino, A. Leporati, M. Viviani, and G. Denaro, “Exploiting ethereum after” the merge”: The interplay between pos and mev strategies.” in ITASEC , 2023.

- [5] 
 
A. Ghosh, Lavanya, V. Hassija, V. Chamola, and A. El Saddik, “A survey on decentralized metaverse using blockchain and web 3.0 technologies, applications, and more,” IEEE Access , vol. 12, pp. 146 915–146 948, 2024.

- [6] 
 
A. Yakovenko, “Solana: A new architecture for a high performance blockchain,” 2017. [Online]. Available: https://solana.com/solana-whitepaper.pdf

- [7] 
 
S. Mishra, “Solana blockchain technology: A review,” International Journal of Informatics and Communication Technology , vol. 13, no. 2, pp. 197–205, 2024. [Online]. Available: https://ijict.iaescore.com/index.php/IJICT/article/view/20829

- [8] 
 
S. Labs, “Token program,” 2023, accessed on January, 8th, 2025. [Online]. Available: https://spl.solana.com/token

- [9] 
 
U. W. Chohan, “A history of dogecoin,” February 2021, discussion Series: Notes on the 21st Century. [Online]. Available: https://ssrn.com/abstract=3091219

- [10] 
 
Cointelegraph. (2023, March) Who accepts dogecoin? a beginner’s guide on businesses accepting doge. Accessed on January, 8th, 2025. [Online]. Available: https://cointelegraph.com/learn/articles/who-accepts-dogecoin-a-beginners-guide-on-businesses-accepting-doge

- [11] 
 
Cointelegraph. (2023, October) Dogecoin vs. shiba inu: What’s the difference? Accessed on January, 8th, 2025. [Online]. Available: https://cointelegraph.com/learn/articles/dogecoin-vs-shiba-inu

- [12] 
 
crypto.news. (2025) Early investors eye a $0.0015 token set to rival pepe with a stunning 30,000

- [13] 
 
D. Krause, “Beyond the hype: A meme coin reality check for retail investors,” Available at SSRN 4891841 , 2024.

- [14] 
 
H.-W. Long, N.-M. Wong, and W. Cai, “Bridging culture and finance: A multimodal analysis of memecoins in the web3 ecosystem,” 2024. [Online]. Available: https://arxiv.org/abs/2412.04913

- [15] 
 
J. H. Kim and H. W. Park, “Identifying networked patterns in memecoin twitter accounts using exponential random graph modeling,” IT Professional , vol. 25, no. 6, pp. 82–89, 2023.

- [16] 
 
Decrypt, “What is pump.fun? the solana meme coin factory,” 2024, accessed on January, 8th, 2025. [Online]. Available: https://decrypt.co/resources/what-is-pump-fun-the-solana-meme-coin-factory

- [17] 
 
Webopedia, “What is pump.fun? solana’s memecoin mothership,” 2024, accessed on January, 8th, 2025. [Online]. Available: https://www.webopedia.com/crypto/learn/pump-fun/

- [18] 
 
Pump.Fun. (2024) Pump.fun board. Accessed on January, 8th, 2025. [Online]. Available: https://pump.fun/board

- [19] 
 
SolanaFloor, “Total tokens created on pump.fun hits record 3 million, averaging 7 per minute since launch,” 2024, accessed on January, 8th, 2025. [Online]. Available: https://solanafloor.com/news/total-tokens-created-on-pump-fun-hits-record-3-million-averaging-7-per-minute-since-launch

- [20] 
 
The Block, “2024: The Year of Memecoins,” 2024, accessed on January, 8th, 2025. [Online]. Available: https://www.theblock.co/post/331410/2024-year-of-memecoins

- [21] 
 
Cointelegraph. (2024) Pump.fun faces backlash over harmful content on livestream feature. Accessed on January, 8th, 2025. [Online]. Available: https://cointelegraph.com/news/pump-fun-livestream-backlash-content

- [22] 
 
Dune. Dune. Accessed on January, 8th, 2025. [Online]. Available: https://docs.dune.com/home

- [23] 
 
Moonshot. Moonshot. Accessed on January, 8th, 2025. [Online]. Available: https://dexscreener.com/moonshot

- [24] 
 
Raydium, “Raydium,” https://raydium.io, accessed on January, 8th, 2025.

- [25] 
 
Meteora, “Meteora,” https://meteora.ag, accessed on January, 8th, 2025.

- [26] 
 
Orca, “Orca,” https://orca.so, accessed on January, 8th, 2025.

- [27] 
 
Lifinity, “Lifinity,” https://lifinity.io, accessed on January, 8th, 2025.

- [28] 
 
Phoenix, “Phoenix,” https://phoenix.trade, accessed on January, 8th, 2025.

- [29] 
 
D. Mancino, A. Leporati, M. Viviani, and G. Denaro, “A role and reward analysis in off-chain mechanisms for executing mev strategies in ethereum proof-of-stake,” Distrib. Ledger Technol. , Jun. 2024, just Accepted. [Online]. Available: https://doi.org/10.1145/3672405
