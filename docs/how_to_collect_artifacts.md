# How to collect recurrence logs (artifact → downloads)

Goal: gather multiple `recurrence_log.json` files under `downloads/` and run the aggregate tool.

## Option A (manual, simplest)
1) GitHub → Actions → select **MMAR Recurrence (v0)** run
2) Download artifact: `recurrence_log.zip`
3) Unzip into `downloads/run-YYYYMMDD-HHMM/`

Expected structure:
- downloads/
  - run-001/recurrence_log.json
  - run-002/recurrence_log.json
  - ...

## Aggregate
```bash
python3 tools/recurrence_aggregate.py --in downloads --out out/recurrence_aggregate.json
