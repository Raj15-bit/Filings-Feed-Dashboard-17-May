"""
Run the full pipeline in one shot:
    1) Parse newest HTML in input/        → data/filings_raw.json
    2) Classify and enrich                → data/filings_enriched.json
    3) Score every company                 → data/scored.json + data/sector_strength.json
    4) Build the final dashboard           → output/filings_dashboard.html

Usage:
    python run_all.py
"""
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
scripts = here / "scripts"
steps = [
    (scripts / "1_parse.py",      "Parsing input HTML"),
    (scripts / "2_classify.py",   "Classifying signals + sentiment"),
    (scripts / "3_score.py",      "Scoring companies + sector strength"),
    (scripts / "4_build_html.py", "Building dashboard"),
]

for script, label in steps:
    print(f"\n━━━ {label} ━━━")
    result = subprocess.run([sys.executable, str(script)])
    if result.returncode != 0:
        print(f"✕ {script.name} failed.")
        sys.exit(result.returncode)

print(f"\n✓ Dashboard ready: {here / 'output' / 'filings_dashboard.html'}")
print("  Open it in any browser. No server / dependencies needed.")
