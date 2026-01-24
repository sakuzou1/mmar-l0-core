import json
from pathlib import Path


def _load_json(p: Path, default):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def _save_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def decide_intervene(gate: dict, profile: dict) -> dict:
    """
    v0 EV-based intervene:
      - Uses gate severity + reason_codes/upstream_reason_codes to estimate p_break.
      - Chooses among NONE / SUBTRACT / ADD_MODEL by comparing EVs.

    Intuition:
      - tight budget or near deadline => SUBTRACT earlier
      - ample budget & stalled => ADD_MODEL can win
    """
    severity = gate.get("severity")
    reason_codes = gate.get("reason_codes", []) or []
    upstream = gate.get("upstream_reason_codes", []) or []
    codes = [x for x in (reason_codes + upstream) if isinstance(x, str)]

    budget_mode = profile.get("budget_mode", "tight")
    deadline_days = float(profile.get("deadline_days", 30))
    window_cost = float(profile.get("window_cost", 1.0))
    c_sub = float(profile.get("intervene_cost_subtract", 1.0))
    c_add = float(profile.get("intervene_cost_add_model", 2.0))
    V = float(profile.get("value_breakthrough", 10.0))
    base_p = float(profile.get("base_p_break", 0.15))

    reasons = []
    stagnation = False

    # heuristics: evidence gap & delay indicates stagnation-ish
    if "MMAR_DELAY_EVIDENCE_GAP" in codes or "AUTO_DELAY_NO_EVIDENCE" in codes:
        stagnation = True
        reasons.append("evidence_gap")

    if deadline_days <= 7:
        reasons.append("deadline_near")

    if budget_mode == "tight":
        reasons.append("budget_tight")
    else:
        reasons.append("budget_ample")

    # Estimate p_break from gate state
    p_continue = base_p

    # If BLOCK, assume current path has low chance unless we subtract risk
    if severity == "BLOCK":
        p_continue *= 0.05
        reasons.append("blocked_now")

    # If DELAY with evidence gap, continuing without change usually low
    if severity == "DELAY" and stagnation:
        p_continue *= 0.4

    # Intervention effects (simple):
    # SUBTRACT: reduce scope => p increases, V may drop a bit
    p_sub = min(0.95, p_continue + (0.20 if (budget_mode == "tight" or deadline_days <= 7) else 0.10))
    V_sub = V * 0.85

    # ADD_MODEL: change search space => p increases more, cost higher, V unchanged
    p_add = min(0.95, p_continue + (0.25 if budget_mode == "ample" else 0.15))
    V_add = V

    # EV calculations (one-window comparison)
    ev_continue = (p_continue * V) - window_cost
    ev_subtract = (p_sub * V_sub) - window_cost - c_sub
    ev_add_model = (p_add * V_add) - window_cost - c_add

    # Choose action
    action = "NONE"
    ev_intervene = ev_continue
    best = ("NONE", ev_continue)

    # Default order bias: SUBTRACT first (safer) unless ample strongly favors add-model
    if ev_subtract > best[1]:
        best = ("SUBTRACT", ev_subtract)
    if ev_add_model > best[1]:
        best = ("ADD_MODEL", ev_add_model)

    action, ev_intervene = best

    # Guardrails: if not stagnation and severity==PASS, do nothing
    if severity == "PASS" and not stagnation:
        action = "NONE"
        ev_intervene = ev_continue
        reasons.append("pass_no_stagnation")

    out = {
        "action": action,
        "stagnation": bool(stagnation),
        "reason": reasons,
        "ev_continue": float(ev_continue),
        "ev_intervene": float(ev_intervene),
        "ev_candidates": {
            "CONTINUE": float(ev_continue),
            "SUBTRACT": float(ev_subtract),
            "ADD_MODEL": float(ev_add_model)
        },
        "profile": profile,
        "gate_summary": {
            "severity": severity,
            "upstream_reason_codes": upstream
        }
    }
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", required=True, help="path to decision_gate.json")
    ap.add_argument("--profile", required=True, help="path to intervene_profile.json")
    ap.add_argument("--out", required=True, help="path to intervene.json")
    args = ap.parse_args()

    gate = _load_json(Path(args.gate), {})
    profile = _load_json(Path(args.profile), {})
    out = decide_intervene(gate, profile)
    _save_json(Path(args.out), out)
    print(f"[intervene] action={out['action']} ev_continue={out['ev_continue']:.3f} ev_intervene={out['ev_intervene']:.3f} -> {args.out}")
