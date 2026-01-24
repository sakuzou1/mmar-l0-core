import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _stable_hash(obj) -> str:
    s = json.dumps(obj, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def _reason_code_for_finding(f: dict) -> str:
    t = f.get("type")
    tag = f.get("tag")
    if tag:
        return f"MMAR:{t}:{tag}"
    return f"MMAR:{t}"


def findings_to_delta(findings_doc: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    case_id = findings_doc.get("case_id", "unknown")
    asof = findings_doc.get("asof", "unknown")
    findings = findings_doc.get("findings", [])

    evidence = []
    changes = []
    reason_codes = []

    has_delay = False
    has_block = False

    flags = {
        "coordination_detected": False
    }

    for f in findings:
        f_type = f.get("type")
        tag = f.get("tag")
        claim = f.get("claim", "")
        needs = f.get("needs") or []
        signals = f.get("signals") or {}
        delta_payload = f.get("delta") or {}

        # v0 severity triggers (conservative)
        if f_type in ("MISSING_EVIDENCE", "STRUCTURAL_ANOMALY"):
            has_delay = True

        # v0.1: explicit flag for a known high-signal anomaly
        if f_type == "STRUCTURAL_ANOMALY" and tag == "COORDINATION":
            flags["coordination_detected"] = True

        # explicit block trigger (only when declared)
        if bool(signals.get("block")) or bool(delta_payload.get("block")):
            has_block = True

        rc = _reason_code_for_finding(f)
        reason_codes.append(rc)

        if f_type == "MISSING_EVIDENCE":
            for n in needs:
                if isinstance(n, str) and n.strip():
                    evidence.append(n.strip())
        else:
            if isinstance(f_type, str) and f_type:
                evidence.append(f"{f_type}:{tag}" if tag else f_type)

        changes.append({
            "type": f_type,
            "tag": tag,
            "claim": claim,
            "needs": needs,
            "signals": signals,
            "reason_code": rc
        })

    severity = "PASS"
    if has_block:
        severity = "BLOCK"
    elif has_delay:
        severity = "DELAY"

    out = {
        "delta_id": f"{case_id}:{asof}:{_stable_hash(findings)}",
        "severity": severity,
        "until": None,
        "block": (severity == "BLOCK"),
        "evidence": sorted(set(evidence)),
        "changes": changes,
        "reason_codes": sorted(set(reason_codes)),
        "meta": {
            "generated_at": now,
            "source": "mmar_findings",
            "case_id": case_id,
            "asof": asof,
            "flags": flags
        }
    }
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="path to mmar_findings.json")
    ap.add_argument("--out", dest="outp", required=True, help="path to delta_entry.json")
    args = ap.parse_args()

    doc = _load_json(Path(args.inp), {})
    out = findings_to_delta(doc)
    _save_json(Path(args.outp), out)
    print(f"[findings_to_delta] wrote -> {args.outp} severity={out['severity']}")

