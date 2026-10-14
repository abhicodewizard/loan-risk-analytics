# Power BI Guide

Build the dashboard in Power BI Desktop from the CSVs in `powerbi/data/`.

## 1. Load and model
Load `fact_loans.csv`, `dim_branch.csv`, `dim_product.csv`, `dim_date.csv`. Set `application_date` (fact) and `date_key` (dim_date) to **Date** type, then create relationships (many-to-one, single direction):

| From (fact_loans) | To |
|---|---|
| branch_id | dim_branch[branch_id] |
| product_id | dim_product[product_id] |
| application_date | dim_date[date_key] |

## 2. DAX measures
```DAX
Applications = COUNTROWS(fact_loans)
Disbursed Loans = CALCULATE(COUNTROWS(fact_loans), fact_loans[is_disbursed] = 1)
Approval Rate % = DIVIDE([Disbursed Loans], [Applications])
Disbursed Cr = DIVIDE(CALCULATE(SUM(fact_loans[loan_amount]), fact_loans[is_disbursed] = 1), 10000000)

Live Book = CALCULATE(SUM(fact_loans[outstanding_principal]), fact_loans[is_disbursed] = 1, fact_loans[loan_status] <> "Closed")
Gross NPA % = DIVIDE(CALCULATE(SUM(fact_loans[outstanding_principal]), fact_loans[is_npa] = 1), [Live Book])
SMA 30-89 % = DIVIDE(CALCULATE(SUM(fact_loans[outstanding_principal]), fact_loans[is_delinquent] = 1), [Live Book])

Matured Loans = CALCULATE(COUNTROWS(fact_loans), fact_loans[is_disbursed] = 1, fact_loans[mob] >= 12)
NPA Rate (Matured) = DIVIDE(CALCULATE(COUNTROWS(fact_loans), fact_loans[is_npa] = 1, fact_loans[mob] >= 12), [Matured Loans])

Credit Loss Cr = DIVIDE(SUM(fact_loans[credit_loss_est]), 10000000)
Interest Earned Cr = DIVIDE(SUM(fact_loans[interest_earned]), 10000000)
Fees Cr = DIVIDE(SUM(fact_loans[processing_fee]), 10000000)
Risk Adjusted Income Cr = [Interest Earned Cr] + [Fees Cr] - [Credit Loss Cr]
Return on Disbursed % = DIVIDE([Risk Adjusted Income Cr], [Disbursed Cr])

Applications Prev Month = CALCULATE([Applications], DATEADD(dim_date[date_key], -1, MONTH))
MoM Growth % = DIVIDE([Applications] - [Applications Prev Month], [Applications Prev Month])
```
Check: Applications = 30,000, Approval Rate = 60.0%, Gross NPA % = 5.04% (same as Excel and SQL).

## 3. Suggested pages
1. **Executive summary:** KPI cards (Applications, Approval %, Disbursed Cr, Live Book, Gross NPA %, SMA %), monthly funnel (columns + line), product donut, slicers for year, product, region.
2. **Risk deep-dive:** NPA rate by score band, NPA rate by FOIR band, score x FOIR matrix (conditional-formatted), vintage line chart by disbursal quarter.
3. **Segments and geography:** NPA rate by channel and employment type, city bar chart sorted by NPA rate, product risk-adjusted return, tooltip page with loan counts.

Add a screenshot of your finished dashboard to the README (`outputs/images/powerbi_dashboard.png`).
