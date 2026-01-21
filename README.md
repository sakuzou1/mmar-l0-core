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

python -m pip install jsonschema && python -m core.run_once --asof examples/asof_pack.example.json --delta examples/delta_entry.example.json --out out_gate_test/decision_gate.json && python -c "import json; from jsonschema import validate; validate(json.load(open('out_gate_test/decision_gate.json')), json.load(open('decision_gate.schema.json'))); print('schema: OK')"

### PIC merge (minimal)
- evidence: ∪ (dedupe)
- until: max (currently direct from delta)
- severity: OR (delta.block=true => BLOCK)
