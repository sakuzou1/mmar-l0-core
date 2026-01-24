import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

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

# --- Diagnostics ---
reason_codes = []
evidence_paths = []
suggested_fix = []

raw_sev = delta.get("severity", "PASS")
if raw_sev not in ("PASS", "DELAY", "BLOCK"):
    reason_codes.append("INVALID_SEVERITY_COERCED_TO_BLOCK")
    evidence_paths.append("delta.severity")
    suggested_fix.append("Set `delta.severity` to PASS/DELAY/BLOCK.")

# Rule 0: explicit block flag overrides everything
if delta.get("block") is True:
    severity = "BLOCK"
    d_rc = delta.get("reason_codes", []) or []
    is_mmar = any(isinstance(x, str) and x.startswith("MMAR:") for x in d_rc)
    reason_codes.append("MMAR_EXPLICIT_BLOCK" if is_mmar else "MANUAL_BLOCK_FLAG")
    evidence_paths.append("delta.block")
    suggested_fix.append("Remove `delta.block=true` or replace with `severity=DELAY` and provide evidence.")

# Carry through evidence list (dedupe, preserve order)
evidence_list = list(dict.fromkeys(delta.get("evidence", [])))

# --- AUTO rule (the upgrade) ---
# If no evidence, we don't trust the change.
# - high externality x high irreversibility -> BLOCK
# - otherwise -> DELAY (until +48h below)
impact = delta.get("impact", {})
if not isinstance(impact, dict):
    impact = {}
externality = str(impact.get("externality", "")).lower().strip()
irreversibility = str(impact.get("irreversibility", "")).lower().strip()

if severity != "BLOCK" and not evidence_list:
    if externality == "high" and irreversibility == "high":
        severity = "BLOCK"
        reason_codes.append("AUTO_BLOCK_HIGH_X_HIGH_NO_EVIDENCE")
        evidence_paths += ["delta.impact.externality", "delta.impact.irreversibility", "delta.evidence"]
        suggested_fix.append("Add evidence or reduce externality/irreversibility; otherwise keep BLOCK.")
    else:
        severity = "DELAY"
        reason_codes.append("AUTO_DELAY_NO_EVIDENCE")
        reason_codes.append("MMAR_DELAY_EVIDENCE_GAP")
        evidence_paths.append("delta.evidence")
        suggested_fix.append("Add at least one item to `delta.evidence` to move from DELAY to PASS/BLOCK.")

# --- DELAY operationalization (48h default) ---
until = delta.get("until", None)
recheck = []
next_action = None

if severity == "DELAY":
    if until is None:
        now_local = datetime.now(timezone.utc).astimezone()
        until_dt = now_local + timedelta(hours=48)
        until = until_dt.isoformat(timespec="seconds")
        reason_codes.append("AUTO_DELAY_UNTIL_SET_48H")
        evidence_paths.append("delta.until")
        suggested_fix.append("Provide a concrete `delta.until` if 48h is not appropriate.")

    recheck = [
        "Add evidence (links / hashes / screenshots) to `delta.evidence`",
        "Reconfirm irreversibility/externality assumptions under As-of constraints",
        "Re-run the gate after `until`",
    ]
    next_action = "RERUN_AFTER_UNTIL"

decision_gate = {
    "severity": severity,
    "until": until,
    "evidence": evidence_list,
    "reason_codes": list(dict.fromkeys(reason_codes)),
    "evidence_paths": list(dict.fromkeys(evidence_paths)),
    "suggested_fix": list(dict.fromkeys(suggested_fix)),
    "recheck": recheck,
    "next_action": next_action,
}

outp = Path(args.out)
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(
    json.dumps(decision_gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

sys.exit(0)
