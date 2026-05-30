"""
Reference Q2: LLM + PDDL Planner

A working reference implementation that:
1. Reads domain.pddl
2. Asks LLM to generate a problem.pddl
3. Calls pyperplan (or fast-downward) to solve
4. Returns the action plan
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict


def build_pddl_prompt(task: Dict, domain_pddl: str) -> str:
    """
    Build a prompt instructing the LLM to output a valid PDDL problem file.
    """
    blocks = task["blocks"]
    initial = task["initial_state"]
    goal = task["goal_state"]

    # Build a human-readable block list and init/goal descriptions
    objects_str = " ".join(blocks)

    init_str = "\n".join(f"    ({p.replace('(', ' ').replace(',', ' ').replace(')', '')})" for p in initial)

    # Convert goal predicates to PDDL format
    goal_preds = []
    for p in goal:
        # p like "on(A,B)" → "(on A B)"
        inner = p.replace("(", " ").replace(",", " ").replace(")", "")
        goal_preds.append(f"    ({inner})")

    goal_str = "\n".join(goal_preds)
    n_goal = len(goal)

    # Build a compact example
    init_example = "\n".join(f"    ({p.replace('(', ' ').replace(',', ' ').replace(')', '')})" for p in initial)
    goal_example = "\n".join(f"    ({p.replace('(', ' ').replace(',', ' ').replace(')', '')})" for p in goal)

    prompt = f"""You are an expert in PDDL (Planning Domain Definition Language). Your task is to generate a valid PDDL problem file for a Blocksworld planning task.

=== FIXED DOMAIN (DO NOT MODIFY) ===
{domain_pddl}

=== TASK ===
Blocks: {', '.join(blocks)}

Initial state:
{chr(10).join(f"  {p}" for p in initial)}

Goal state:
{chr(10).join(f"  {p}" for p in goal)}

Natural language description:
{task.get('natural_language', '')}

=== YOUR JOB ===
Generate ONLY the PDDL problem file. Use EXACTLY this format:

(define (problem {task['task_id']})
  (:domain blocksworld)
  (:objects {objects_str} - block)
  (:init
{init_example}
  )
  (:goal (and
{goal_example}
  ))
)

=== RULES ===
1. Use :domain blocksworld (all lowercase).
2. Declare all {len(blocks)} blocks as :objects of type block.
3. Use predicates EXACTLY as defined in the domain: on, ontable, clear, holding, handempty.
4. Predicate syntax: (predicate arg1 arg2) — with spaces, NOT commas.
5. The goal must be wrapped in (and ...) even if there is only one goal predicate.
6. Output ONLY the PDDL problem file. No markdown, no code fences, no explanations.

Now output the problem file:"""
    return prompt


def generate_problem_pddl(task: Dict, domain_pddl: str, llm_client) -> str:
    """
    Call LLM to generate a PDDL problem file.
    """
    prompt = build_pddl_prompt(task, domain_pddl)
    response = llm_client.chat(prompt)

    # Clean the response: strip markdown fences
    response = response.strip()
    # Remove ```lisp or ``` blocks
    response = re.sub(r'```[a-zA-Z]*\s*', '', response)
    response = re.sub(r'```', '', response)
    response = response.strip()

    # Basic validation: should start with (define
    if not response.startswith('(define'):
        # Try to find the define block
        m = re.search(r'\(define\s*\(problem.*', response, re.DOTALL)
        if m:
            response = m.group(0).strip()

    return response


def solve_pddl(domain_path: str, problem_path: str) -> List[str]:
    """
    Solve a PDDL problem using the configured planner.

    Tries pyperplan first (lightweight, pure Python), then falls back
    to fast-downward if installed.
    """
    # Try pyperplan first
    try:
        return _solve_with_pyperplan(domain_path, problem_path)
    except (ImportError, Exception) as e:
        print(f"  [INFO] pyperplan failed ({e}), trying fast-downward ...")

    # Try fast-downward
    try:
        return _solve_with_fast_downward(domain_path, problem_path)
    except Exception as e:
        raise RuntimeError(
            f"PDDL planning failed. Tried pyperplan and fast-downward.\n"
            f"Install at least one: pip install pyperplan\n"
            f"Error: {e}"
        )


def _solve_with_pyperplan(domain_path: str, problem_path: str) -> List[str]:
    """Use pyperplan to solve the PDDL problem."""
    from pyperplan import planner
    from pyperplan.search import breadth_first_search

    # breadth_first_search guarantees optimal (shortest) plan
    plan = planner.search_plan(
        domain_path, problem_path, breadth_first_search, None
    )
    if plan is None:
        raise RuntimeError("pyperplan: no plan found")

    # str(op) gives e.g. "(pickup d)\n  PRE: ..." → take first line → "pickup d"
    return [str(op).split("\n")[0].strip("() ") for op in plan]


def _solve_with_fast_downward(domain_path: str, problem_path: str) -> List[str]:
    """Use Fast Downward to solve the PDDL problem."""
    # Find the fast-downward executable
    fd_candidates = [
        "fast-downward",
        "fast-downward.py",
        "/usr/bin/fast-downward",
        os.path.expanduser("~/fast-downward/fast-downward.py"),
    ]

    fd_exe = None
    for c in fd_candidates:
        # just check if the command exists
        result = subprocess.run(
            ["which", c], capture_output=True, text=True
        )
        if result.returncode == 0:
            fd_exe = c
            break

    if fd_exe is None:
        raise RuntimeError(
            "fast-downward not found. Install it or use pyperplan."
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        sas_plan = os.path.join(tmpdir, "sas_plan")

        cmd = [
            fd_exe,
            "--alias", "lama-first",
            "--plan-file", sas_plan,
            domain_path,
            problem_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 and not os.path.exists(sas_plan):
            raise RuntimeError(
                f"Fast Downward failed:\n{result.stderr[:500]}"
            )

        if not os.path.exists(sas_plan):
            # Plan might be in current directory
            sas_plan = "sas_plan"

        if not os.path.exists(sas_plan):
            return []

        with open(sas_plan) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith(';')]

    # Parse FD output: "(unstack c a)" → "unstack c a"
    actions = []
    for line in lines:
        # Remove surrounding parentheses
        line = line.strip().lstrip('(').rstrip(')')
        actions.append(line)

    return actions


def plan_with_llm_pddl(task: Dict, domain_path: str, llm_client) -> List[str]:
    """
    Full Q2 pipeline:
    1. Read domain.pddl
    2. LLM generates problem.pddl
    3. PDDL planner solves
    4. Return action sequence
    """
    # Read domain
    with open(domain_path) as f:
        domain_pddl = f.read()

    # Generate problem PDDL via LLM
    problem_pddl = generate_problem_pddl(task, domain_pddl, llm_client)

    # Save problem to temp file
    output_dir = Path("outputs") / task["task_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    problem_path = output_dir / "problem.pddl"
    with open(problem_path, "w") as f:
        f.write(problem_pddl)
    print(f"  Saved problem PDDL to: {problem_path}")

    # Call planner
    plan = solve_pddl(domain_path, str(problem_path))

    return plan
