"""Weak Q1 prompt — minimal instruction, no preconditions."""
import re
from typing import List, Dict

def build_prompt(task: Dict) -> str:
    blocks = task["blocks"]
    initial = task.get("initial_state", [])
    goal = task.get("goal_state", [])
    nl = task.get("natural_language", "")
    init_str = ", ".join(initial) if initial else f"[described in natural language: {nl[:200]}]"
    goal_str = ", ".join(goal) if goal else f"[described in natural language: {nl[200:400] if len(nl)>200 else nl}]"
    return f"""Solve this Blocksworld problem.

Blocks: {', '.join(blocks)}
Initial: {init_str}
Goal: {goal_str}

Output one action per line."""
    return prompt

def parse_llm_output(response: str) -> List[str]:
    response = re.sub(r'```[a-zA-Z]*\n', '\n', response)
    response = re.sub(r'```', '', response)
    actions = []
    action_pattern = re.compile(
        r'^\s*(?:\d+[\.\)]\s*)?(PICKUP|PUTDOWN|UNSTACK|STACK)\s*\(([^)]+)\)\s*$',
        re.IGNORECASE
    )
    for line in response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = action_pattern.match(line)
        if m:
            name = m.group(1).upper()
            args = [a.strip() for a in m.group(2).split(',')]
            actions.append(f"{name}({','.join(args)})")
    return actions

def plan_with_llm(task: Dict, llm_client) -> List[str]:
    prompt = build_prompt(task)
    response = llm_client.chat(prompt)
    return parse_llm_output(response)
