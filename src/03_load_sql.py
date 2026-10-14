"""
Step 3 - Build the SQLite star schema, load the cleaned data, create the views,
and export star-schema CSVs for Power BI.

Run:  python src/03_load_sql.py
"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC, SQL, PBI = ROOT / "data" / "processed", ROOT / "sql", ROOT / "powerbi" / "data"
DB = ROOT / "database" / "loans.db"
DB.parent.mkdir(exist_ok=True)
PBI.mkdir(parents=True, exist_ok=True)
DB.unlink(missing_ok=True)

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript((SQL / "schema.sql").read_text())
pd.read_csv(PROC / "branches.csv").to_sql("dim_branch", conn, if_exists="append", index=False)
pd.read_csv(PROC / "products.csv").to_sql("dim_product", conn, if_exists="append", index=False)

d = pd.DataFrame({"k": pd.date_range("2023-01-01", "2026-01-31")})
pd.DataFrame({"date_key": d.k.dt.strftime("%Y-%m-%d"), "year": d.k.dt.year, "quarter": d.k.dt.quarter, "month": d.k.dt.month,
              "month_name": d.k.dt.strftime("%b"), "year_month": d.k.dt.strftime("%Y-%m"),
              "year_quarter": d.k.dt.year.astype(str) + "-Q" + d.k.dt.quarter.astype(str),
              "day_name": d.k.dt.strftime("%a"), "is_weekend": (d.k.dt.dayofweek >= 5).astype(int)}).to_sql("dim_date", conn, if_exists="append", index=False)

fact = pd.read_csv(PROC / "applications_clean.csv")
fact["dq_flags"] = fact.dq_flags.fillna("")
for c in ["dpd", "default_mob"]:
    fact[c] = fact[c].astype("Float64")
fact.to_sql("fact_applications", conn, if_exists="append", index=False)
conn.executescript((SQL / "views.sql").read_text())
conn.commit()

for t in ["dim_branch", "dim_product", "dim_date", "fact_applications"]:
    print(f"  {t:18s}{conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>8,} rows")
print("  foreign-key violations:", len(conn.execute("PRAGMA foreign_key_check").fetchall()))

pd.read_sql("SELECT * FROM vw_loans", conn).to_csv(PBI / "fact_loans.csv", index=False)
for t in ["dim_branch", "dim_product", "dim_date"]:
    pd.read_sql(f"SELECT * FROM {t}", conn).to_csv(PBI / f"{t}.csv", index=False)
print("Power BI CSVs exported ->", PBI.relative_to(ROOT))
conn.close()
