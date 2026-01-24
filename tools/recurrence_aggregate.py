import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone


def _load_json(p: Path, default):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def _save_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def decide_promotion(count: int, distinct_sources: int, support_size: int) -> tuple[str, list[str]]:
    """
    v0.1 promotion: recurrence + gain
    - gain := distinct_sources or support_size growth proxy
    """
    reasons = [f"count={count}", f"distinct_sources={distinct_sources}", f"support_size={support_size}"]

    if count >= 3 and (distinct_sources >= 3 or support_size >= 3):
        return "NOVEL_STRUCTURE_CANDIDATE", reasons + ["rule:count>=3", "rule:distinct_sources>=3 OR support_size>=3"]
    if count >= 2 and (distinct_sources >= 2 or support_size >= 2):
        return "RECURRENCE_2X_REVIEW", reasons + ["rule:count>=2", "rule:distinct_sources>=2 OR support_size>=2"]
    return "NONE", reasons + ["rule:else"]


def aggregate(inputs):
    now = datetime.now(timezone.utc).isoformat()
    total_files = 0

    acc = defaultdict(lambda: {
        "type": None,
        "tag": None,
        "count": 0,
        "first_seen": None,
        "last_seen": None,
        "sources": [],   # union
        "support": [],   # union
        "examples": []
    })

    for p in inputs:
        p = Path(p)
        files = list(p.rglob("recurrence_log.json")) if p.is_dir() else [p]

        for f in files:
            doc = _load_json(f, {})
            items = doc.get("items", {})
            if not isinstance(items, dict):
                continue
            total_files += 1

            for fp, it in items.items():
                a = acc[fp]
                a["type"] = a["type"] or it.get("type")
                a["tag"] = a["tag"] if a["tag"] is not None else it.get("tag")
                a["count"] += int(it.get("count", 0) or 0)

                fs = it.get("first_seen")
                ls = it.get("last_seen")
                if fs and (a["first_seen"] is None or fs < a["first_seen"]):
                    a["first_seen"] = fs
                if ls and (a["last_seen"] is None or ls > a["last_seen"]):
                    a["last_seen"] = ls

                # union sources
                srcs = it.get("sources", [])
                if isinstance(srcs, list):
                    a["sources"].extend(srcs)

                # union support
                sup = it.get("support", [])
                if isinstance(sup, list):
                    a["support"].extend(sup)

                # examples
                ex = it.get("examples", [])
                if isinstance(ex, list) and ex:
                    a["examples"].extend(ex)
                if len(a["examples"]) > 10:
                    a["examples"] = a["examples"][-10:]

    merged_items = {}
    ranking = []

    for fp, it in acc.items():
        # dedupe sources by (case_id, asof)
        seen = set()
        dedup_sources = []
        for s in it["sources"]:
            key = (s.get("case_id"), s.get("asof"))
            if key in seen:
                continue
            seen.add(key)
            dedup_sources.append(s)

        support_set = list(dict.fromkeys([x for x in it["support"] if isinstance(x, str)]))

        promo, promo_reason = decide_promotion(
            count=it["count"],
            distinct_sources=len(dedup_sources),
            support_size=len(support_set)
        )

        merged = {
            "type": it["type"],
            "tag": it["tag"],
            "count": it["count"],
            "distinct_sources": len(dedup_sources),
            "support_size": len(support_set),
            "promotion": promo,
            "promotion_reason": promo_reason,
            "first_seen": it["first_seen"],
            "last_seen": it["last_seen"],
            "sources": dedup_sources[:20],
            "support": support_set[:200],
            "examples": it["examples"],
        }
        merged_items[fp] = merged
        ranking.append({"fp": fp, **merged})

    ranking.sort(key=lambda x: x["count"], reverse=True)

    return {
        "version": "aggregate-v0.1",
        "generated_at": now,
        "inputs": {"num_files": total_files},
        "top": ranking[:50],
        "items": merged_items
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inputs", nargs="+", required=True,
                    help="files or directories to scan (dir searches **/recurrence_log.json)")
    ap.add_argument("--out", dest="outp", required=True, help="output json path")
    args = ap.parse_args()

    out = aggregate(args.inputs)
    _save_json(Path(args.outp), out)
    print(f"[aggregate] files={out['inputs']['num_files']} items={len(out['items'])} -> {args.outp}")
    if out["top"]:
        print("[top]")
        for x in out["top"][:10]:
            tag = f":{x['tag']}" if x.get("tag") else ""
            print(f"  {x['count']}x  {x.get('type')}{tag}  {x['promotion']}")

