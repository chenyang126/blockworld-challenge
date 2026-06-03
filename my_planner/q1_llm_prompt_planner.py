"""
Q1: 纯 LLM Prompt 规划器 —— 学生实现

这是一个基础可用版本（弱 Prompt）。你需要在此基础上优化 Prompt 设计，
提升规划成功率。参考思路：
  - 在 Prompt 中明确四类动作的前提条件
  - 要求 LLM 逐步检查状态，但不输出推理过程
  - 通过 Few-shot 示例帮助 LLM 理解输出格式

当前版本问题（请改进）：
  - 未告知 LLM 动作的前提条件 → LLM 可能生成不可执行的动作
  - 未要求 LLM 进行内部自检 → 长计划容易出错
  - NL-only 任务没有结构化状态时，LLM 需要自行从自然语言提取
"""

import re
from typing import List, Dict


def build_prompt(task: Dict) -> str:
    """
    构造发给 LLM 的 Prompt。当前为基础版本，请优化。
    """
    blocks = task["blocks"]
    initial = task.get("initial_state", [])
    goal = task.get("goal_state", [])
    nl = task.get("natural_language", "")

    # 如果有结构化状态就用，否则只靠自然语言
    if initial and goal:
        init_str = ", ".join(initial)
        goal_str = ", ".join(goal)
    else:
        init_str = f"[需要从自然语言中推断]"
        goal_str = f"[需要从自然语言中推断]"

    prompt = f"""Solve this Blocksworld planning problem.

Available actions (use exact format):
  PICKUP(x)  — pick up x from table (requires: x on table, x clear, hand empty)
  PUTDOWN(x) — put x on table (requires: holding x)
  UNSTACK(x,y) — take x off y (requires: x on y, x clear, hand empty)
  STACK(x,y)  — put x on y (requires: holding x, y clear)

Blocks: {', '.join(blocks)}
Initial: {init_str}
Goal: {goal_str}
Description: {nl}

Output one action per line. Format: ACTION(ARG1,ARG2). No explanation."""

    return prompt


def parse_llm_output(response: str) -> List[str]:
    """
    从 LLM 文本输出中解析动作序列。
    当前为基础版本：匹配大写动作格式，处理 markdown 代码块。
    请根据你的 Prompt 输出格式进行优化。
    """
    # 去除 markdown 代码围栏
    response = re.sub(r'```[a-zA-Z]*\n?', '', response)
    response = re.sub(r'```', '', response)

    actions = []
    # 匹配格式：可选的编号 + ACTION(ARG1,ARG2)
    pattern = re.compile(
        r'^\s*(?:\d+[\.\)]\s*)?(PICKUP|PUTDOWN|UNSTACK|STACK)\s*\(([^)]+)\)\s*$',
        re.IGNORECASE
    )

    for line in response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            name = m.group(1).upper()
            args = [a.strip().upper() for a in m.group(2).split(',')]
            actions.append(f"{name}({','.join(args)})")

    return actions


def plan_with_llm(task: Dict, llm_client) -> List[str]:
    """
    完整 Q1 流程：build_prompt → 调 LLM → parse_llm_output。
    llm_client 提供 .chat(prompt: str) -> str 方法。
    """
    prompt = build_prompt(task)
    response = llm_client.chat(prompt)
    plan = parse_llm_output(response)
    return plan
