# arxiv-2607.02823-graduation-survival

Fonte: https://arxiv.org/html/2607.02823v3

Pump.fun Graduation Regime Windows: Survival Analysis of832,941 Token Launches and the Social-Presence Effect (Corrected, v2; incorporates Corrigenda v1.3 and v1.4) 

- 

- 

- 

- 

- 

- 

- 
- 

 Title: 

 Content selection saved. Describe the issue below:

 Description: 

 arXiv is now an independent nonprofit! 
 Learn more 
 × 

 License: CC BY 4.0

arXiv:2607.02823v3 [q-fin.TR] 17 Aug 2026

# Pump.fun Graduation Regime Windows: Survival Analysis of
 832,941 Token Launches and the Social-Presence Effect
 
 (Corrected, v2; incorporates Corrigenda v1.3 and v1.4)

 Arati Uday Kamat
 ORCID: 0009-0000-4781-312X 

 June 10, 2026 (original); revised August 13, 2026

###### Abstract

 We present a Kaplan-Meier and Cox proportional-hazards survival analysis of 832,941 Solana pump.fun
token launches, observed continuously between 2026-05-08 and 2026-06-10. The pooled graduation rate
is 0.198% (Wilson 95% CI [0.189%, 0.208%]; steady-state 0.207%). A post-publication audit
established that the collector’s coverage was effectively limited to roughly six minutes after each
launch, so this figure should be read as a fast-regime graduation rate and a lower bound on the true
24-hour rate, not an estimate of the latter. Comparing this figure to the 0.63% rate Marino et al.
(2026) report for September-October 2025 gives a ratio of 3.18 × \times ; because our figure is itself a
lower bound, this ratio is an upper bound on the true decline, and the true decline is smaller by an
amount this dataset cannot establish. We formalise the windowed comparison as the Graduation Regime
Windows (GRW) framework and release the underlying 860,213-launch dataset under CC-BY-4.0 on Zenodo.
Within the fast-regime window we measure reliably, social-channel presence exerts a large effect:
launches advertising a Telegram channel graduate at 1.485% versus 0.166% without (8.94 × \times lift;
Cox hazard ratio 5.40, 95% CI [4.73, 6.17]), likely itself a lower bound on the true 24-hour effect.
Initial market capitalisation above the 30 SOL platform default is the strongest single predictor (Cox
HR 4.51); the top quartile graduates at 0.634%, close to though not conclusively matching the
Marino et al. pooled rate. Cox concordance is 0.858, stable under bootstrap resampling and a
time-window split. A subsequent attempt to recover missed late graduations by flagging implausibly
high market-capitalisation TIMEOUT mints was tested directly against pump.fun’s live bonding-curve
state and did not hold up (0 of 100 sampled mints showed evidence of graduation); we report and
withdraw that analysis in full rather than let an unverified correction stand. The dataset is deposited
at Zenodo concept DOI 10.5281/zenodo.20633486 , with the
current corrigendum (v1.4) at 10.5281/zenodo.21923106 .

 Keywords: pump.fun, Solana, memecoin, Kaplan-Meier, Cox proportional hazards,
survival analysis, crypto microstructure, benchmark dataset, measurement error, coverage bias.

## 1 Introduction

 The Solana-based pump.fun platform issued more than 12.8 million tokens by October 2025 (Hu et al.,
2026) and accounted for a majority of Solana token mints during late 2024 (Mancino, 2025). A token
“graduates” when its bonding-curve reserve reaches a threshold (approximately 85 SOL in real
reserves, on top of a 30 SOL virtual bootstrap) and migrates to the PumpSwap decentralized exchange.
Graduation is the rare event in this market: Marino et al. (2026), the first peer-quality empirical
study of the platform, report a 0.63% graduation rate over a 655,770-token sample collected in
September and October 2025, with a time-to-graduation distribution extending to tens of minutes.

 This paper originally set out to extend that line of work with a Kaplan-Meier and Cox
proportional-hazards treatment of a comparably large sample, adding launch-metadata features (Twitter,
website, and Telegram presence) not previously studied at this scale. The core empirical results below
are real and reproducible: 832,941 launches, 1,651 graduations, a large and statistically overwhelming
lift associated with an advertised Telegram channel, and a market-capitalisation threshold effect
consistent with the platform’s own bonding-curve mechanics. What has changed since the original release
of this paper and its companion dataset is our understanding of what the pooled rate actually measures.

 An external reader who reproduced our released figures from the deposited data noticed that
recomputing graduation and timeout durations from on-chain timestamps produced two disjoint clusters:
every graduation completed within six minutes of launch, and every timeout was recorded at almost
exactly 24 hours, with nothing in between. This pattern is not a property of pump.fun; it is a property
of the data collector, which polled a paginated top-50-newest listing endpoint and lost track of any
mint that scrolled off that list before it graduated. A token that took, say, twenty minutes to
graduate was invisible to the collector for the rest of its tracked life and was recorded as a
non-graduate at the 24-hour mark regardless of what actually happened on-chain. We document this
limitation in full in Section 3 and, following standard practice for a dataset already in public use,
relabel every rate in this paper accordingly rather than issue a silent revision.

 We subsequently attempted to correct for the missing slow-graduating mints by treating TIMEOUT-labelled
launches with an implausibly high recorded market capitalisation as probable missed graduations. We no
longer believe that correction is valid, and we describe why, and withdraw it, in Section 3.3. We
report both the original limitation and the withdrawn attempted fix here in full, rather than quietly
revise the headline numbers, because a visible correction record is worth more to downstream users of
this dataset than a clean-looking but undocumented number.

### Contributions

- 1. 
 
 The first publicly released record-level pump.fun launch benchmark, RED-PUMP-2026-v1, with a
frozen schema and CC-BY-4.0 licence, together with a documented, reproducible correction record
(Section 3).

- 2. 
 
 The first published Kaplan-Meier survival curve and Cox proportional-hazards analysis of pump.fun
graduation, correctly scoped as a fast-regime (approximately six-minute) characterisation rather than a
24-hour one (Sections 4–5).

- 3. 
 
 A three-point longitudinal comparison across published pump.fun graduation-rate measurements,
with an explicit accounting of why the comparison is an upper bound on the true cross-regime decline
rather than a point estimate (Section 5).

- 4. 
 
 A worked example of diagnosing and retracting an invalid post-hoc data correction using direct
on-chain verification, offered as a caution to other users of bonding-curve datasets who may be tempted
to treat a virtual-reserve-derived field as evidence of real capital accumulation (Section 3.3).

## 2 Related work

 Pump.fun-specific. Marino et al. (2026) provide the first academic study of the platform: a
655,770-token sample from September–October 2025, with 4,338 graduations (0.63%). Their methodology
is non-parametric conditional-probability estimation with binning, plus a Shewhart-style control chart
for dump detection. They explicitly do not apply Kaplan-Meier, Cox proportional-hazards, logistic, or
other machine-learning models to graduation, proposing all as future work; their feature set is purely
on-chain (bonding-curve state, bot-routed transaction share, trader identities). They do not release
data or code, and their reported time-to-graduation distribution has a median of 4.4 minutes with a
tail extending to tens of minutes, materially longer than what our collector, as we now understand it,
could observe.

 Anderson (2025) offers a qualitative discussion of pump.fun tokenisation and market dynamics. Hu et al.
(2026) introduce MELT, a behavioural-trace dataset for detecting high-risk memecoin launches on Solana
(initially circulated as “MemeTrans”), and report the 12.8-million-token figure by October 2025;
their orientation is classification of malicious launches rather than graduation modelling.

 Broader Solana memecoin literature. Mancino (2025) studies Solana memecoin trends across Q4
2024 and finds fewer than 2% of pump.fun tokens transition to major decentralised exchanges. Long et al.
(2024) introduce a multimodal dataset combining visual, textual, community, and financial signals for
memecoin analysis.

 Survival analysis in microstructure. Kaplan-Meier and Cox proportional-hazards models are
standard tools in market-microstructure research, with prior application to limit-order survival,
execution duration, and asset delisting. We apply them here, for the first time in published form, to
bonding-curve graduation as the event of interest, with the coverage caveat detailed below.

## 3 Data

### 3.1 Collection

 A public-blockchain observer polled the pump.fun REST endpoint

 GET /coins?sort=created_timestamp&order=DESC&limit=50 

 continuously between
2026-05-08T17:17:38Z and 2026-06-10T18:11:08Z (34 days). At first detection of a new launch, the
observer recorded the mint address, the observer-side detection timestamp, the on-chain creation
timestamp, the initial market capitalisation in SOL, three Boolean indicators for whether the launch
metadata advertised a Twitter/X account, a website, or a Telegram channel, and the character length of
the token description. Each launch was then tracked toward one of two terminal outcomes: GRADUATED, if
the bonding curve reached the migration threshold, or TIMEOUT, written by a background timer if 24
hours elapsed from first detection.

### 3.2 Coverage-window limitation

 At the observed steady-state creation rate of approximately 18.08 new mints per minute, the 50-slot
listing window turns over roughly every 2.77 minutes. Once a mint scrolled off that list it was never
re-queried through any per-mint path, and the TIMEOUT outcome was written by a timer keyed only to
elapsed time, with no check of the mint’s actual state at 24 hours. This is visible directly in the
deposited timestamps: recomputing duration from on-chain creation to terminal outcome, the 1,629
GRADUATED rows with a valid chain timestamp span 1.02 to 5.98 minutes (median 1.66); the 781,401
comparable TIMEOUT rows span 1440.00 to 1448.59 minutes, with no outcome recorded anywhere in between.
Fourteen mints appear twice in the raw data, first as GRADUATED within a few minutes of launch and then,
independently, as TIMEOUT roughly 24 hours later for the same mint. This is only explicable if the
timeout-writing process does not check prior state before firing.

 We therefore describe the observed regime as fast-regime graduation : the collector reliably
captures graduations completing within about six minutes of launch, and cannot distinguish, among the
remainder, between tokens that genuinely never graduated and tokens that graduated slowly and were
never re-observed. Every rate reported in this paper is a fast-regime rate and a lower bound on the
corresponding true 24-hour rate. This limitation was identified in a post-publication audit and is
documented as Corrigendum v1.3 (2026-08-11) on the Zenodo record.

### 3.3 Withdrawn correction attempt

 Following the discovery above, we attempted a numeric correction: among TIMEOUT-labelled mints, a
subset records a final market capitalisation above the highest value ever observed among confirmed
graduates (165.41 SOL), which we initially read as evidence of missed late graduations. Restricting to
ordinary-start mints (initial market cap of 40 SOL or less) with a final market cap above this ceiling
yielded 1,126 such mints, which would have raised the pooled rate to approximately 0.333% had they
genuinely graduated.

 This correction is withdrawn. Direct verification against pump.fun’s live API for a deterministic
100-mint sample of this group found that none had graduated: the complete flag on the bonding
curve, a permanent record once a token migrates, read false for all 100, and real SOL reserves were
typically a small fraction of a SOL rather than the roughly 85 SOL graduation requires. The
market-capitalisation field we had used is computed from the curve’s virtual reserves, a
quantity that tracks speculative price movement and can rise arbitrarily far above the graduation
ceiling without any corresponding real capital ever entering the curve. We report this withdrawn
correction here, rather than omit it, because it is a useful caution: on a bonding-curve platform, a
field named “market cap” is not automatically evidence of accumulated real capital, and the two can
diverge sharply under thin-liquidity price action. Full verification evidence (raw API responses,
calibration data, and a reproducible verification script) is deposited as Corrigendum v1.4
(2026-08-13) alongside this dataset.

### 3.4 Headline statistics

 The raw dataset contains 860,213 launch records on 860,194 unique mints; after removing 18 duplicate
mints and 216 malformed or unusable outcome rows (0.03% of 833,171 outcome records), 832,941 unique
mints carry a usable terminal outcome: 1,651 graduated and 831,290 timed out. A further 27,253 launches
were still within their tracking window at the observation snapshot and are excluded from analysis.

 The pooled fast-regime graduation rate is

 p ^ = 1,651 832,941 = 0.001982 , \hat{p}=\frac{1{,}651}{832{,}941}=0.001982, 

 Wilson 95% CI [0.001889, 0.002080], i.e. 0.198% (95% CI [0.189%, 0.208%]). Restricting to the
29-day steady-state window that excludes four days of tracker warm-up and the final partial day gives
0.207% (95% CI [0.198%, 0.218%]) on 763,091 launches; every stratified result below is unchanged to
within rounding under this restriction. Among the 1,651 graduates, time to graduation on the on-chain
timestamp basis has median 1.66 minutes, 90th percentile 2.80 minutes, and maximum 5.98 minutes. This is
consistent with the coverage limitation above, not a claim about the platform’s true time-to-graduation
distribution, which Marino et al. (2026) report as extending well past six minutes.

### 3.5 Public release

 We release the data as RED-PUMP-2026-v1 on Zenodo under CC-BY-4.0. The deposit contains two raw data
files ( red_pump_2026_v1_launches.jsonl.gz , 47.9 MB, and
 red_pump_2026_v1_outcomes.csv.gz , 43.6 MB), a frozen schema, reproducible analysis
scripts ( km_full.py , km_figures.py ), an integrity manifest, and two corrigenda
documenting the coverage-window limitation and the withdrawn market-capitalisation correction
respectively, together with full verification evidence for the latter.
Raw data files are byte-identical across every version of the deposit; only labelling, documentation,
and derived analysis have changed.

## 4 Methods

### 4.1 Survival framework

 For each launch i ∈ { 1 , … , N } i\in\{1,\dots,N\} with N = 832,941 N=832{,}941 , let T i ∈ ( 0 , 24 ​ h ] T_{i}\in(0,24\text{h}] denote
observed time from detection to graduation (if it occurred), and δ i ∈ { 0 , 1 } \delta_{i}\in\{0,1\} the event
indicator. We estimate the cumulative graduation probability F ⁡ ( t ) = 1 − S ⁡ ( t ) F(t)=1-S(t) via the Kaplan-Meier
estimator

 S ^ ​ ( t ) = ∏ t ( i ) ≤ t ( 1 − d i n i ) , \hat{S}(t)=\prod_{t_{(i)}\leq t}\left(1-\frac{d_{i}}{n_{i}}\right), 

 with pointwise 95% confidence bands from the log-log transform. Given the coverage limitation
described in Section 3.2, this curve should be read as characterising the fast-regime graduation
process specifically, not survival over the full nominal 24-hour window; the plateau visible in Figure 1
beyond approximately six minutes reflects the boundary of what the collector could observe, not a
substantive claim that graduation probability stops evolving after that point.

### 4.2 Stratification and Cox proportional hazards

 We stratify by the three binary social-presence indicators, individually and by their sum, and by
quartile of initial market capitalisation, testing between-stratum equality with the log-rank
statistic. The multivariate Cox model uses covariate vector
 x i = ( has_twitter i , has_website i , has_telegram i , log ⁡ ( 1 + mcap_sol i ) , log ⁡ ( 1 + desc_len i ) ) x_{i}=(\text{has\_twitter}_{i},\text{has\_website}_{i},\text{has\_telegram}_{i},\log(1+\text{mcap\_sol}_{i}),\log(1+\text{desc\_len}_{i})) with an ℓ 2 \ell_{2} -penalised partial likelihood
(penalty 10 − 3 10^{-3} ). All analyses use Python 3.12, lifelines 0.30.3, and pandas 2.3.3; Wilson confidence
intervals use scipy.stats .

## 5 Results

### 5.1 Overall graduation curve

 Figure 1 shows the Kaplan-Meier cumulative graduation curve. The curve rises steeply for t ≤ 2 t\leq 2 
minutes, covering 90% of graduates, then flattens at the boundary of the collector’s effective
visibility window rather than at a substantive asymptote.

 Figure 1: Kaplan-Meier cumulative graduation curve for the full RED-PUMP-2026-v1 sample ( N = 832,941 N=832{,}941 ).
The curve flattens beyond approximately six minutes because the collector’s coverage window ends there
(Section 3.2), not because graduation probability substantively stops evolving at that point. 

### 5.2 Social-presence stratification

 Table 1 reports stratified rates. All three social-channel indicators are highly significant; the
Telegram indicator alone yields an 8.94 × \times lift within the fast-regime window measured. Because
slower-graduating tokens are systematically undercounted by the coverage window (Section 3.2), and
Telegram presence plausibly correlates with slower, more organic liquidity accumulation rather than
instant bot-driven fills, this lift is likely itself a lower bound on the true 24-hour effect; we do not
attempt to quantify the size of that correction numerically, having withdrawn an earlier attempt to do
so (Section 3.3).

 Table 1: Graduation rates stratified by each social-channel indicator (fast-regime). 

 Stratum 
 n n 
 graduates 
 rate (%) 
 95% CI (%) 
 log-rank p p 

 Twitter 

 has_twitter = 0 
 304,815 
 453 
 0.1486 
 [0.136, 0.163] 
 1.1 × 10 − 14 1.1\times 10^{-14} 

 has_twitter = 1 
 528,126 
 1,198 
 0.2268 
 [0.214, 0.240] 

 has_website = 0 
 517,680 
 820 
 0.1584 
 [0.148, 0.170] 
 1.2 × 10 − 25 1.2\times 10^{-25} 

 has_website = 1 
 315,261 
 831 
 0.2636 
 [0.246, 0.282] 

 has_telegram = 0 
 812,671 
 1,350 
 0.1661 
 [0.158, 0.175] 
 < 10 − 300 <10^{-300} 

 has_telegram = 1 
 20,270 
 301 
 1.4850 
 [1.327, 1.661] 

 Figure 2: KM cumulative graduation curves split by Telegram presence, fast-regime window
(log-rank p < 10 − 300 p<10^{-300} ). 

 The combined social-channel count produces a near-monotone gradient: from 0.110% for launches
advertising none of the three, to 1.919% for launches advertising all three, a 17.4 × \times lift.

 Figure 3: KM curves by combined social-channel count, fast-regime window. 

### 5.3 Initial market-capitalisation quartiles

 The initial market-capitalisation distribution has a large point mass at exactly 30 SOL, the platform
default; quartile boundaries are correspondingly uneven (Q1: 1.39–30.00 SOL, n = 326,691 n=326{,}691 ; Q2:
 { 30.00 } \{30.00\} , n = 91,247 n=91{,}247 ; Q3: 30.00–31.04 SOL, n = 206,768 n=206{,}768 ; Q4: 31.04–2,000 SOL, n = 208,235 n=208{,}235 ).
The top quartile, interpretable as launches where the creator bought into their own token at launch,
graduates at 0.634% (95% CI [0.601%, 0.669%]), close to the 0.63% pooled rate Marino et al. (2026)
report for a different measurement window. We had originally read this proximity as strong evidence
that the cross-regime decline in graduation rates was substantially attributable to a shift in launch
composition toward zero-self-buy tokens. We now hold that interpretation more loosely: since our own
pooled rate is a fast-regime lower bound rather than a directly comparable 24-hour figure, the apparent
3 × \times -scale gap this decomposition explains is itself not established with confidence (Section 5.5),
and the compositional-shift account should be read as a hypothesis about what would explain an
apparent gap of this kind, rather than a confirmed decomposition of a measured one.

### 5.4 Cox proportional-hazards model

 Table 2 and Figure 4 report the multivariate Cox model. Telegram presence carries the largest hazard
ratio (5.40, 95% CI [4.73, 6.17]), followed by log market capitalisation (4.51); Twitter and website
presence carry smaller but significant hazard ratios (1.30 and 1.19). Harrell’s concordance is 0.858,
stable under bootstrap resampling (95% CI [0.850, 0.870]) and under a first-half/second-half
time-window split (0.881 and 0.847 respectively). All of this should be read as a characterisation of
fast-regime discrimination specifically, per Section 3.2.

 Table 2: Multivariate Cox proportional-hazards model, fast-regime window. Penalised partial likelihood,
 ℓ 2 \ell_{2} coefficient 10 − 3 10^{-3} . 

 Covariate 
 HR 
 95% CI 
 β \beta 
 SE 
 p p 

 has_twitter 
 1.305 
 [1.192, 1.428] 
 0.266 
 0.046 
 7.3 × 10 − 9 7.3\times 10^{-9} 

 has_website 
 1.194 
 [1.096, 1.300] 
 0.177 
 0.044 
 4.9 × 10 − 5 4.9\times 10^{-5} 

 has_telegram 
 5.402 
 [4.733, 6.166] 
 1.687 
 0.067 
 6.8 × 10 − 138 6.8\times 10^{-138} 

 log ⁡ ( 1 + mcap_sol ) \log(1+\text{mcap\_sol}) 
 4.506 
 [4.293, 4.729] 
 1.505 
 0.025 
 < 10 − 300 <10^{-300} 

 log ⁡ ( 1 + desc_len ) \log(1+\text{desc\_len}) 
 1.054 
 [1.034, 1.076] 
 0.053 
 0.010 
 1.8 × 10 − 7 1.8\times 10^{-7} 

 N N 
 832,941 

 events 
 1,651 

 concordance 
 0.858 

 Figure 4: Cox proportional-hazards forest plot, fast-regime window. All five covariates significant at
 p < 10 − 4 p<10^{-4} . 

### 5.5 Regime comparison

 We compare our fast-regime figure to two prior published measurements: Mancino (2025) for Q4 2024
( < 2 % <2\% graduation), and Marino et al. (2026) for September–October 2025 (0.63% over 655,770
launches). Figure 5 shows the three-point series. Because our 0.198% figure is a confirmed lower bound
rather than a directly comparable 24-hour rate, the ratio 0.63 / 0.198 = 3.18 × 0.63/0.198=3.18\times is an
 upper bound on the true decline between the Marino et al. window and our own; the true decline
is smaller, by an amount this dataset cannot establish without a properly instrumented re-collection.

 Figure 5: Three-point longitudinal comparison of published pump.fun graduation-rate measurements. The
RED-PUMP-2026-v1 bar is hatched and marked with an upward arrow to indicate that it is a lower bound on
the true fast-regime figure, not a directly comparable 24-hour estimate. 

### 5.6 Temporal behaviour within the observation window

 Figure 6 shows daily fast-regime rates, excluding the partial last day. That day is excluded because,
given a 24-hour TIMEOUT window and a snapshot taken partway through it, no launch from that calendar day
could yet have accumulated enough elapsed time to be written as TIMEOUT; every terminal outcome
recorded for it is mechanically a GRADUATED row, making its single-day rate meaningless as a measurement
and not indicative of anything unusual in the data. The first four days
(2026-05-08 to 2026-05-11) run materially below the pooled 95% CI, which we attribute to
graduation-detection callbacks initialising later than launch-detection callbacks in the observer
infrastructure; we exclude these as a warm-up period. The remaining 29 days stabilise inside the pooled
CI band, giving the steady-state rate of 0.207% reported above. All structural conclusions in this
paper replicate to within decimal-place noise under this restriction.

 Figure 6: Daily fast-regime graduation rate with Wilson 95% CIs. Orange: four warm-up days. Blue: 29
steady-state days. Partial last day excluded. 

## 6 Discussion

### 6.1 Social-presence effects: direction, not yet magnitude

 The 5.40 Cox hazard ratio for Telegram presence is the largest social effect measured, and the
social-channel-count gradient is near-monotone. We do not claim causality; setting up a Telegram
channel may proxy for creator effort, discoverability to buy-side bots and traders, or selection by
creators who already expect to succeed. We also do not claim these are correctly scaled 24-hour
effects: a token that graduates within six minutes is fully visible to our collector regardless of its
features, while a token taking longer is only visible if it happens to graduate before scrolling off
the top-50 listing, a probability unrelated to launch features but related to how long graduation takes.
If Telegram presence correlates with slower, more organic accumulation, our collector undercounts
Telegram-associated graduations more than instant, likely self-buy-driven ones, biasing the reported
lift downward relative to the true 24-hour effect. We flag this direction of bias without attempting to
quantify it numerically, since our one attempt to do so (Section 3.3) did not survive direct
verification.

### 6.2 The withdrawn correction, and what it teaches

 Beyond the specific retraction, the failure mode in Section 3.3 generalises: on a bonding-curve
platform, a field labelled “market cap” typically reflects virtual reserves that move with price, not
real reserves that reflect accumulated capital. The two are only loosely coupled and diverge sharply
under thin-liquidity price action, which is common on pump.fun. Any dataset user treating market-cap
fields as a proxy for graduation proximity should confirm, against the platform’s own state
( complete , real_sol_reserves ), that the field in question is real-reserve-derived
before drawing that inference.

### 6.3 What remains genuinely unknown

 The true 24-hour pump.fun graduation rate for the window we observed is unknown from this dataset. It
is bounded below by 0.198% and has no established upper bound from these data. The compositional-shift
account in Section 5.3 remains a plausible explanation for why zero-self-buy and self-buy launches
diverge as sharply as they do within our own sample, but it should not be read as an explanation of a
confirmed cross-regime decline, since the size of that decline is not itself confirmed.

## 7 Limitations

- 1. 
 
 The central limitation of this study is the coverage-window bound described in Section 3.2: our
collector’s effective visibility window was approximately six minutes, not 24 hours, and every rate we
report is a fast-regime rate and a lower bound on the true 24-hour equivalent. We are not able, from
this dataset, to state how large the gap between the two is.

- 2. 
 
 Feature-level hazard ratios in Section 5.4 likely carry a feature-dependent bias in the direction
described in Section 6.1, which we can characterise qualitatively but not correct numerically with the
data in hand.

- 3. 
 
 Our attempt at a numerical correction using final market capitalisation as a graduation proxy was
itself invalid and is withdrawn (Section 3.3); we describe it in full for the sake of an honest and
complete record rather than omit it.

- 4. 
 
 The Cox proportional-hazards model assumes time-invariant covariate effects over a very short and
heavily left-truncated observed-duration range (five discrete integer-minute values among graduates
against a fixed censoring point for the remainder); we report concordance as a measure of discrimination
within the fast regime and do not claim it would hold under a properly instrumented 24-hour collector.

- 5. 
 
 We make no real-money trading or filter-deployment claims. Reported effect sizes are predictive
and useful for filter design within the fast regime observed, not actionable trading signals without
further out-of-sample validation on a corrected, full-coverage dataset.

## 8 Conclusion

 We report a large-sample Kaplan-Meier and Cox proportional-hazards analysis of pump.fun token
graduation, finding strong and consistent evidence that advertised Telegram presence and above-default
initial market capitalisation are the two strongest predictors of graduation within the regime this
dataset can support: launches completing within roughly six minutes of creation. A post-publication
audit established that the collector’s paginated polling design could not reliably observe graduations
outside that window; the pooled rate originally reported as a 24-hour figure is more precisely a
fast-regime figure and a lower bound on the true 24-hour rate. A subsequent attempt to numerically
correct for this limitation was tested directly against the platform’s own bonding-curve state and did
not hold up; we withdraw it here rather than let it stand uncorrected. We release the full dataset,
including the timestamps and verification evidence that made both corrections possible, under
CC-BY-4.0, and treat measurement of the true 24-hour pump.fun graduation rate for this window as an
open problem for a differently instrumented follow-up study.

## Data and code availability

 The dataset (RED-PUMP-2026-v1) and analysis code are deposited on Zenodo at concept DOI
 10.5281/zenodo.20633486 , which resolves to the latest
version. The current version (v1.4, DOI
 10.5281/zenodo.21923106 ) includes the raw launch and
outcome files (byte-identical since v1.0), a frozen schema, reproducible analysis scripts
( km_full.py , km_figures.py ), and two corrigenda: v1.3 (coverage-window
relabelling) and v1.4 (retraction of the market-capitalisation correction, with full verification
evidence). All figures and tables in this paper are reproducible from the deposited files.

## Acknowledgements

 The author thanks the open-source Solana RPC and pump.fun program developers whose public data
infrastructure makes this kind of empirical work possible, and the external reader who first identified
the coverage-window limitation in the originally deposited dataset.

## Conflicts of interest

 The author holds two pending United States provisional patent applications in the field of algorithmic
decentralised-exchange trading and blockchain market microstructure (#64/022,461, filed 30 March 2026;
#64/099,108, filed 25 June 2026), both Micro Entity status. Neither application covers the methods or
findings reported in this manuscript.

## References

 Anderson, M. (2025). Pump.fun and the tokenization of memes. SSRN preprint 5257754. 

 ChainCatcher (2025). Pump.fun weekly graduation rate report (September 2025).
 https://www.chaincatcher.com/en/article/2178053 . 

 Dune Analytics (2026). Pump.fun graduations dashboard. https://dune.com/jondar/pumpfun . 

 Hu, S., Tekin, S. F., Xu, Y., and Liu, L. (2026). MELT: A behavioral trace dataset for high-risk
memecoin launch detection. arXiv preprint arXiv:2602.13480. 

 Long, H.-W., Wong, N.-M., and Cai, W. (2024). Bridging culture and finance: a multimodal analysis of
memecoins in the Web3 ecosystem. arXiv preprint arXiv:2412.04913. 

 Mancino, D. (2025). The memecoin phenomenon: an in-depth study of Solana’s blockchain trends.
 2025 IEEE Symposium on Computers and Communications (ISCC) , 1–6.
doi:10.1109/ISCC65549.2025.11326251. arXiv preprint arXiv:2512.11850. 

 Marino, G., Naviglio, M., Tarantelli, F., and Lillo, F. (2026). Predicting the success of new
crypto-tokens: the pump.fun case. arXiv preprint arXiv:2602.14860. SSRN ID 6543715. 

 The Block (2026). Pump.fun percent graduated tokens (daily).
 https://www.theblock.co/data/on-chain-metrics/solana/pump-fun-percent-graduated-tokens-daily .
