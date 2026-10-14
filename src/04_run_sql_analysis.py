"""
Step 4 - Execute every query in sql/analysis_queries.sql and save each result as a CSV.

Run:  python src/04_run_sql_analysis.py
"""
import re
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "query_results"
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*.csv"):
    f.unlink()
conn = sqlite3.connect(ROOT / "database" / "loans.db")
blocks = re.split(r"^-- name:\s*", (ROOT / "sql" / "analysis_queries.sql").read_text(), flags=re.M)[1:]
for b in blocks:
    name, _, sql = b.partition("\n")
    df = pd.read_sql(sql, conn)
    df.to_csv(OUT / f"{name.strip()}.csv", index=False)
    print(f"  {name.strip():42s}{len(df):>4} rows")
print(f"{len(blocks)} queries executed -> {OUT.relative_to(ROOT)}")
