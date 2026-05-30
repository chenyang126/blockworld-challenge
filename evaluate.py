#!/usr/bin/env python3
"""
Batch Evaluator — Teacher-Provided

Runs a planner method (q1 or q2) on all tasks in a directory and prints
a summary table of results.

Usage:
    python evaluate.py --method q1 --task_dir tasks/public
    python evaluate.py --method q2 --task_dir tasks/public
    python evaluate.py --method q1 --task_dir tasks/hidden
    python evaluate.py --method q1 --task_dir tasks/public --output results.json

Environment variables (optional):
    OPENAI_API_KEY       OpenAI API key
    ANTHROPIC_API_KEY    Anthropic API key
    LLM_PROVIDER         "openai" (default), "anthropic", or "openai-compatible"
    LLM_MODEL            Model name
    LLM_BASE_URL         Base URL for openai-compatible providers
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from env.blocksworld_env import BlocksworldEnv
from llm_client import LLMClient


def load_tasks(task_dir: str) -> List[Dict]:
    """Load all task JSON files sorted by task_id from *task_dir*."""
    task_dir = Path(task_dir)
    if not task_dir.is_dir():
        print(f"[ERROR] Task directory not found: {task_dir}")
        sys.exit(1)

    tasks = []
    for fpath in sorted(task_dir.glob("task_*.json")) + sorted(task_dir.glob("nl_task_*.json")):
        with open(fpath) as f:
            task = json.load(f)
            tasks.append(task)
    return tasks


def make_student_task(task: Dict) -> Dict:
    """Create a copy of task for student use.

    For nl_only tasks, structured initial_state and goal_state are
    stripped so the student must extract them from natural_language.
    The original states are preserved for environment validation only.
    """
    student_task = dict(task)
    if task.get("nl_only"):
        student_task["initial_state"] = []
        student_task["goal_state"] = []
    return student_task


def evaluate_q1(task: Dict, llm_client: LLMClient) -> Dict:
    """Run Q1 (pure LLM prompt) on a single task and return metrics."""
    from student.q1_llm_prompt_planner import plan_with_llm

    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])

    # For NL-only tasks, hide structured states from the student
    student_task = make_student_task(task)

    start = time.time()
    try:
        plan = plan_with_llm(student_task, llm_client)
    except Exception as e:
        return {
            "task_id": task["task_id"],
            "method": "q1_llm_prompt",
            "plan": [],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "failed_step": None,
            "failed_action": None,
            "error": str(e),
            "time_seconds": round(time.time() - start, 2),
        }

    elapsed = round(time.time() - start, 2)

    if not plan:
        return {
            "task_id": task["task_id"],
            "method": "q1_llm_prompt",
            "plan": [],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "failed_step": None,
            "failed_action": None,
            "error": "Empty plan returned",
            "time_seconds": elapsed,
        }

    result = env.execute_plan(plan)
    goal_success = env.is_goal_satisfied(task["goal_state"])

    return {
        "task_id": task["task_id"],
        "method": "q1_llm_prompt",
        "plan": plan,
        "plan_valid": result["plan_valid"],
        "goal_success": goal_success,
        "num_steps": len(plan),
        "failed_step": result["failed_step"],
        "failed_action": result["failed_action"],
        "error": None,
        "time_seconds": elapsed,
    }


def evaluate_q2(task: Dict, domain_path: str, llm_client: LLMClient) -> Dict:
    """Run Q2 (LLM + PDDL) on a single task and return metrics."""
    from student.q2_llm_pddl_planner import plan_with_llm_pddl

    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])

    # For NL-only tasks, hide structured states from the student
    student_task = make_student_task(task)

    start = time.time()
    try:
        plan = plan_with_llm_pddl(student_task, domain_path, llm_client)
    except Exception as e:
        return {
            "task_id": task["task_id"],
            "method": "q2_llm_pddl",
            "plan": [],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "failed_step": None,
            "failed_action": None,
            "pddl_success": False,
            "planner_success": False,
            "error": str(e),
            "time_seconds": round(time.time() - start, 2),
        }

    elapsed = round(time.time() - start, 2)

    if not plan:
        return {
            "task_id": task["task_id"],
            "method": "q2_llm_pddl",
            "plan": [],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "failed_step": None,
            "failed_action": None,
            "pddl_success": False,
            "planner_success": False,
            "error": "Empty plan returned",
            "time_seconds": elapsed,
        }

    # Normalise plan format (handle lowercase planner output)
    normalised_plan = _normalise_plan(plan)
    result = env.execute_plan(normalised_plan)
    goal_success = env.is_goal_satisfied(task["goal_state"])

    return {
        "task_id": task["task_id"],
        "method": "q2_llm_pddl",
        "plan": normalised_plan,
        "plan_valid": result["plan_valid"],
        "goal_success": goal_success,
        "num_steps": len(normalised_plan),
        "failed_step": result["failed_step"],
        "failed_action": result["failed_action"],
        "pddl_success": True,    # if plan was generated, PDDL succeeded
        "planner_success": True,  # same logic
        "error": None,
        "time_seconds": elapsed,
    }


def _normalise_plan(plan: list) -> list:
    """Convert planner output to canonical BlocksworldEnv format."""
    normalised = []
    for action in plan:
        action = action.strip().lower().replace("-", "")
        parts = action.split(None, 1)
        if not parts:
            continue
        name = parts[0].upper()
        args_raw = parts[1] if len(parts) > 1 else ""
        args_list = [a.strip().upper() for a in args_raw.split() if a.strip()]
        normalised.append(f"{name}({','.join(args_list)})")
    return normalised


def print_summary(results: List[Dict]) -> None:
    """Print a formatted summary table."""
    n = len(results)
    n_valid = sum(1 for r in results if r["plan_valid"])
    n_goal = sum(1 for r in results if r["goal_success"])
    n_error = sum(1 for r in results if r.get("error"))

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    # Per-task table
    header = f"{'Task ID':<12} {'Valid':<8} {'Goal':<8} {'Steps':<8} {'Time(s)':<10} {'Error'}"
    print(header)
    print("-" * 70)

    for r in results:
        err = r.get("error", "") or ""
        if len(err) > 30:
            err = err[:27] + "..."
        print(
            f"{r['task_id']:<12} "
            f"{'✓' if r['plan_valid'] else '✗':<8} "
            f"{'✓' if r['goal_success'] else '✗':<8} "
            f"{r['num_steps']:<8} "
            f"{r.get('time_seconds', 0):<10} "
            f"{err}"
        )

    print("-" * 70)
    print(f"Total tasks:        {n}")
    print(f"Plan valid:         {n_valid}/{n}  ({100*n_valid/n:.0f}%)" if n else "")
    print(f"Goal achieved:      {n_goal}/{n}  ({100*n_goal/n:.0f}%)" if n else "")
    if n_error:
        print(f"Errors:             {n_error}/{n}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Batch evaluate Q1 or Q2 on a task directory."
    )
    parser.add_argument(
        "--method", type=str, required=True, choices=["q1", "q2"],
        help="Planning method: q1 (pure LLM) or q2 (LLM + PDDL)"
    )
    parser.add_argument(
        "--task_dir", type=str, required=True,
        help="Directory containing task_*.json files"
    )
    parser.add_argument(
        "--domain", type=str, default=None,
        help="Path to domain.pddl (Q2 only; default: pddl/domain.pddl)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Optional JSON path to save detailed results"
    )
    parser.add_argument(
        "--provider", type=str, default=None,
        help="LLM provider"
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Model name"
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="API key"
    )
    parser.add_argument(
        "--base-url", type=str, default=None,
        help="Base URL for openai-compatible providers"
    )
    args = parser.parse_args()

    # ── Load tasks ──────────────────────────────────────────────────
    tasks = load_tasks(args.task_dir)
    if not tasks:
        print(f"[ERROR] No task files found in {args.task_dir}")
        sys.exit(1)
    print(f"Found {len(tasks)} task(s) in {args.task_dir}")

    # ── Init LLM client ─────────────────────────────────────────────
    provider = args.provider or os.environ.get("LLM_PROVIDER", "openai")
    model = args.model or os.environ.get("LLM_MODEL", None)
    api_key = args.api_key or None
    base_url = args.base_url or os.environ.get("LLM_BASE_URL", None)

    try:
        llm_client = LLMClient(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        print(f"LLM: {provider} / {llm_client.model}")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # ── Domain path (Q2) ────────────────────────────────────────────
    domain_path = None
    if args.method == "q2":
        domain_path = args.domain or str(PROJECT_ROOT / "pddl" / "domain.pddl")
        if not Path(domain_path).exists():
            print(f"[ERROR] Domain file not found: {domain_path}")
            sys.exit(1)

    # ── Evaluate ────────────────────────────────────────────────────
    results = []
    for task in tasks:
        print(f"\nEvaluating {task['task_id']} ...")
        if args.method == "q1":
            r = evaluate_q1(task, llm_client)
        else:
            r = evaluate_q2(task, domain_path, llm_client)
        results.append(r)

        status = "✓" if r["goal_success"] else "✗"
        err = f" — {r.get('error', '')}" if r.get("error") else ""
        print(f"  {status} Goal: {r['goal_success']}, Plan valid: {r['plan_valid']}, "
              f"Steps: {r['num_steps']}{err}")

    # ── Summary ─────────────────────────────────────────────────────
    print_summary(results)

    # ── Save detailed results ──────────────────────────────────────
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed results saved to: {args.output}")

    # ── Exit code ──────────────────────────────────────────────────
    all_pass = all(r["plan_valid"] and r["goal_success"] for r in results)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
