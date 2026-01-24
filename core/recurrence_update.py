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
    Stable fingerprint for recurrence tracking.
    NOTE: This is v0-style fingerprint. If you later want "same type/tag even if details change",
    you can switch fingerprint base to type/tag only (v0.2).
    """
    base = {
        "type": f.get("type"),
        "tag": f.get("tag"),
        "claim": f.get("claim"),
        "needs": f.get("needs"),
        "delta": f.get("delta"),
        "signals": f.get("signals", {}),
    }
    s = json.dumps(base, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _extract_support(f: dict) -> list[str]:
    """
    Extract minimal "support fragments" to justify promotion.
    These are not full evidence; they are small stable signals:
      - needs entries
      - signals keys
      - delta keys (if object)
      - type/tag
    """
    out = []

    t = f.get("type")
    tag = f.get("tag")
    if t:
        out.append(f"type:{t}")
    if tag:
        out.append(f"tag:{tag}")

    needs = f.get("needs") or []
    if isinstance(needs, list):
        for n in needs:
            if isinstance(n, str) and n.strip():
                out.append(f"needs:{n.strip()}")

    signals = f.get("signals") or {}
    if isinstance(signals, dict):
        for k in sorted(signals.keys()):
            out.append(f"signal_key:{k}")

    delta = f.get("delta")
    if isinstance(delta, dict):
        for k in sorted(delta.keys()):
            out.append(f"delta_key:{k}")

    # Keep it bounded
    return out[:50]


def update_recurrence(mmar_findings_path: Path) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    log = _load_json(LOG_PATH, {"version": "v1.1", "items": {}})
    log["version"] = "v1.1"

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

            # v1.1 additions
            "sources": [],   # list[{case_id, asof}]
            "support": [],   # list[str] (set-like, deduped)
            "examples": []
        })

        item["count"] += 1
        item["last_seen"] = now

        # sources (dedupe)
        src = {"case_id": case_id, "asof": asof}
        item["sources"].append(src)
        # dedupe sources while keeping recent ones
        seen = set()
        dedup_sources = []
        for s in item["sources"]:
            key = (s.get("case_id"), s.get("asof"))
            if key in seen:
                continue
            seen.add(key)
            dedup_sources.append(s)
        item["sources"] = dedup_sources[-20:]

        # support (union, bounded)
        item["support"] = list(dict.fromkeys(item.get("support", []) + _extract_support(f)))[:200]

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


