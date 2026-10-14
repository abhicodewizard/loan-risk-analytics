-- Business-logic layer: every risk metric is derived in SQL.  As-of date = 2025-12-31.
--   FOIR          = (existing EMIs + new EMI) / monthly income   (fixed-obligation-to-income ratio)
--   MOB           = months on book at the as-of date
--   NPA           = loan with 90+ days past due (RBI definition)
--   credit_loss   = outstanding principal on NPA loans x LGD of the product (secured loans lose less)
--   interest_earned (estimate) = EMI x months paid - principal repaid

CREATE VIEW vw_loans_base AS
SELECT f.*, b.city, b.region, p.product, p.secured, p.lgd,
       CASE WHEN f.decision = 'Approved' THEN 1 ELSE 0 END                          AS is_disbursed,
       strftime('%Y-%m', f.application_date)                                        AS app_month,
       strftime('%Y', f.disbursed_date) || '-Q' || ((CAST(strftime('%m', f.disbursed_date) AS INTEGER) + 2) / 3) AS disb_quarter,
       ROUND((f.existing_emi + f.emi) / f.monthly_income, 3)                        AS foir,
       CASE WHEN f.disbursed_date IS NULL THEN NULL
            ELSE CAST((julianday('2025-12-31') - julianday(f.disbursed_date)) / 30.4 AS INTEGER) END AS mob,
       CASE WHEN f.credit_score IS NULL THEN '7. No score'
            WHEN f.credit_score < 600 THEN '1. Below 600'  WHEN f.credit_score < 650 THEN '2. 600-649'
            WHEN f.credit_score < 700 THEN '3. 650-699'    WHEN f.credit_score < 750 THEN '4. 700-749'
            WHEN f.credit_score < 800 THEN '5. 750-799'    ELSE '6. 800+' END       AS score_band,
       CASE WHEN f.monthly_income < 25000 THEN '1. Below 25k' WHEN f.monthly_income < 50000 THEN '2. 25k-50k'
            WHEN f.monthly_income < 100000 THEN '3. 50k-1L'   ELSE '4. Above 1L' END AS income_band,
       CASE WHEN f.customer_age <= 25 THEN '1. 21-25' WHEN f.customer_age <= 35 THEN '2. 26-35'
            WHEN f.customer_age <= 45 THEN '3. 36-45' ELSE '4. 46+' END             AS age_band,
       CASE WHEN f.loan_status = 'NPA' THEN 1 ELSE 0 END                            AS is_npa,
       CASE WHEN f.loan_status = 'Delinquent 30-89' THEN 1 ELSE 0 END               AS is_delinquent,
       CASE WHEN f.loan_status IS NULL THEN NULL
            WHEN f.loan_status = 'Closed' THEN 'Closed'
            WHEN f.dpd >= 90 THEN '4. NPA (90+)' WHEN f.dpd >= 30 THEN '3. SMA (30-89)'
            WHEN f.dpd >= 1 THEN '2. Early (1-29)' ELSE '1. Standard (0)' END        AS dpd_bucket
FROM fact_applications f
JOIN dim_branch  b ON b.branch_id  = f.branch_id
JOIN dim_product p ON p.product_id = f.product_id;

CREATE VIEW vw_loans AS
SELECT t.*,
       CASE WHEN t.is_npa = 1 THEN t.outstanding_principal * t.lgd ELSE 0 END       AS credit_loss_est,
       CASE WHEN t.is_disbursed = 1 THEN t.loan_amount * 0.01 ELSE 0 END            AS processing_fee,
       CASE WHEN t.is_disbursed = 0 THEN 0
            ELSE MAX(0, t.emi * (CASE WHEN t.is_npa = 1 THEN t.default_mob ELSE MIN(t.tenure_months, t.mob) END)
                        - (t.loan_amount - COALESCE(t.outstanding_principal, 0))) END AS interest_earned,
       CASE WHEN t.is_npa = 1 THEN strftime('%Y-%m', date(t.disbursed_date, '+' || CAST(t.default_mob AS INTEGER) || ' months')) END AS npa_month
FROM vw_loans_base t;
