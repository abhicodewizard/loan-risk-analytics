"""
Step 2 - Clean the raw applications file with pandas and log every fix in a data-quality report.

Run:  python src/02_clean_data.py
"""
import re
import shutil
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RAW / "applications_raw.csv", dtype=str)
branches, products = pd.read_csv(RAW / "branches.csv"), pd.read_csv(RAW / "products.csv")
report = []


def log(issue, rows, action):
    report.append({"issue": issue, "rows_affected": int(rows), "action_taken": action})
    print(f"  - {issue}: {int(rows):,} rows -> {action}")


print(f"Raw rows: {len(df):,}")
n = df.duplicated("application_id").sum()
df = df.drop_duplicates("application_id", keep="first")
log("Duplicate application_id", n, "kept first occurrence")

for c in ["city", "employment_type", "product", "decision", "loan_status", "channel", "gender"]:
    df[c] = df[c].str.strip()

# city ------------------------------------------------------------------------------
CITY = {"new delhi": "Delhi", "gurgaon": "Gurugram", "bangalore": "Bengaluru", "bombay": "Mumbai", "calcutta": "Kolkata", "madras": "Chennai"}
valid = {c.lower(): c for c in branches.city}
new = df.city.map(lambda x: CITY.get(x.lower(), valid.get(x.lower())))
log("Inconsistent city names", (new != df.city).sum(), "mapped to standard branch cities")
df["city"] = new

# employment / product -------------------------------------------------------------
EMP = {"salaried": "Salaried", "self employed": "Self-Employed", "self-employed": "Self-Employed", "business": "Business Owner", "business owner": "Business Owner"}
new = df.employment_type.str.lower().map(EMP)
log("Employment type spelling variants", (new != df.employment_type).sum(), "standardised to 3 categories")
df["employment_type"] = new
new = df["product"].str.title()
log("Product name casing / spaces", (new != df["product"]).sum(), "standardised to Title Case")
df["product"] = new


# dates ---------------------------------------------------------------------------------
def pdate(s):
    if pd.isna(s):
        return pd.NaT
    s = s.strip()
    for pat, f in ((r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y"), (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y")):
        if re.fullmatch(pat, s):
            return pd.to_datetime(s, format=f)
    return pd.NaT


log("Mixed date formats", (~df.application_date.str.fullmatch(r"\d{4}-\d{2}-\d{2}")).sum(), "parsed ISO, DD-MM-YYYY and DD/MM/YYYY into one format")
df["application_date"], df["disbursed_date"] = df.application_date.map(pdate), df.disbursed_date.map(pdate)

# amounts as text ------------------------------------------------------------------------
txt = df.loan_amount.str.contains(r"[^\d.]", regex=True)
log("Loan amount stored as text (Rs., INR, commas)", txt.sum(), "stripped symbols and converted to numeric")
df["loan_amount"] = pd.to_numeric(df.loan_amount.str.replace(r"[^\d.]", "", regex=True))
for c in ["customer_age", "monthly_income", "credit_score", "existing_emi", "tenure_months", "interest_rate", "emi", "dpd",
          "default_mob", "outstanding_principal"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# invalid values -------------------------------------------------------------------------
bad = (df.customer_age < 18) | (df.customer_age > 80)
log("Impossible ages (<18 or >80)", bad.sum(), "set to NULL and imputed with median age")
df["flag_age_imputed"] = bad
df.loc[bad, "customer_age"] = np.nan
df["customer_age"] = df.customer_age.fillna(df.customer_age.median()).astype(int)

bad = df.credit_score.notna() & ((df.credit_score < 300) | (df.credit_score > 900))
log("Invalid credit scores (0, -1, 999)", bad.sum(), "set to NULL (treated as no bureau score)")
df.loc[bad, "credit_score"] = np.nan
log("Missing credit score (new-to-credit)", df.credit_score.isna().sum(), "kept NULL - analysed as 'No score' band, never imputed")

miss = df.monthly_income.isna()
med = df.groupby("employment_type").monthly_income.transform("median")
log("Missing monthly income", miss.sum(), "imputed with median income of same employment type (flagged)")
df["flag_income_imputed"] = miss
df.loc[miss, "monthly_income"] = med[miss]

# keys + flags ---------------------------------------------------------------------------
df["branch_id"] = df.city.map(dict(zip(branches.city, branches.branch_id)))
df["product_id"] = df["product"].map(dict(zip(products["product"], products.product_id)))
assert df.branch_id.notna().all() and df.product_id.notna().all()
df["dq_flags"] = (np.where(df.flag_age_imputed, "age_imputed;", "") + np.where(df.flag_income_imputed, "income_imputed;", ""))
df["dq_flags"] = df.dq_flags.str.rstrip(";")

cols = ["application_id", "application_date", "disbursed_date", "branch_id", "product_id", "customer_age", "gender", "employment_type",
        "monthly_income", "credit_score", "existing_emi", "loan_amount", "tenure_months", "interest_rate", "emi", "channel", "decision",
        "rejection_reason", "loan_status", "dpd", "default_mob", "outstanding_principal", "dq_flags"]
out = df[cols].copy()
for c in ["application_date", "disbursed_date"]:
    out[c] = out[c].dt.strftime("%Y-%m-%d")
out.to_csv(PROC / "applications_clean.csv", index=False)
for f in ["branches.csv", "products.csv"]:
    shutil.copy(RAW / f, PROC / f)
pd.DataFrame(report).to_csv(PROC / "data_quality_report.csv", index=False)
print(f"Clean rows: {len(out):,} -> data/processed/applications_clean.csv (+ data_quality_report.csv)")
