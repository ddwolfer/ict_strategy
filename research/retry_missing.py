"""Retry the 3 missing transcripts every 20 minutes until success (max 8 rounds)."""
import subprocess
import sys
import time
from pathlib import Path

MISSING = ["3xgtrXok-xs", "xi0N9BG1Qvs", "kNlySn81dmo"]
OUT = Path(__file__).parent / "transcripts"

for round_no in range(1, 9):
    remaining = [v for v in MISSING if not (OUT / f"{v}.txt").exists()]
    if not remaining:
        print("All transcripts fetched.")
        sys.exit(0)
    print(f"Round {round_no}: waiting 20 min, then retrying {remaining}", flush=True)
    time.sleep(1200)
    subprocess.run([sys.executable, str(Path(__file__).parent / "fetch_transcripts.py")])

remaining = [v for v in MISSING if not (OUT / f"{v}.txt").exists()]
print(f"Finished. Still missing: {remaining}")
sys.exit(1 if remaining else 0)
