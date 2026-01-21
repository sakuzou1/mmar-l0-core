import argparse, json
from pathlib import Path

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--asof", required=True)
    p.add_argument("--delta", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    asof = json.loads(Path(args.asof).read_text(encoding="utf-8"))
    delta = json.loads(Path(args.delta).read_text(encoding="utf-8"))

    # L0: placeholder output (deterministic)
    decision_gate = {
        "severity": "PASS",
        "until": None,
        "evidence": [],
        "asof": asof,
        "delta": delta,
    }

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(
        json.dumps(decision_gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
