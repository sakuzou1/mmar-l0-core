# MMAR signals (recommended keys) — v0

Signals are optional, but using stable keys makes recurrence + review easier.

## Common keys
- `block` (bool): explicit hard-stop request. Use sparingly.
- `confidence` (number 0..1): subjective confidence for the finding.
- `top10_pct` (number): concentration signal (used in COORDINATION examples).
- `source` (string): where the signal came from (model/tool/log).
- `notes` (string): short freeform note.

## Examples
### COORDINATION
```json
{ "top10_pct": 70, "confidence": 0.6 }
