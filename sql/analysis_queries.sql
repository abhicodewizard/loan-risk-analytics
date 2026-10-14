-- ============================================================================
-- LOAN PORTFOLIO & CREDIT RISK ANALYTICS - 22 business queries (SQLite)
-- Run all:  python src/04_run_sql_analysis.py   (results -> outputs/query_results/)
-- "Matured" = loans with 12+ months on book, so default rates are comparable across segments.
-- ============================================================================

-- name: q01_portfolio_kpis
-- Q: What is the overall health of the lending book?
SELECT COUNT(*)                                                                     AS applications,
       SUM(is_disbursed)                                                            AS disbursed_loans,
       ROUND(100.0 * SUM(is_disbursed) / COUNT(*), 1)                               AS approval_rate_pct,
       ROUND(SUM(CASE WHEN is_disbursed = 1 THEN loan_amount END) / 1e7, 1)         AS disbursed_cr,
       ROUND(AVG(CASE WHEN is_disbursed = 1 THEN loan_amount END), 0)               AS avg_ticket_size,
       ROUND(SUM(CASE WHEN loan_status <> 'Closed' THEN outstanding_principal END) / 1e7, 1) AS outstanding_cr,
       SUM(is_npa)                                                                  AS npa_loans,
       ROUND(100.0 * SUM(is_npa) / SUM(is_disbursed), 2)                            AS npa_rate_by_count_pct,
       ROUND(100.0 * SUM(CASE WHEN is_npa = 1 THEN outstanding_principal END)
                   / SUM(CASE WHEN loan_status <> 'Closed' THEN outstanding_principal END), 2) AS gross_npa_pct,
       ROUND(100.0 * SUM(CASE WHEN is_delinquent = 1 THEN outstanding_principal END)
                   / SUM(CASE WHEN loan_status <> 'Closed' THEN outstanding_principal END), 2) AS sma_30_89_pct,
       ROUND(SUM(credit_loss_est) / 1e7, 2)                                         AS est_credit_loss_cr,
       ROUND(AVG(CASE WHEN is_disbursed = 1 THEN interest_rate END), 2)             AS avg_interest_rate
FROM vw_loans;

-- name: q02_monthly_funnel
-- Q: How do applications, approvals and disbursals trend month by month? (LAG)
WITH m AS (
    SELECT app_month, COUNT(*) AS applications, SUM(is_disbursed) AS approved,
           ROUND(SUM(CASE WHEN is_disbursed = 1 THEN loan_amount END) / 1e7, 2) AS disbursed_cr
    FROM vw_loans GROUP BY app_month
)
SELECT app_month, applications, approved,
       ROUND(100.0 * approved / applications, 1) AS approval_rate_pct,
       disbursed_cr,
       ROUND(100.0 * (applications - LAG(applications) OVER (ORDER BY app_month)) / LAG(applications) OVER (ORDER BY app_month), 1) AS mom_application_growth_pct
FROM m ORDER BY app_month;

-- name: q03_approval_by_credit_score
-- Q: Is credit policy actually tracking bureau score?
SELECT score_band, COUNT(*) AS applications,
       ROUND(100.0 * SUM(is_disbursed) / COUNT(*), 1) AS approval_rate_pct,
       ROUND(AVG(foir), 3) AS avg_foir
FROM vw_loans GROUP BY score_band ORDER BY score_band;

-- name: q04_approval_by_foir_band
-- Q: How does the obligation-to-income ratio drive approvals?
SELECT CASE WHEN foir < .30 THEN '1. Below 30%' WHEN foir < .40 THEN '2. 30-40%' WHEN foir < .50 THEN '3. 40-50%'
            WHEN foir < .60 THEN '4. 50-60%' ELSE '5. 60%+' END AS foir_band,
       COUNT(*) AS applications,
       ROUND(100.0 * SUM(is_disbursed) / COUNT(*), 1) AS approval_rate_pct
FROM vw_loans GROUP BY foir_band ORDER BY foir_band;

-- name: q05_rejection_reasons
-- Q: Why are applications rejected? (share via SUM() OVER)
SELECT rejection_reason, COUNT(*) AS rejected,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM vw_loans WHERE decision = 'Rejected'
GROUP BY rejection_reason ORDER BY rejected DESC;

-- name: q06_npa_by_credit_score
-- Q: Does the bureau score separate good borrowers from bad ones? (matured loans only)
SELECT score_band, COUNT(*) AS matured_loans, SUM(is_npa) AS npa_loans,
       ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct,
       ROUND(AVG(interest_rate), 2) AS avg_interest_rate
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY score_band ORDER BY score_band;

-- name: q07_npa_by_product
-- Q: Which products carry the most credit risk and how much do we lose after collateral (LGD)?
SELECT product, secured, lgd, COUNT(*) AS matured_loans, SUM(is_npa) AS npa_loans,
       ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct,
       ROUND(SUM(credit_loss_est) / 1e7, 2) AS est_credit_loss_cr
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY product, secured, lgd ORDER BY npa_rate_pct DESC;

-- name: q08_npa_by_employment_and_channel
-- Q: Which employment-type x sourcing-channel combinations are riskiest?
SELECT employment_type, channel, COUNT(*) AS matured_loans,
       ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY employment_type, channel ORDER BY npa_rate_pct DESC;

-- name: q09_npa_by_foir_band
-- Q: At what obligation level does risk accelerate?
SELECT CASE WHEN foir < .30 THEN '1. Below 30%' WHEN foir < .40 THEN '2. 30-40%' WHEN foir < .50 THEN '3. 40-50%'
            WHEN foir < .60 THEN '4. 50-60%' ELSE '5. 60%+' END AS foir_band,
       COUNT(*) AS matured_loans,
       ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY foir_band ORDER BY foir_band;

-- name: q10_vintage_analysis
-- Q: How quickly do loans from each disbursal quarter go bad? (cohort / vintage curve at MOB 6 and 12)
SELECT disb_quarter, COUNT(*) AS loans,
       SUM(is_npa = 1 AND default_mob <= 6)  AS npa_by_mob6,
       SUM(is_npa = 1 AND default_mob <= 12) AS npa_by_mob12,
       ROUND(100.0 * SUM(is_npa = 1 AND default_mob <= 6)  / COUNT(*), 2) AS npa_rate_mob6_pct,
       ROUND(100.0 * SUM(is_npa = 1 AND default_mob <= 12) / COUNT(*), 2) AS npa_rate_mob12_pct
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY disb_quarter ORDER BY disb_quarter;

-- name: q11_monthly_npa_formation
-- Q: How many new NPAs are forming each month and what exposure do they carry?
SELECT npa_month, COUNT(*) AS new_npas, ROUND(SUM(outstanding_principal) / 1e7, 2) AS exposure_cr,
       ROUND(AVG(SUM(outstanding_principal)) OVER (ORDER BY npa_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) / 1e7, 2) AS exposure_3m_avg_cr
FROM vw_loans WHERE is_npa = 1
GROUP BY npa_month ORDER BY npa_month;

-- name: q12_portfolio_ageing
-- Q: What does the live book look like by days-past-due bucket?
SELECT dpd_bucket, COUNT(*) AS loans, ROUND(SUM(outstanding_principal) / 1e7, 2) AS outstanding_cr,
       ROUND(100.0 * SUM(outstanding_principal) / SUM(SUM(outstanding_principal)) OVER (), 2) AS share_of_book_pct
FROM vw_loans WHERE is_disbursed = 1 AND loan_status <> 'Closed'
GROUP BY dpd_bucket ORDER BY dpd_bucket;

-- name: q13_early_warning_by_product
-- Q: Where is stress building before it becomes NPA? (30-89 DPD balances)
SELECT product,
       SUM(is_delinquent) AS delinquent_loans,
       ROUND(SUM(CASE WHEN is_delinquent = 1 THEN outstanding_principal END) / 1e7, 2) AS delinquent_cr,
       ROUND(100.0 * SUM(CASE WHEN is_delinquent = 1 THEN outstanding_principal END)
                   / SUM(outstanding_principal), 2) AS pct_of_product_book,
       ROUND(100.0 * SUM(CASE WHEN is_npa = 1 THEN outstanding_principal END) / SUM(outstanding_principal), 2) AS gnpa_pct
FROM vw_loans WHERE is_disbursed = 1 AND loan_status <> 'Closed'
GROUP BY product ORDER BY pct_of_product_book DESC;

-- name: q14_city_risk_ranking
-- Q: Which branches/cities have the highest NPA rate? (RANK)
SELECT city, region, COUNT(*) AS matured_loans,
       ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct,
       RANK() OVER (ORDER BY 1.0 * SUM(is_npa) / COUNT(*) DESC) AS risk_rank,
       ROUND(SUM(CASE WHEN loan_status <> 'Closed' THEN outstanding_principal END) / 1e7, 1) AS outstanding_cr
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY city, region ORDER BY risk_rank;

-- name: q15_product_risk_adjusted_profit
-- Q: After credit losses, which products actually make money?
SELECT product,
       ROUND(SUM(loan_amount) / 1e7, 1)                                    AS disbursed_cr,
       ROUND(SUM(interest_earned) / 1e7, 2)                                AS interest_earned_cr,
       ROUND(SUM(processing_fee) / 1e7, 2)                                 AS processing_fee_cr,
       ROUND(SUM(credit_loss_est) / 1e7, 2)                                AS credit_loss_cr,
       ROUND((SUM(interest_earned) + SUM(processing_fee) - SUM(credit_loss_est)) / 1e7, 2) AS risk_adjusted_income_cr,
       ROUND(100.0 * (SUM(interest_earned) + SUM(processing_fee) - SUM(credit_loss_est)) / SUM(loan_amount), 2) AS return_on_disbursed_pct
FROM vw_loans WHERE is_disbursed = 1
GROUP BY product ORDER BY return_on_disbursed_pct DESC;

-- name: q16_channel_economics
-- Q: Is the DSA (agent) channel worth it once defaults are counted?
SELECT channel, COUNT(*) AS applications,
       ROUND(100.0 * SUM(is_disbursed) / COUNT(*), 1) AS approval_rate_pct,
       SUM(is_disbursed) AS disbursed_loans,
       ROUND(100.0 * SUM(CASE WHEN mob >= 12 THEN is_npa END) / SUM(CASE WHEN mob >= 12 THEN 1 END), 2) AS npa_rate_matured_pct,
       ROUND((SUM(interest_earned) + SUM(processing_fee) - SUM(credit_loss_est)) / 1e7, 2) AS risk_adjusted_income_cr,
       ROUND(100.0 * (SUM(interest_earned) + SUM(processing_fee) - SUM(credit_loss_est)) / SUM(CASE WHEN is_disbursed = 1 THEN loan_amount END), 2) AS return_on_disbursed_pct
FROM vw_loans GROUP BY channel ORDER BY return_on_disbursed_pct DESC;

-- name: q17_npa_by_income_band
-- Q: Is risk concentrated in low-income borrowers?
SELECT income_band, COUNT(*) AS matured_loans, ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct,
       ROUND(AVG(loan_amount), 0) AS avg_ticket
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY income_band ORDER BY income_band;

-- name: q18_npa_by_age_band
-- Q: How does age relate to repayment behaviour?
SELECT age_band, COUNT(*) AS matured_loans, ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY age_band ORDER BY age_band;

-- name: q19_policy_simulation
-- Q: What if we tightened policy to score >= 650 and FOIR <= 55%? Bad loans avoided vs good business lost.
WITH l AS (
    SELECT *, CASE WHEN (credit_score < 650 OR foir > .55) THEN 1 ELSE 0 END AS would_reject
    FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
)
SELECT COUNT(*)                                                                AS matured_loans,
       SUM(would_reject)                                                       AS loans_rejected_under_new_policy,
       ROUND(100.0 * SUM(would_reject) / COUNT(*), 1)                          AS pct_of_book_rejected,
       SUM(is_npa = 1 AND would_reject = 1)                                    AS npas_avoided,
       ROUND(100.0 * SUM(is_npa = 1 AND would_reject = 1) / SUM(is_npa), 1)    AS pct_of_all_npas_avoided,
       SUM(is_npa = 0 AND would_reject = 1)                                    AS good_loans_lost,
       ROUND(SUM(CASE WHEN would_reject = 1 THEN loan_amount END) / 1e7, 1)    AS business_foregone_cr,
       ROUND(SUM(CASE WHEN would_reject = 1 THEN credit_loss_est END) / 1e7, 2) AS credit_loss_avoided_cr
FROM l;

-- name: q20_stress_vintage_comparison
-- Q: Was the Jun-Dec 2024 vintage really weaker than the rest?
SELECT CASE WHEN disbursed_date BETWEEN '2024-06-01' AND '2024-12-31' THEN 'Jun-Dec 2024 vintage' ELSE 'All other vintages' END AS cohort,
       COUNT(*) AS loans,
       ROUND(100.0 * SUM(is_npa = 1 AND default_mob <= 12) / COUNT(*), 2) AS npa_rate_by_mob12_pct,
       ROUND(AVG(credit_score), 0) AS avg_credit_score,
       ROUND(AVG(foir), 3) AS avg_foir
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY cohort;

-- name: q21_risk_matrix_score_x_foir
-- Q: Which score x FOIR cells should be priced higher or declined? (segments with 80+ loans)
SELECT score_band,
       CASE WHEN foir < .40 THEN 'FOIR < 40%' WHEN foir < .55 THEN 'FOIR 40-55%' ELSE 'FOIR 55%+' END AS foir_group,
       COUNT(*) AS matured_loans, ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_pct
FROM vw_loans WHERE is_disbursed = 1 AND mob >= 12
GROUP BY score_band, foir_group HAVING COUNT(*) >= 80
ORDER BY npa_rate_pct DESC;

-- name: q22_top_cities_by_disbursal
-- Q: Where is the money going and is growth coming with quality? (RANK on disbursal vs risk)
SELECT city, ROUND(SUM(loan_amount) / 1e7, 1) AS disbursed_cr,
       RANK() OVER (ORDER BY SUM(loan_amount) DESC) AS disbursal_rank,
       ROUND(100.0 * SUM(is_npa) / COUNT(*), 2) AS npa_rate_all_loans_pct
FROM vw_loans WHERE is_disbursed = 1
GROUP BY city ORDER BY disbursal_rank;
