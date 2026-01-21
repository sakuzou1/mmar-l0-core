![ci](https://github.com/shin4141/mmar-l0-core/actions/workflows/ci.yml/badge.svg)

# mmar-l0-core

Minimal MMAR / L0 core.
As-of (Time V2) + Δ + PIC merge (∪/max/OR) -> deterministic PASS/DELAY/BLOCK.

## Run (local)
```bash
python -m core.run_once \
  --asof examples/asof_pack.example.json \
  --delta examples/delta_entry.example.json \
  --out out_gate_test/decision_gate.json
