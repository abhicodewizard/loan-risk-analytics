"""Run the full pipeline: generate -> clean -> load SQL -> run queries -> charts -> Excel dashboard."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
STEPS = ["01_generate_data.py", "02_clean_data.py", "03_load_sql.py", "04_run_sql_analysis.py", "05_eda_charts.py", "06_build_excel_dashboard.py"]
for s in STEPS:
    print(f"\n=== {s} ===")
    if subprocess.run([sys.executable, str(ROOT / "src" / s)]).returncode != 0:
        sys.exit(f"Step failed: {s}")
print("\nAll done. See outputs/ and powerbi/data/")
