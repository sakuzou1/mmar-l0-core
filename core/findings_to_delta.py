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


def findings_to_delta(findings_doc: dict) -> dict:
    """
    v0 mapping (simple + deterministic):
    - PASS by default
    - DELAY if any MISSING_EVIDENCE or STRUCTURAL_ANOMALY exists
    - BLOCK only if a finding explicitly asks for block via signals.block=true or delta.block=true
    Required output fields per delta_entry schema:
      delta_id, severity, until, block, evidence[], changes[]
    """
    now = datetime.now(timezone.utc).isoformat()

    case_id = findings_doc.get("case_id", "unknown")
    asof = findings_doc.get("asof", "unknown")
    findings = findings_doc.get("findings", [])

    # evidence: collect strings (dedupe later)
    evidence = []
    changes = []

    has_delay = False
    has_block = False

    for f in findings:
        f_type = f.get("type")
        tag = f.get("tag")
        claim = f.get("claim", "")
        needs = f.get("needs") or []
        signals = f.get("signals") or {}
        delta_payload = f.get("delta") or {}

        # v0 severity triggers
        if f_type in ("MISSING_EVIDENCE", "STRUCTURAL_ANOMALY"):
            has_delay = True

        # explicit block trigger (only when declared)
        if bool(signals.get("block")) or bool(delta_payload.get("block")):
            has_block = True

        # evidence strings
        if f_type == "MISSING_EVIDENCE":
            for n in needs:
                if isinstance(n, str) and n.strip():
                    evidence.append(n.strip())
        else:
            # keep a lightweight trace without exploding evidence
            if isinstance(f_type, str) and f_type:
                if tag:
                    evidence.append(f"{f_type}:{tag}")
                else:
                    evidence.append(f_type)

        # changes: keep minimal structured record (schema allows any item type)
        changes.append({
            "type": f_type,
            "tag": tag,
            "claim": claim,
            "needs": needs,
            "signals": signals
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

        # optional extras (allowed by additionalProperties=true)
        "meta": {
            "generated_at": now,
            "source": "mmar_findings",
            "case_id": case_id,
            "asof": asof
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
