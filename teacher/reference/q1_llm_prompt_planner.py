"""
Reference Q1: Pure LLM Prompt Planner

A working reference implementation with a thoughtful prompt design.
"""

import re
from typing import List, Dict


def build_prompt(task: Dict) -> str:
    """
    Build a comprehensive prompt with:
    - Clear action definitions with preconditions
    - Initial and goal states in both structured and natural language
    - Strict output format requirements
    - Request for internal verification without explicit reasoning output
    """
    blocks = task["blocks"]
    initial = task["initial_state"]
    goal = task["goal_state"]
    nl = task.get("natural_language", "")

    prompt = f"""You are an expert Blocksworld planning agent. Your task is to output a valid sequence of actions to transform the initial state into the goal state.

=== ACTION SPACE ===
You have exactly four actions available:

1. PICKUP(x)
   - Preconditions: ontable(x), clear(x), handempty
   - Effect: The arm holds x. x is no longer on the table or clear. The arm is no longer empty.

2. PUTDOWN(x)
   - Preconditions: holding(x)
   - Effect: x is placed on the table. x becomes clear. The arm becomes empty.

3. UNSTACK(x, y)
   - Preconditions: on(x,y), clear(x), handempty
   - Effect: The arm holds x. y becomes clear. x is no longer on y or clear. The arm is no longer empty.

4. STACK(x, y)
   - Preconditions: holding(x), clear(y)
   - Effect: x is placed on y. x becomes clear. The arm becomes empty. y is no longer clear.

=== PRECONDITION RULES ===
- You can only PICKUP a block that is ON THE TABLE and CLEAR (nothing on top of it) and the HAND IS EMPTY.
- You can only PUTDOWN a block that you are HOLDING.
- You can only UNSTACK a block from another if it is CLEAR (nothing on top of it) and the HAND IS EMPTY.
- You can only STACK a block onto another if you are HOLDING the first block and the second block is CLEAR.

=== TASK ===
Blocks: {', '.join(blocks)}

Initial state (structured):
{chr(10).join(f"  {p}" for p in initial)}

Goal state (structured):
{chr(10).join(f"  {p}" for p in goal)}

Natural language description:
{nl}

=== OUTPUT FORMAT ===
Output ONLY the action sequence, ONE action per line, with NO other text. Do not output explanations, reasoning, markdown formatting, or code blocks. Only output the actions.

Example valid output:
UNSTACK(C,A)
PUTDOWN(C)
PICKUP(B)
STACK(B,C)
PICKUP(A)
STACK(A,B)

=== VERIFICATION ===
Before finalizing, mentally check that each action's preconditions are satisfied at the moment it executes. The state changes after each action — make sure you are tracking the current state correctly.

Now output the plan:"""
    return prompt


def parse_llm_output(response: str) -> List[str]:
    """
    Parse LLM output: extract lines matching action format.
    Handles markdown code blocks, extra whitespace, and numbering.
    """
    # Strip markdown code fences if present
    # Remove ``` blocks
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
    """
    Full Q1 pipeline: build prompt → call LLM → parse output.
    """
    prompt = build_prompt(task)
    response = llm_client.chat(prompt)
    plan = parse_llm_output(response)
    return plan
