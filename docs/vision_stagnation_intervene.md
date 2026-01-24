# Stagnation → Intervene (Subtract-first) — Vision (v0)

Goal: avoid endless loops when progress stalls.

## Progress (v0)
Progress is measured by **resolved_count** (issues/evidence gaps closed) per window (session/day).

## Stagnation (v0)
Stagnation when:
- resolved_count = 0 for a window, AND
- the same finding types repeat without new evidence.

If a **deadline** exists, the stagnation threshold is compressed to meet the date.

## Intervene (order)
1) **SUBTRACT**: reduce scope/assumptions/dependencies (make the problem smaller).
2) **ADD_MODEL**: inject a different model/OS only if needed (change the search space).

This is a policy layer; implementation can be CI/offline aggregation later.
