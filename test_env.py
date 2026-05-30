#!/usr/bin/env python3
"""
Smoke-test the Blocksworld environment against all tasks using reference plans.

This script does NOT require an LLM — it verifies the environment, tasks,
and action validation are all internally consistent.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from env.blocksworld_env import BlocksworldEnv

# ── Reference plans for each task (verified to be correct) ──────────

REFERENCE_PLANS = {
    "task_01": [
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_02": [
        "UNSTACK(C,A)",
        "PUTDOWN(C)",
        "PICKUP(B)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_03": [
        "UNSTACK(D,C)",
        "PUTDOWN(D)",
        "UNSTACK(C,B)",
        "STACK(C,D)",
        "UNSTACK(B,A)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_04": [
        "UNSTACK(C,A)",
        "PUTDOWN(C)",
        "PICKUP(B)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_05": [
        "PICKUP(D)",
        "STACK(D,E)",
        "PICKUP(C)",
        "STACK(C,D)",
        "PICKUP(B)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_06": [
        "UNSTACK(D,B)",
        "PUTDOWN(D)",
        "UNSTACK(B,A)",
        "PUTDOWN(B)",
        "PICKUP(A)",
        "STACK(A,B)",
        "PICKUP(D)",
        "STACK(D,A)",
        "PICKUP(C)",
        "STACK(C,D)",
    ],
    "task_07": [
        "UNSTACK(B,C)",
        "PUTDOWN(B)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    # ── hard ─────────────────────────────────────────────────────────
    "task_08": [
        "UNSTACK(C,B)",
        "PUTDOWN(C)",
        "UNSTACK(B,A)",
        "PUTDOWN(B)",
        "UNSTACK(F,E)",
        "PUTDOWN(F)",
        "UNSTACK(E,D)",
        "PUTDOWN(E)",
        "PICKUP(C)",
        "STACK(C,A)",
        "PICKUP(E)",
        "STACK(E,C)",
        "PICKUP(D)",
        "STACK(D,F)",
        "PICKUP(B)",
        "STACK(B,D)",
    ],
    "task_09": [
        "UNSTACK(D,C)",
        "PUTDOWN(D)",
        "UNSTACK(C,B)",
        "STACK(C,D)",
        "UNSTACK(B,A)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_10": [
        "UNSTACK(B,A)",
        "PUTDOWN(B)",
        "UNSTACK(D,C)",
        "PUTDOWN(D)",
        "UNSTACK(F,E)",
        "PUTDOWN(F)",
        "PICKUP(B)",
        "STACK(B,A)",
        "PICKUP(C)",
        "STACK(C,B)",
        "PICKUP(D)",
        "STACK(D,C)",
        "PICKUP(E)",
        "STACK(E,D)",
        "PICKUP(F)",
        "STACK(F,E)",
        "PICKUP(G)",
        "STACK(G,F)",
    ],
    # ── extreme ──────────────────────────────────────────────────────
    "task_11": [
        "UNSTACK(C,B)",
        "PUTDOWN(C)",
        "UNSTACK(B,A)",
        "PUTDOWN(B)",
        "UNSTACK(D,E)",
        "STACK(D,C)",
        "PICKUP(E)",
        "STACK(E,D)",
        "PICKUP(B)",
        "STACK(B,E)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_12": [
        "UNSTACK(C,B)",
        "PUTDOWN(C)",
        "UNSTACK(B,A)",
        "PUTDOWN(B)",
        "PICKUP(C)",
        "STACK(C,A)",
        "PICKUP(B)",
        "STACK(B,C)",
        "UNSTACK(F,E)",
        "PUTDOWN(F)",
        "UNSTACK(E,D)",
        "PUTDOWN(E)",
        "PICKUP(F)",
        "STACK(F,D)",
        "PICKUP(E)",
        "STACK(E,F)",
    ],
    "task_13": [
        "PICKUP(D)",
        "STACK(D,C)",
        "PICKUP(E)",
        "STACK(E,D)",
        "PICKUP(F)",
        "STACK(F,E)",
        "PICKUP(G)",
        "STACK(G,F)",
    ],
    "task_14": [
        "UNSTACK(D,C)",
        "PUTDOWN(D)",
        "UNSTACK(C,B)",
        "STACK(C,D)",
        "UNSTACK(B,A)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
        "PICKUP(F)",
        "STACK(F,G)",
        "PICKUP(E)",
        "STACK(E,F)",
    ],
    "task_15": [
        "UNSTACK(H,G)",
        "PUTDOWN(H)",
        "UNSTACK(G,F)",
        "STACK(G,H)",
        "UNSTACK(F,E)",
        "STACK(F,G)",
        "UNSTACK(E,D)",
        "STACK(E,F)",
        "UNSTACK(D,C)",
        "STACK(D,E)",
        "UNSTACK(C,B)",
        "STACK(C,D)",
        "UNSTACK(B,A)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "task_16": [
        "UNSTACK(D,C)",
        "PUTDOWN(D)",
        "PICKUP(C)",
        "STACK(C,B)",
        "UNSTACK(F,E)",
        "PUTDOWN(F)",
        "PICKUP(E)",
        "STACK(E,D)",
        "PICKUP(F)",
        "STACK(F,E)",
        "PICKUP(G)",
        "STACK(G,F)",
    ],
    "task_17": [
        "UNSTACK(G,F)",
        "PUTDOWN(G)",
        "UNSTACK(F,A)",
        "PUTDOWN(F)",
        "UNSTACK(E,D)",
        "PUTDOWN(E)",
        "UNSTACK(D,B)",
        "PUTDOWN(D)",
        "PICKUP(C)",
        "STACK(C,A)",
        "PICKUP(G)",
        "STACK(G,C)",
        "PICKUP(D)",
        "STACK(D,G)",
        "PICKUP(E)",
        "STACK(E,B)",
        "PICKUP(F)",
        "STACK(F,E)",
    ],
    "task_18": [
        "PICKUP(G)",
        "STACK(G,C)",
    ],
    "task_19": [
        "UNSTACK(D,C)",
        "PUTDOWN(D)",
        "UNSTACK(C,B)",
        "STACK(C,D)",
        "UNSTACK(B,A)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
        "UNSTACK(H,G)",
        "PUTDOWN(H)",
        "UNSTACK(G,F)",
        "STACK(G,H)",
        "UNSTACK(F,E)",
        "STACK(F,G)",
        "PICKUP(E)",
        "STACK(E,F)",
    ],
    "task_20": [
        "UNSTACK(C,B)",
        "PUTDOWN(C)",
        "UNSTACK(B,A)",
        "PUTDOWN(B)",
        "UNSTACK(F,E)",
        "PUTDOWN(F)",
        "UNSTACK(E,D)",
        "PUTDOWN(E)",
        "UNSTACK(I,H)",
        "PUTDOWN(I)",
        "UNSTACK(H,G)",
        "PUTDOWN(H)",
        "PICKUP(C)",
        "STACK(C,A)",
        "PICKUP(F)",
        "STACK(F,C)",
        "PICKUP(I)",
        "STACK(I,F)",
        "PICKUP(D)",
        "STACK(D,B)",
        "PICKUP(E)",
        "STACK(E,D)",
        "PICKUP(G)",
        "STACK(G,E)",
        "PICKUP(H)",
        "STACK(H,G)",
    ],
    # ── nl_only ─────────────────────────────────────────────────────
    "nl_task_01": [
        "UNSTACK(C,A)",
        "PUTDOWN(C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "nl_task_02": [
        "UNSTACK(C,A)",
        "PUTDOWN(C)",
        "PICKUP(B)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "nl_task_03": [
        "UNSTACK(E,D)",
        "PUTDOWN(E)",
        "UNSTACK(D,C)",
        "STACK(D,E)",
        "UNSTACK(C,B)",
        "STACK(C,D)",
        "PICKUP(B)",
        "STACK(B,C)",
        "PICKUP(A)",
        "STACK(A,B)",
    ],
    "nl_task_04": [
        "UNSTACK(D,C)",
        "PUTDOWN(D)",
        "UNSTACK(C,B)",
        "PUTDOWN(C)",
        "UNSTACK(B,A)",
        "STACK(B,A)",
        "PICKUP(C)",
        "STACK(C,B)",
        "PICKUP(D)",
        "STACK(D,C)",
        "UNSTACK(F,E)",
        "PUTDOWN(F)",
        "PICKUP(E)",
        "STACK(E,D)",
        "PICKUP(F)",
        "STACK(F,E)",
    ],
    "nl_task_05": [
        "UNSTACK(C,B)",
        "PUTDOWN(C)",
        "UNSTACK(B,A)",
        "PUTDOWN(B)",
        "UNSTACK(E,D)",
        "PUTDOWN(E)",
        "UNSTACK(G,F)",
        "PUTDOWN(G)",
        "PICKUP(C)",
        "STACK(C,A)",
        "PICKUP(E)",
        "STACK(E,C)",
        "PICKUP(G)",
        "STACK(G,E)",
        "PICKUP(D)",
        "STACK(D,B)",
        "PICKUP(F)",
        "STACK(F,D)",
    ],
}


def test_task(task_path: Path, reference_plan: list) -> bool:
    """Run a single task through the environment and check against reference plan."""
    with open(task_path) as f:
        task = json.load(f)

    task_id = task["task_id"]
    print(f"  [{task_id}] ", end="")

    # Create env and reset
    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])

    # Execute reference plan
    result = env.execute_plan(reference_plan)

    if not result["plan_valid"]:
        print(f"FAIL — plan invalid at step {result['failed_step']}: {result['failed_action']}")
        print(f"    State at failure: {result['final_state']}")
        return False

    goal_ok = env.is_goal_satisfied(task["goal_state"])
    if not goal_ok:
        print(f"FAIL — plan valid but goal not satisfied")
        print(f"    Final state: {sorted(env.state)}")
        print(f"    Expected goal: {task['goal_state']}")
        print(f"    Missing: {set(task['goal_state']) - env.state}")
        return False

    print(f"OK — {len(reference_plan)} steps, goal satisfied")
    return True


def main():
    print("=" * 60)
    print("Blocksworld Environment Smoke Test")
    print("=" * 60)

    all_tasks = []

    # Public tasks
    public_dir = PROJECT_ROOT / "tasks" / "public"
    for fpath in sorted(public_dir.glob("task_*.json")):
        all_tasks.append(fpath)

    # Hidden tasks
    hidden_dir = PROJECT_ROOT / "tasks" / "hidden"
    for fpath in sorted(hidden_dir.glob("task_*.json")):
        all_tasks.append(fpath)

    # Hard tasks
    hard_dir = PROJECT_ROOT / "tasks" / "hard"
    if hard_dir.is_dir():
        for fpath in sorted(hard_dir.glob("task_*.json")):
            all_tasks.append(fpath)

    # Extreme tasks
    extreme_dir = PROJECT_ROOT / "tasks" / "extreme"
    if extreme_dir.is_dir():
        for fpath in sorted(extreme_dir.glob("task_*.json")):
            all_tasks.append(fpath)

    # NL-only tasks
    nl_dir = PROJECT_ROOT / "tasks" / "nl_only"
    if nl_dir.is_dir():
        for fpath in sorted(nl_dir.glob("nl_task_*.json")):
            all_tasks.append(fpath)

    passed = 0
    failed = 0

    for fpath in all_tasks:
        task_id = fpath.stem  # e.g. "task_01"
        ref_plan = REFERENCE_PLANS.get(task_id)
        if ref_plan is None:
            print(f"  [{task_id}] SKIP — no reference plan defined")
            continue

        if test_task(fpath, ref_plan):
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    print(f"{'=' * 60}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
