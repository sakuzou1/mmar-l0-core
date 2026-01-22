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

# --- Determine severity (minimal contract) ---
severity = delta.get("severity", "PASS")
if severity not in ("PASS", "DELAY", "BLOCK"):
    severity = "BLOCK"

# --- Add "diagnostic" fields (reason/evidence/fix) ---
reason_codes = []
evidence_paths = []
suggested_fix = []

# Rule: explicit block flag overrides everything
if delta.get("block") is True:
    severity = "BLOCK"
    reason_codes.append("MANUAL_BLOCK_FLAG")
    evidence_paths.append("delta.block")
    suggested_fix.append("Remove `delta.block=true` or replace with `severity=DELAY` and provide evidence.")

# Rule: invalid severity value coerced to BLOCK (already handled above)
# We keep a reason for transparency
raw_sev = delta.get("severity", "PASS")
if raw_sev not in ("PASS", "DELAY", "BLOCK"):
    reason_codes.append("INVALID_SEVERITY_COERCED_TO_BLOCK")
    evidence_paths.append("delta.severity")
    suggested_fix.append("Set `delta.severity` to PASS/DELAY/BLOCK.")

# Carry through evidence list (dedupe, preserve order)
evidence_list = list(dict.fromkeys(delta.get("evidence", [])))

decision_gate = {
    "severity": severity,
    "until": delta.get("until", None),
    "evidence": evidence_list,
    # Diagnostics (makes the gate look like it "judged" something)
    "reason_codes": list(dict.fromkeys(reason_codes)),
    "evidence_paths": list(dict.fromkeys(evidence_paths)),
    "suggested_fix": list(dict.fromkeys(suggested_fix)),
}

outp = Path(args.out)
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(
    json.dumps(decision_gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

sys.exit(0)

