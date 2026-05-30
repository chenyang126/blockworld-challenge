"""Weak Q2 prompt — minimal PDDL instruction."""
import os, re, subprocess, sys, tempfile
from pathlib import Path
from typing import List, Dict

def build_pddl_prompt(task: Dict, domain_pddl: str) -> str:
    blocks = task["blocks"]
    initial = task.get("initial_state", [])
    goal = task.get("goal_state", [])
    nl = task.get("natural_language", "")
    init_str = "\n".join(f"    ({p.replace('(', ' ').replace(',', ' ').replace(')', '')})" for p in initial) if initial else f"    ; from NL: {nl[:100]}"
    goal_str = "\n".join(f"    ({p.replace('(', ' ').replace(',', ' ').replace(')', '')})" for p in goal) if goal else f"    ; from NL: {nl[100:200] if len(nl)>100 else nl}"
    return f"""Generate a PDDL problem file for this Blocksworld task.

Domain:
{domain_pddl}

Blocks: {', '.join(blocks)}
Initial: {init_str}
Goal: {goal_str}

Output the problem PDDL."""

def generate_problem_pddl(task, domain_pddl, llm_client):
    prompt = build_pddl_prompt(task, domain_pddl)
    response = llm_client.chat(prompt)
    response = re.sub(r'```[a-zA-Z]*\s*', '', response.strip())
    response = re.sub(r'```', '', response).strip()
    if not response.startswith('(define'):
        m = re.search(r'\(define\s*\(problem.*', response, re.DOTALL)
        if m: response = m.group(0).strip()
    return response

def solve_pddl(domain_path, problem_path):
    from pyperplan import planner
    from pyperplan.search import breadth_first_search
    plan = planner.search_plan(domain_path, problem_path, breadth_first_search, None)
    if plan is None: raise RuntimeError("no plan found")
    return [str(op).split("\n")[0].strip("() ") for op in plan]

def plan_with_llm_pddl(task, domain_path, llm_client):
    with open(domain_path) as f: domain_pddl = f.read()
    problem_pddl = generate_problem_pddl(task, domain_pddl, llm_client)
    output_dir = Path("outputs") / task["task_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "problem.pddl", "w") as f: f.write(problem_pddl)
    return solve_pddl(domain_path, str(output_dir / "problem.pddl"))
