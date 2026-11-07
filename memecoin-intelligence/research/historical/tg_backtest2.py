"""Study 'tg_backtest2': out-of-sample check of the @BINANCE_CRYPTO_SIGNALS_ML signals on data never looked at.

Written AFTER reading tg_backtest (signals of Oct 9-30 with 7 full days), BEFORE looking at these signals: the only
reading that came out slightly positive there was the limit order at the written entry (+0.09% to +0.13% per trade,
interval including zero). Check: the same rules on the signals posted from Oct 31 (excluded there because their
7 days were not complete), with a 24-hour maximum hold (trades lasted 2-7 hours on average). Verdict "regge" only
if the limit-entry readings V2 and V4 are positive here too, with a 95% interval above zero.
"""

import tg_backtest as T

T.HOLD_MIN = 1440
T.MIN_TIME = "2026-10-31"
T.REPORT_NAME = "tg_backtest2"
T.TITLE_EXTRA = ": verifica fuori campione (dal 31 ottobre, tenuta massima 24 ore)"

if __name__ == "__main__":
    T.main()
