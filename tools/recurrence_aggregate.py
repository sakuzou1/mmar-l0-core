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


def promotion_for_count(count: int) -> str:
    if count >= 3:
        return "NOVEL_STRUCTURE_CANDIDATE"
    if count >= 2:
        return "RECURRENCE_2X_REVIEW"
    return "NONE"


def aggregate(paths):
    """
    Aggregate many recurrence_log.json files.
    Input can be:
      - a directory (searches **/recurrence_log.json)
      - individual files
    Output:
      - merged items with summed counts
      - ranking by count
      - promotion flag derived from total count
    """
    now = datetime.now(timezone.utc).isoformat()
    merged = {}
    total_files = 0

    # fp -> accumulator
    acc = defaultdict(lambda: {
        "type": None,
        "tag": None,
        "count": 0,
        "first_seen": None,
        "last_seen": None,
        "examples": []
    })

    for p in paths:
        p = Path(p)
        files = []
        if p.is_dir():
            files = list(p.rglob("recurrence_log.json"))
        else:
            files = [p]

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

                ex = it.get("examples", [])
                if isinstance(ex, list) and ex:
                    a["examples"].extend(ex)

                # keep last 10 examples for readability
                if len(a["examples"]) > 10:
                    a["examples"] = a["examples"][-10:]

    merged_items = {}
    for fp, it in acc.items():
        promo = promotion_for_count(it["count"])
        merged_items[fp] = {
            "type": it["type"],
            "tag": it["tag"],
            "count": it["count"],
            "promotion": promo,
            "first_seen": it["first_seen"],
            "last_seen": it["last_seen"],
            "examples": it["examples"],
        }

    ranking = sorted(
        [{"fp": fp, **it} for fp, it in merged_items.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    out = {
        "version": "aggregate-v0",
        "generated_at": now,
        "inputs": {"num_files": total_files},
        "top": ranking[:50],
        "items": merged_items
    }
    return out


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
