# Probe jocry (download diretto)

## postgard_outcomes.parquet: 5,669 righe, 1.0 MB
- `mint` VARCHAR
- `computed_at` TIMESTAMP WITH TIME ZONE
- `peak_price_usd` DOUBLE
- `peak_price_at` TIMESTAMP WITH TIME ZONE
- `peak_mcap_usd` DOUBLE
- `peak_liquidity_usd` DOUBLE
- `price_at_grad_usd` DOUBLE
- `price_at_1m_usd` DOUBLE
- `price_at_5m_usd` DOUBLE
- `price_at_10m_usd` DOUBLE
- `price_at_20s_usd` DOUBLE
- `price_at_30s_usd` DOUBLE
- `price_at_30m_usd` DOUBLE
- `price_change_1h_pct` DOUBLE
- `price_change_6h_pct` DOUBLE
- `price_change_24h_pct` DOUBLE
- `price_change_36h_pct` DOUBLE
- `still_liquid_at_24h` BOOLEAN
- `still_liquid_at_48h` BOOLEAN
- `rug_detected` BOOLEAN
- `rug_at` TIMESTAMP WITH TIME ZONE
- `total_volume_24h_usd` DOUBLE
- `total_volume_48h_usd` DOUBLE
- `success_label` BOOLEAN
- `success_window_mins` DOUBLE
- `target_label_legacy` VARCHAR
- `volume_to_liquidity_ratio` DOUBLE
- `outcome_label` VARCHAR

```
                            mint                    computed_at  peak_price_usd                  peak_price_at  peak_mcap_usd  peak_liquidity_usd  price_at_grad_usd  price_at_1m_usd  price_at_5m_usd  price_at_10m_usd  price_at_20s_usd  price_at_30s_usd  price_at_30m_usd  price_change_1h_pct  price_change_6h_pct  price_change_24h_pct  price_change_36h_pct  still_liquid_at_24h  still_liquid_at_48h  rug_detected rug_at  total_volume_24h_usd  total_volume_48h_usd  success_label  success_window_mins target_label_legacy  volume_to_liquidity_ratio outcome_label
0  4bbP9eJHH4RYmJ7PMZVTYMzpYS... 2026-07-14 14:32:21.769228+...    8.825000e-09 2026-07-14 13:18:41.118884+...           18.0                6.70       6.760000e-09     8.825000e-09     8.353000e-10      7.278000e-10      6.760000e-09      6.760000e-09      6.394000e-10               -92.96                  NaN                   NaN                   NaN                False                False         False    NaT                308.83                617.66          False                  NaN                dead                   160.7500          dead
1  FXUV8pJ1YW7Wv4iothAoJkd3NF... 2026-07-09 14:04:06.103667+...    3.625000e-04 2026-07-07 16:49:32.504023+...       362528.0            46398.48       1.753000e-04     1.753000e-04     1.846000e-04      3.041000e-04      1.753000e-04      1.753000e-04      5.374000e-05               -98.73               -98.29                -98.99                -99.13                 True                False         False    NaT             363923.99             364438.19           True                 10.0          minor_pump                     6.0612    minor_pump
2  6rnsrxG75EjBUpL29NhdmnZMoG... 2026-07-10 01:35:50.386036+...    8.219000e-08 2026-07-08 04:00:20.214146+...          164.0               39.54       6.224000e-08     8.219000e-08     8.919000e-09      7.190000e-09      6.224000e-08      6.224000e-08      5.885000e-09               -93.02               -97.04                -97.45                -97.45                False                False         False    NaT                587.85                587.95          False                  NaN                dead                    48.9563          dead
```

## migrations.parquet: 5,701 righe, 0.5 MB
- `mint` VARCHAR
- `migrated_at` TIMESTAMP WITH TIME ZONE
- `seconds_to_graduation` DOUBLE
- `pool_address` VARCHAR

```
                            mint                    migrated_at  seconds_to_graduation                   pool_address
0  Hd7GcJMeEjYDNNtz7dLQZ7Af47... 2026-07-07 17:56:31.988296+...              35.105301     synthetic_graduation_queue
1  HTmeSfrWC1cdZboZuoqjmyJs11... 2026-07-07 17:58:01.626377+...                    NaN  2jiXG5LCNTM7J5DKC3RonFn7hr...
2  5Lro9ExmNQXvqLMAba4x9TgS8U... 2026-07-07 17:59:57.189274+...              47.266672     synthetic_graduation_queue
```

## postgard_snapshots.parquet: 1,392,133 righe, 89.3 MB
- `mint` VARCHAR
- `snapshot_time` TIMESTAMP WITH TIME ZONE
- `seconds_since_graduation` DOUBLE
- `phase` BIGINT
- `pair_address` VARCHAR
- `dex_id` VARCHAR
- `incomplete_data` BOOLEAN
- `price_native` DOUBLE
- `price_usd` DOUBLE
- `price_change_5m` DOUBLE
- `price_change_1h` DOUBLE
- `price_change_6h` DOUBLE
- `price_change_24h` DOUBLE
- `market_cap_usd` DOUBLE
- `fdv_usd` DOUBLE
- `liquidity_usd` DOUBLE
- `liquidity_base` DOUBLE
- `liquidity_quote` DOUBLE
- `volume_5m` DOUBLE
- `volume_1h` DOUBLE
- `volume_6h` DOUBLE
- `volume_24h` DOUBLE
- `buys_5m` BIGINT
- `sells_5m` BIGINT
- `buys_1h` BIGINT
- `sells_1h` BIGINT
- `buy_pressure_1h` DOUBLE

```
                            mint                  snapshot_time  seconds_since_graduation  phase                   pair_address    dex_id  incomplete_data  price_native     price_usd  price_change_5m  price_change_1h  price_change_6h  price_change_24h  market_cap_usd   fdv_usd  liquidity_usd  liquidity_base  liquidity_quote  volume_5m  volume_1h  volume_6h  volume_24h  buys_5m  sells_5m  buys_1h  sells_1h  buy_pressure_1h
0  6AvAzJ2BaCzst4msW9rkgEu5Zz... 2026-07-07 19:23:02.798109+...                 102604.61      4  CfVAcqA2K5vVSVyMCiB6q7hcfC...  pumpswap            False  1.779000e-11  1.439000e-09              NaN              NaN           -12.09            -12.09            3.00      3.00           5.09    1.821932e+09           0.0305        0.0        0.0       0.18        0.31        0         0        0         0              NaN
1  7b7i8W4EmX2ke3NUHNGMvLXKZZ... 2026-07-07 19:23:02.798295+...                 111576.85      4  JCHvq3MrLr66JWEvDQtQ1dcSAG...   pumpfun            False  1.635000e-07  1.331000e-05              NaN              NaN              NaN            -80.26        13310.32  13310.32            NaN             NaN              NaN        0.0        0.0       0.00      685.33        0         0        0         0              NaN
2  FVCS67YAujjA9U71Z5bKFTNpSz... 2026-07-07 19:23:02.798477+...                 154641.48      4  LKg3qGFSyKB6Sq8p6sCFLBcm54...  pumpswap            False  2.879000e-08  2.361000e-06              NaN              NaN            19.30             12.14         2360.00   2360.00        3833.90    8.124972e+08          23.3481        0.0        0.0     235.74      263.96        0         0        0         0              NaN
```

## tokens.parquet: 798,430 righe, 214.4 MB
- `mint` VARCHAR
- `detected_at` TIMESTAMP WITH TIME ZONE
- `tracking_expires_at` TIMESTAMP WITH TIME ZONE
- `name` VARCHAR
- `symbol` VARCHAR
- `uri` VARCHAR
- `is_mayhem_mode` BOOLEAN
- `creator` VARCHAR
- `creator_past_tokens` DOUBLE
- `creator_past_rugs` DOUBLE
- `initial_buy_tokens` DOUBLE
- `initial_buy_sol` DOUBLE
- `v_tokens_bonding_curve` DOUBLE
- `v_sol_bonding_curve` DOUBLE
- `initial_market_cap_sol` DOUBLE
- `initial_price_sol` DOUBLE
- `dev_buy_pct` DOUBLE
- `bonding_curve_key` VARCHAR
- `initial_holder_count` DOUBLE
- `initial_top1_pct` DOUBLE
- `initial_top5_pct` DOUBLE
- `initial_top10_pct` DOUBLE
- `initial_gini` DOUBLE
- `graduated_at` TIMESTAMP WITH TIME ZONE
- `seconds_to_graduation` DOUBLE
- `peak_market_cap_sol` DOUBLE
- `peak_market_cap_at` TIMESTAMP WITH TIME ZONE
- `trade_count` BIGINT
- `data_quality_score` DOUBLE
- `is_training_ready` BOOLEAN
- `is_zombie` BOOLEAN
- `entry_price_usd` DOUBLE
- `entry_price_20s_usd` DOUBLE
- `entry_price_30s_usd` DOUBLE
- `entry_price_1m_usd` DOUBLE
- `launch_snipe_delta_sol` DOUBLE
- `first_trade_price_sol` DOUBLE
- `is_cashback_enabled` BOOLEAN
- `initial_top1_pct_corrected` DOUBLE
- `initial_top5_pct_corrected` DOUBLE
- `initial_top10_pct_corrected` DOUBLE
- `dev_buy_pct_corrected` DOUBLE
- `supply_bug_corrected` BOOLEAN
- `top10_pct_suspect` BOOLEAN

```
                            mint                    detected_at            tracking_expires_at                           name    symbol                            uri  is_mayhem_mode                        creator  creator_past_tokens  creator_past_rugs  initial_buy_tokens  initial_buy_sol  v_tokens_bonding_curve  v_sol_bonding_curve  initial_market_cap_sol  initial_price_sol  dev_buy_pct              bonding_curve_key  initial_holder_count  initial_top1_pct  initial_top5_pct  initial_top10_pct  initial_gini graduated_at  seconds_to_graduation  peak_market_cap_sol             peak_market_cap_at  trade_count  data_quality_score  is_training_ready  is_zombie  entry_price_usd  entry_price_20s_usd  entry_price_30s_usd  entry_price_1m_usd  launch_snipe_delta_sol  first_trade_price_sol  is_cashback_enabled  initial_top1_pct_corrected  initial_top5_pct_corrected  initial_top10_pct_corrected  dev_buy_pct_corrected  supply_bug_corrected  top10_pct_suspect
0  4r7MHS3Zbdzw8RGaxqchjZtvJx... 2026-07-07 17:14:26.863317+... 2026-07-09 17:14:26.863317+...                   American Ape        AA  https://ipfs.io/ipfs/QmPwX...            True  AnYkCMkr1Ci2uGkStG3yecYHGi...                738.0              510.0        3.461290e+07         1.000000            1.073000e+15         3.000000e+10               27.958993       2.795899e-08     3.461290  3RNmPm2LMiprJRgwkskjF9uqvQ...                   3.0         93.566690          96.68185          96.681850        0.4678          NaT                    NaN           215.871115 2026-07-07 17:14:55.491922+...           44                 1.0               True      False              NaN                  NaN                  NaN                 NaN            2.314004e-08           5.109904e-08                False                   46.783345                   48.340925                    48.340925               1.730645                  True              False
1  GJDYUjkgnt1f7ug2SbkzK8w6Z9... 2026-06-12 00:05:47.767520+... 2026-06-14 00:05:47.767520+...  Cancer Treatment Fund For ...      LUKE  https://ipfs.io/ipfs/bafkr...           False  C7unxuor882KdAMNCCDkHMtMry...                  0.0                0.0        6.628571e+07         1.975309            1.073000e+15         3.000000e+10               27.958993       2.795899e-08     6.628571  Cw29a4Pd72mTq2b4EGThU2HBgj...                  17.0          6.628571          17.69025          18.986818        0.7062          NaT                    NaN            61.510664 2026-06-12 00:06:52.452232+...           79                 1.0               True      False              NaN                  NaN                  NaN                 NaN            9.731332e-09           3.769033e-08                False                    6.628571                   17.690250                    18.986818               6.628571                 False              False
2  13USkknHCTTyzTgYfXXkHhKbwv... 2026-06-11 23:39:21.682216+... 2026-06-13 23:39:21.682216+...               FAGGOT ALERT DOG  FAGALERT  https://ipfs.io/ipfs/bafkr...           False  FZozpjx68zxshZviD33mYDXxpq...                  5.0                5.0        3.461290e+07         1.000000            1.073000e+15         3.000000e+10               27.958993       2.795899e-08     3.461290  BLWihsN6j1T5xLZXqELn96kGc7...                   8.0         96.838590          96.95394          96.953940        0.8567          NaT                    NaN            80.926745 2026-06-11 23:39:25.840531+...           27                 1.0               True      False              NaN                  NaN                  NaN                 NaN            1.306587e-08           4.102486e-08                False                   96.838590                   96.953940                    96.953940               3.461290                 False              False
```

## trades/trades-00000.parquet: 1,966,080 righe, 309.2 MB
- `id` BIGINT
- `mint` VARCHAR
- `tx_signature` VARCHAR
- `event_time` TIMESTAMP WITH TIME ZONE
- `seconds_since_launch` DOUBLE
- `is_buy` BOOLEAN
- `sol_amount` DOUBLE
- `token_amount` DOUBLE
- `user_wallet` VARCHAR
- `v_tokens_bonding_curve` DOUBLE
- `v_sol_bonding_curve` DOUBLE
- `market_cap_sol` DOUBLE
- `price_sol` DOUBLE
- `curve_pct_depleted` DOUBLE
- `source` VARCHAR

```
        id                           mint                   tx_signature                     event_time  seconds_since_launch  is_buy  sol_amount  token_amount                    user_wallet  v_tokens_bonding_curve  v_sol_bonding_curve  market_cap_sol     price_sol  curve_pct_depleted   source
0  2491711  1212wKK7n3PTChDcXn5X26Q5Dh...  38MYBnJPKJwpi4tRH2psQZhEyA... 2026-06-08 13:58:47.134662+...                   5.0   False    1.481481  5.049412e+07  A1LiHmbdL44bSt7HeybyWSAvXA...            1.073000e+15         3.000000e+10       27.958993  2.795899e-08           35.294117  pumpdev
1  5991343  121HYXX37Q91cFWuukffDnZDU6...  2Zpjoi4sJpybKnyMDuiarqqeqx... 2026-06-10 16:30:36.491356+...                 194.3   False    0.097560  3.478005e+06  4asNBqXDh6uWiYatVP7p5TneS2...            1.072987e+15         3.000036e+10       27.959665  2.795967e-08           35.294540  pumpdev
2  5991186  121HYXX37Q91cFWuukffDnZDU6...  vrZjC7xDcUNd78auh3DnrHTqBC... 2026-06-10 16:30:30.791009+...                 188.6   False    0.098197  3.478005e+06  9q4p3rGdpaQ92YU7hGaT74ZKgP...            1.069509e+15         3.009792e+10       28.141809  2.814181e-08           35.409317  pumpdev
```

## postgard_snapshots: intervallo tra istantanee e copertura per token
```
   mints  dt_mediano_s  dt_p90_s  t_mediano_s    t_max_s
0   5701        310.93   1806.37     11451.48  172808.99
```

## postgard_outcomes: esiti
```
  outcome_label     n
0          dead  2692
1     pump_dump  1072
2    slow_bleed   784
3    major_pump   607
4    minor_pump   320
5     sustained   194
```
