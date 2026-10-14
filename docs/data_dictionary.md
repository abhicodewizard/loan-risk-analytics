# Data Dictionary

## fact_applications (one row per loan application, 30,000 rows)
| Column | Description |
|---|---|
| application_id | Unique application ID (LN2000001...) |
| application_date / disbursed_date | Date applied / date funds were released (NULL if rejected) |
| branch_id, product_id | Keys to dim_branch and dim_product |
| customer_age, gender, employment_type | Applicant profile (Salaried / Self-Employed / Business Owner) |
| monthly_income | Gross monthly income in Rs |
| credit_score | Bureau score 300-900; NULL = new-to-credit or invalid score |
| existing_emi | Monthly EMIs already being paid on other loans |
| loan_amount, tenure_months, interest_rate, emi | Requested / sanctioned loan terms |
| channel | Branch, Online or DSA (direct selling agent) |
| decision, rejection_reason | Approved / Rejected and the main reason |
| loan_status | Current, Closed, Delinquent 30-89, NPA (blank if rejected) |
| dpd | Days past due at 31-Dec-2025 |
| default_mob | Months on book at which the loan became NPA |
| outstanding_principal | Principal still owed at 31-Dec-2025 (0 if closed) |
| dq_flags | Data-quality flags added during cleaning (age_imputed, income_imputed) |

## Derived columns (SQL view vw_loans)
| Column | Definition |
|---|---|
| foir | (existing_emi + emi) / monthly_income |
| mob | Months on book at the 31-Dec-2025 as-of date |
| score_band, income_band, age_band | Banded versions of score, income, age |
| dpd_bucket | Standard (0), Early (1-29), SMA (30-89), NPA (90+), Closed |
| is_disbursed, is_npa, is_delinquent | 0/1 flags |
| credit_loss_est | NPA outstanding x product LGD |
| interest_earned | Estimated: EMI x months paid - principal repaid |
| processing_fee | 1% of loan amount on disbursal |

## Dimensions
- **dim_branch**: branch_id, city, region (15 cities)
- **dim_product**: product_id, product, secured flag, assumed LGD (Personal 65%, Auto 35%, Home 25%, Business 65%, Education 55%)
- **dim_date**: calendar attributes for 2023-01-01 to 2026-01-31
