"""
Step 1 - Generate a SIMULATED retail-lending dataset (30,000 loan applications, Jan 2023 - Sep 2025).

Real bank data is confidential, so this builds a realistic synthetic portfolio (applications, approvals,
disbursals, repayment behaviour, delinquency, NPAs) and then makes the RAW file messy on purpose so the
cleaning step (02) has real work to do.

Run:  python src/01_generate_data.py     (seeded -> identical data every time)
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)
N = 30_000
AS_OF = pd.Timestamp("2025-12-31")
sig = lambda z: 1 / (1 + np.exp(-z))

CITIES = [("Delhi", "North", 16), ("Gurugram", "North", 7), ("Noida", "North", 6), ("Jaipur", "North", 4), ("Lucknow", "North", 3),
          ("Chandigarh", "North", 3), ("Meerut", "North", 2.5), ("Mumbai", "West", 15), ("Pune", "West", 7), ("Ahmedabad", "West", 5),
          ("Indore", "West", 3), ("Bengaluru", "South", 12), ("Hyderabad", "South", 8), ("Chennai", "South", 6), ("Kolkata", "East", 5)]
branches = pd.DataFrame(CITIES, columns=["city", "region", "w"])
branches.insert(0, "branch_id", [f"B{i:02d}" for i in range(1, len(branches) + 1)])
city_bias = {"Delhi": .05, "Gurugram": -.05, "Noida": .0, "Jaipur": .1, "Lucknow": .2, "Chandigarh": -.1, "Meerut": .15, "Mumbai": .05,
             "Pune": -.1, "Ahmedabad": -.05, "Indore": .05, "Bengaluru": -.1, "Hyderabad": -.05, "Chennai": -.05, "Kolkata": .25}

PRODUCTS = pd.DataFrame([  # product, secured, LGD, base rate, median amount, amount floor, cap, tenures
    ("Personal Loan", 0, .65, 12.5, 300_000, 50_000, 2_500_000, [12, 24, 36, 48, 60]),
    ("Auto Loan", 1, .35, 9.5, 500_000, 150_000, 2_500_000, [36, 48, 60, 84]),
    ("Home Loan", 1, .25, 8.7, 4_000_000, 1_000_000, 15_000_000, [120, 180, 240]),
    ("Business Loan", 0, .65, 14.0, 1_000_000, 200_000, 8_000_000, [24, 36, 48, 60]),
    ("Education Loan", 0, .55, 10.5, 600_000, 100_000, 3_000_000, [60, 84, 120]),
], columns=["product", "secured", "lgd", "base_rate", "median_amt", "amt_min", "amt_max", "tenures"])
PRODUCTS.insert(0, "product_id", [f"P{i}" for i in range(1, 6)])

# ---- applicant profile ----
age = np.clip(rng.normal(34, 8, N), 21, 62).astype(int)
gender = rng.choice(["Male", "Female"], N, p=[.63, .37])
emp = rng.choice(["Salaried", "Self-Employed", "Business Owner"], N, p=[.62, .25, .13])
pidx = rng.choice(5, N, p=[.40, .18, .17, .15, .10])
P = PRODUCTS.iloc[pidx].reset_index(drop=True)
inc_mult = np.array([1.0, 1.3, 2.4, 1.8, 1.1])[pidx]                 # home / business borrowers earn more
base_inc = np.select([emp == "Salaried", emp == "Self-Employed"], [45_000, 55_000], 90_000) * inc_mult
income = np.clip(rng.lognormal(np.log(base_inc), .50), 12_000, 900_000)
income = (np.round(income / 100) * 100).astype(float)
city = rng.choice(branches.city, N, p=branches.w / branches.w.sum())
channel = rng.choice(["Branch", "Online", "DSA"], N, p=[.35, .30, .35])
score = np.clip(rng.normal(715, 70, N) + 9 * np.log(income / 45_000), 300, 900).round().astype(float)
ntc = rng.random(N) < .07                                      # new-to-credit: no bureau score
existing_emi = np.where(rng.random(N) < .30, 0, income * rng.beta(2, 7, N) * .8).round(-1)

amt = P.median_amt.values * (income / (45_000 * inc_mult)) ** .8 * rng.lognormal(0, .40, N)
amt = (np.round(np.clip(amt, P.amt_min.values, P.amt_max.values) / 5_000) * 5_000)
tenure = np.array([rng.choice(t) for t in P.tenures])
rate = np.clip(P.base_rate.values + (750 - np.where(ntc, 650, score)) / 100 * 1.6 + rng.normal(0, .4, N), 7.5, 24).round(2)
r = rate / 1200
emi = (amt * r * (1 + r) ** tenure / ((1 + r) ** tenure - 1)).round(0)
foir = (existing_emi + emi) / income

appdate = pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 1004, N), unit="D")   # to 2025-09-30
appdate = pd.Series(appdate).sort_values().reset_index(drop=True)

# ---- credit decision ----
sc_eff = np.where(ntc, 650, score)
z = 0.55 + .012 * (sc_eff - 700) - 5.5 * (foir - .4) + np.where(P["product"].values == "Home Loan", .3, 0)
approved = rng.random(N) < sig(z)
reason = np.where(approved, None, np.select([sc_eff < 650, foir > .55, income < 20_000], ["Low credit score", "High FOIR / obligations", "Insufficient income"], "Policy / documentation"))
disb = appdate + pd.to_timedelta(rng.integers(3, 11, N), unit="D")

# ---- repayment behaviour ----
stress = np.where((disb >= "2024-06-01") & (disb <= "2024-12-31"), .40, 0)          # weak vintage
unsec = 1 - P.secured.values
zd = (-3.35 - .012 * (sc_eff - 720) + 3.2 * (foir - .4)
      + np.select([emp == "Self-Employed", emp == "Business Owner"], [.25, .15], 0)
      + np.select([channel == "DSA", channel == "Online"], [.45, .10], 0)
      + np.select([P["product"].values == "Personal Loan", P["product"].values == "Business Loan", P["product"].values == "Education Loan", P["product"].values == "Home Loan"], [.4, .5, .1, -.7], 0)
      + .004 * (tenure - 36) * unsec * (tenure <= 60) + stress + .3 * ntc + pd.Series(city).map(city_bias).values + rng.normal(0, .35, N))
will_default = approved & (rng.random(N) < sig(zd))
dmob = np.minimum(tenure - 1, 3 + np.ceil(rng.exponential(7, N)).astype(int))
mob = ((AS_OF - disb).dt.days / 30.4).astype(int).clip(lower=0)
prepaid = approved & ~will_default & (mob > 6) & (rng.random(N) < .06)
cure = approved & ~will_default & (rng.random(N) < .025)

status = np.full(N, None, dtype=object)
dpd = np.zeros(N, dtype=int)
npa = will_default & (dmob <= mob)
early = will_default & ~npa & (dmob - mob <= 2)
status[approved] = "Current"
status[approved & (mob >= tenure)] = "Closed"
status[prepaid] = "Closed"
status[early | cure] = "Delinquent 30-89"
status[npa] = "NPA"
dpd[npa] = rng.integers(91, 400, N)[npa]
dpd[(early | cure) & ~npa] = rng.integers(31, 90, N)[(early | cure) & ~npa]
cur = approved & (status == "Current") & (rng.random(N) < .06)
dpd[cur] = rng.integers(1, 30, N)[cur]

paid_k = np.where(npa, dmob, mob)
outst = np.where(status == "Closed", 0, amt * ((1 + r) ** tenure - (1 + r) ** np.minimum(paid_k, tenure)) / ((1 + r) ** tenure - 1)).round(0)
outst = np.where(approved, outst, np.nan)
default_mob = np.where(npa, dmob, np.nan)

df = pd.DataFrame({
    "application_id": [f"LN{2_000_001 + i}" for i in range(N)], "application_date": appdate, "customer_age": age, "gender": gender,
    "city": city, "employment_type": emp, "monthly_income": income, "credit_score": np.where(ntc, np.nan, score),
    "existing_emi": existing_emi, "product": P["product"].values, "loan_amount": amt, "tenure_months": tenure,
    "interest_rate": rate, "emi": emi, "channel": channel, "decision": np.where(approved, "Approved", "Rejected"),
    "rejection_reason": reason, "disbursed_date": np.where(approved, disb, pd.NaT), "loan_status": status, "dpd": np.where(approved, dpd, np.nan),
    "default_mob": default_mob, "outstanding_principal": outst})

# =============== make the RAW file messy on purpose ===============
raw = df.copy()


def fmt(s):
    s = pd.to_datetime(s)
    u = rng.random(len(s))
    out = np.where(u < .80, s.dt.strftime("%Y-%m-%d"), np.where(u < .94, s.dt.strftime("%d-%m-%Y"), s.dt.strftime("%d/%m/%Y")))
    return pd.Series(out, index=s.index).where(s.notna())


raw["application_date"], raw["disbursed_date"] = fmt(raw.application_date), fmt(raw.disbursed_date)
v = {"Delhi": ["New Delhi", "delhi"], "Gurugram": ["Gurgaon", "gurugram "], "Bengaluru": ["Bangalore", "BANGALORE"], "Mumbai": ["Bombay", "mumbai"],
     "Kolkata": ["Calcutta"], "Chennai": ["Madras"], "Pune": ["pune"], "Hyderabad": ["hyderabad "]}
for i in np.where(rng.random(N) < .08)[0]:
    if raw.at[i, "city"] in v:
        raw.at[i, "city"] = rng.choice(v[raw.at[i, "city"]])
ev = {"Salaried": ["salaried", "SALARIED", "Salaried "], "Self-Employed": ["Self Employed", "self-employed", "SELF EMPLOYED"], "Business Owner": ["Business", "business owner"]}
for i in np.where(rng.random(N) < .07)[0]:
    raw.at[i, "employment_type"] = rng.choice(ev[raw.at[i, "employment_type"]])
for i in np.where(rng.random(N) < .03)[0]:
    raw.at[i, "product"] = rng.choice([raw.at[i, "product"].lower(), raw.at[i, "product"] + " "])
raw["loan_amount"] = raw.loan_amount.astype(object)
for i in np.where(rng.random(N) < .015)[0]:
    a = int(raw.at[i, "loan_amount"])
    raw.at[i, "loan_amount"] = rng.choice([f"Rs. {a}", f"{a:,}", f"INR {a}"])
raw.loc[rng.random(N) < .015, "monthly_income"] = np.nan
bad = rng.random(N)
raw.loc[bad < .005, "credit_score"] = rng.choice([0, -1, 999], (bad < .005).sum())
raw.loc[(bad >= .005) & (bad < .007), "customer_age"] = rng.choice([-5, 0, 150, 220], ((bad >= .005) & (bad < .007)).sum())
raw = pd.concat([raw, raw.sample(frac=.01, random_state=3)]).sort_values("application_id", kind="stable").reset_index(drop=True)

raw.to_csv(RAW / "applications_raw.csv", index=False)
branches[["branch_id", "city", "region"]].to_csv(RAW / "branches.csv", index=False)
PRODUCTS[["product_id", "product", "secured", "lgd"]].to_csv(RAW / "products.csv", index=False)

ap = df[df.decision == "Approved"]
m = ap[ap.loan_status != "Closed"]
print(f"raw rows: {len(raw):,} | applications: {N:,}")
print(f"approval rate: {approved.mean():.1%} | disbursed: {len(ap):,} | NPA loans: {(ap.loan_status == 'NPA').sum():,} "
      f"({(ap.loan_status == 'NPA').mean():.1%} of disbursed) | NPA balance share: {m[m.loan_status == 'NPA'].outstanding_principal.sum() / m.outstanding_principal.sum():.1%}")
