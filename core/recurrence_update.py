import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / ".mmar" / "recurrence_log.json"

def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _fingerprint_finding(f: dict) -> str:
    """
    Stable fingerprint: same "kind of thing" should hash the same even if timestamps differ.
    Tune this later (v1) once patterns emerge.
    """
    base = {
        "type": f.get("type"),
        "tag": f.get("tag"),
        "claim": f.get("claim"),
        "needs": f.get("needs"),
        "delta": f.get("delta"),
        # Keep signals but sort keys for stability
        "signals": f.get("signals", {}),
    }
    s = json.dumps(base, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def update_recurrence(mmar_findings_path: Path) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    log = _load_json(LOG_PATH, {"version": "v0", "items": {}})

    findings_doc = _load_json(mmar_findings_path, {})
    case_id = findings_doc.get("case_id", "unknown")
    asof = findings_doc.get("asof", "unknown")
    findings = findings_doc.get("findings", [])

    for f in findings:
        fp = _fingerprint_finding(f)
        item = log["items"].get(fp, {
            "type": f.get("type"),
            "tag": f.get("tag"),
            "first_seen": now,
            "last_seen": now,
            "count": 0,
            "examples": []
        })

        item["count"] += 1
        item["last_seen"] = now

        # keep up to 5 examples for debugging
        item["examples"].append({"case_id": case_id, "asof": asof})
        item["examples"] = item["examples"][-5:]

        log["items"][fp] = item

    _save_json(LOG_PATH, log)
    return log

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="path to mmar_findings.json")
    args = ap.parse_args()

    out = update_recurrence(Path(args.inp))
    print(f"[recurrence] updated items={len(out['items'])} -> {LOG_PATH}")
