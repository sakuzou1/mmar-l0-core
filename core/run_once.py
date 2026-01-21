import argparse
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--asof", required=True)
p.add_argument("--delta", required=True)
p.add_argument("--out", required=True)
args = p.parse_args()

asof = json.loads(Path(args.asof).read_text(encoding="utf-8"))
delta = json.loads(Path(args.delta).read_text(encoding="utf-8"))

severity = delta.get("severity", "PASS")
if severity not in ("PASS", "DELAY", "BLOCK"):
    severity = "BLOCK"

decision_gate = {
    "severity": severity,
    "until": None,
    "evidence": list(dict.fromkeys(delta.get("evidence", []))),
}

outp = Path(args.out)
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(
    json.dumps(decision_gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

sys.exit(0)

