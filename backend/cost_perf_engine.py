import math
import sqlite3
import os
import sys
import numpy as np
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import get_db_connection

def calculate_regression(prices, scores):
    """
    Fits Score = a * log10(Price) + b
    Returns (a, b, r_squared)
    """
    valid_x = []
    valid_y = []
    for p, s in zip(prices, scores):
        if p and p > 0 and s is not None and not math.isnan(s):
            valid_x.append(math.log10(p))
            valid_y.append(float(s))

    if len(valid_x) < 5:
        return 0.0, 5.0, 0.0

    x_arr = np.array(valid_x)
    y_arr = np.array(valid_y)

    # Linear regression
    a, b = np.polyfit(x_arr, y_arr, 1)
    # Correlation coefficient R^2
    residuals = y_arr - (a * x_arr + b)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return float(a), float(b), float(r_squared)

def update_cost_performance():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 日本市場価格には2種類ある:
    #   confirmed_price_jpy : 国内価格が確定している機種のみ（verified かつ price_jpy あり）。
    #                         -> 公開ランキング(cp_tone 等)に使用。未確定なら cp_* は NULL。
    #   est_price_jpy       : 未確定でも為替換算の概算を許す探索用の参考価格。
    #                         -> 検証キュー(cp_*_est)の優先順位付けにのみ使用。
    cursor.execute("""
        SELECT
            s.id,
            s.brand,
            s.model,
            s.price_usd,
            CASE
                -- 国内で購入できない（入手不可・生産完了）と確定した機種はコスパ算定から除外
                WHEN j.availability IN ('not_available', 'discontinued')
                     OR j.verification_status = 'unavailable' THEN NULL
                -- ランキングは「国内価格が検証済み(verified)」の機種のみ。
                -- 為替換算などの未検証価格しか持たない機種は順位に載せない
                WHEN j.verification_status != 'verified' OR j.price_jpy IS NULL THEN NULL
                ELSE j.price_jpy
            END as confirmed_price_jpy,
            CASE
                WHEN j.availability IN ('not_available', 'discontinued')
                     OR j.verification_status = 'unavailable' THEN NULL
                ELSE COALESCE(j.price_jpy, CAST(ROUND(s.price_usd * 155.0) AS INTEGER))
            END as est_price_jpy,
            s.score_tone,
            s.score_tone_sub,
            s.score_tone_eq,
            s.score_tone_sub_eq
        FROM speakers s
        LEFT JOIN japan_market j ON s.id = j.speaker_id
    """)
    rows = cursor.fetchall()

    # 回帰は確定価格のみで当てる（推定値を混ぜると基準がぶれるため）
    prices = [r["confirmed_price_jpy"] for r in rows]
    scores_tone = [r["score_tone"] for r in rows]
    scores_tone_sub = [r["score_tone_sub"] for r in rows]
    scores_tone_eq = [r["score_tone_eq"] for r in rows]
    scores_tone_sub_eq = [r["score_tone_sub_eq"] for r in rows]

    # Calculate regression line for each metric
    reg_tone = calculate_regression(prices, scores_tone)
    reg_sub = calculate_regression(prices, scores_tone_sub)
    reg_eq = calculate_regression(prices, scores_tone_eq)
    reg_sub_eq = calculate_regression(prices, scores_tone_sub_eq)

    print(f"Regression Models (Score = a * log10(Price) + b):")
    print(f"  Tone:        a={reg_tone[0]:.3f}, b={reg_tone[1]:.3f}, R^2={reg_tone[2]:.3f}")
    print(f"  Tone w/Sub:  a={reg_sub[0]:.3f}, b={reg_sub[1]:.3f}, R^2={reg_sub[2]:.3f}")
    print(f"  Tone w/EQ:   a={reg_eq[0]:.3f}, b={reg_eq[1]:.3f}, R^2={reg_eq[2]:.3f}")
    print(f"  Tone w/Both: a={reg_sub_eq[0]:.3f}, b={reg_sub_eq[1]:.3f}, R^2={reg_sub_eq[2]:.3f}")

    now = datetime.now().isoformat()

    def calc_cpi(price, score, base_score=2.0):
        """
        Intuitive Cost-Performance Index (CPI):
        (Score - Base) / sqrt(Price / 10,000)

        - Highly rewards affordable speakers (10k - 150k JPY) that achieve great acoustic scores.
        - Strongly penalizes ultra-expensive speakers (300k - 2M+ JPY) so they cannot dominate CP.
        - Ignores poor sounding speakers (score < base_score).
        """
        if price and price > 0 and score is not None and not math.isnan(score):
            effective_score = float(score)
            if effective_score <= base_score:
                return 0.0
            # Square root of price normalized to 10,000 JPY
            price_norm = math.sqrt(price / 10000.0)
            cpi = (effective_score - base_score) / price_norm
            return round(cpi, 2)
        return None

    def calc_residual(price, score, a, b):
        if price and price > 0 and score is not None and not math.isnan(score):
            expected = a * math.log10(price) + b
            return round(score - expected, 2)
        return None

    count = 0
    for r in rows:
        sid = r["id"]
        p = r["confirmed_price_jpy"]   # ランキング用（確定価格のみ）
        p_est = r["est_price_jpy"]     # 検証キュー用（為替換算の概算を含む）

        # Intuitive Cost-Performance Index (CPI)
        # Base scores: Tone=2.0, w/Sub=3.0, w/EQ=3.0, w/Both=4.0
        cp_tone = calc_cpi(p, r["score_tone"], base_score=2.0)
        cp_tone_sub = calc_cpi(p, r["score_tone_sub"], base_score=3.0)
        cp_tone_eq = calc_cpi(p, r["score_tone_eq"], base_score=3.0)
        cp_tone_sub_eq = calc_cpi(p, r["score_tone_sub_eq"], base_score=4.0)

        # 参考CPI（未確定機種の調査優先度付け専用。ランキングには使わない）
        cp_tone_est = calc_cpi(p_est, r["score_tone"], base_score=2.0)
        cp_tone_sub_est = calc_cpi(p_est, r["score_tone_sub"], base_score=3.0)
        cp_tone_eq_est = calc_cpi(p_est, r["score_tone_eq"], base_score=3.0)
        cp_tone_sub_eq_est = calc_cpi(p_est, r["score_tone_sub_eq"], base_score=4.0)

        # Residuals for reference
        res_tone = calc_residual(p, r["score_tone"], *reg_tone[:2])
        res_sub = calc_residual(p, r["score_tone_sub"], *reg_sub[:2])
        res_eq = calc_residual(p, r["score_tone_eq"], *reg_eq[:2])
        res_sub_eq = calc_residual(p, r["score_tone_sub_eq"], *reg_sub_eq[:2])

        cursor.execute("""
            INSERT INTO cost_performance (
                speaker_id, cp_tone, cp_tone_sub, cp_tone_eq, cp_tone_sub_eq,
                cp_tone_ratio, cp_tone_sub_ratio, cp_tone_eq_ratio, cp_tone_sub_eq_ratio,
                cp_tone_est, cp_tone_sub_est, cp_tone_eq_est, cp_tone_sub_eq_est,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(speaker_id) DO UPDATE SET
                cp_tone = excluded.cp_tone,
                cp_tone_sub = excluded.cp_tone_sub,
                cp_tone_eq = excluded.cp_tone_eq,
                cp_tone_sub_eq = excluded.cp_tone_sub_eq,
                cp_tone_ratio = excluded.cp_tone_ratio,
                cp_tone_sub_ratio = excluded.cp_tone_sub_ratio,
                cp_tone_eq_ratio = excluded.cp_tone_eq_ratio,
                cp_tone_sub_eq_ratio = excluded.cp_tone_sub_eq_ratio,
                cp_tone_est = excluded.cp_tone_est,
                cp_tone_sub_est = excluded.cp_tone_sub_est,
                cp_tone_eq_est = excluded.cp_tone_eq_est,
                cp_tone_sub_eq_est = excluded.cp_tone_sub_eq_est,
                updated_at = excluded.updated_at
        """, (
            sid, cp_tone, cp_tone_sub, cp_tone_eq, cp_tone_sub_eq,
            res_tone, res_sub, res_eq, res_sub_eq,
            cp_tone_est, cp_tone_sub_est, cp_tone_eq_est, cp_tone_sub_eq_est,
            now
        ))
        count += 1

    conn.commit()
    conn.close()
    print(f"Cost performance computed and updated for {count} speakers.")

    return {
        "reg_tone": reg_tone,
        "reg_sub": reg_sub,
        "reg_eq": reg_eq,
        "reg_sub_eq": reg_sub_eq
    }

if __name__ == "__main__":
    update_cost_performance()
