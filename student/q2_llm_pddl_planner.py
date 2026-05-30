"""
Q2: LLM + PDDL 规划器 —— 学生实现

这是一个基础可用版本（弱 Prompt）。你需要在此基础上优化 Prompt 设计，
提升 PDDL problem 文件的生成正确率。参考思路：
  - 在 Prompt 中给出正确的 PDDL problem 示例
  - 明确告知 LLM 谓词语法（空格分隔，非逗号）
  - 要求 LLM 检查 :objects 是否包含了所有积木
  - NL-only 任务需要让 LLM 从自然语言中提取状态

当前版本问题（请改进）：
  - 未给出 PDDL 语法示例 → LLM 可能生成格式错误的 problem.pddl
  - 未强调谓词参数用空格分隔 → LLM 可能写成 (on A,B) 而非 (on A B)
  - NL-only 任务没有结构化状态时，LLM 难以正确翻译
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
    构造让 LLM 生成 PDDL problem 文件的 Prompt。当前为基础版本，请优化。
    """
    blocks = task["blocks"]
    initial = task.get("initial_state", [])
    goal = task.get("goal_state", [])
    nl = task.get("natural_language", "")

    # 如果有结构化状态，格式化为 PDDL 语法
    if initial:
        init_str = "\n".join(
            f"    ({p.replace('(', ' ').replace(',', ' ').replace(')', '')})"
            for p in initial
        )
    else:
        init_str = f"    ; 需要从自然语言中推断初始状态\n    ; {nl[:200]}"

    if goal:
        goal_str = "\n".join(
            f"    ({p.replace('(', ' ').replace(',', ' ').replace(')', '')})"
            for p in goal
        )
    else:
        goal_str = f"    ; 需要从自然语言中推断目标状态\n    ; {nl[200:400] if len(nl) > 200 else nl}"

    objects_str = " ".join(blocks)

    prompt = f"""Generate a PDDL problem file for this Blocksworld task.

Domain:
{domain_pddl}

Blocks: {', '.join(blocks)}

Initial state:
{init_str}

Goal state:
{goal_str}

Natural language description:
{nl}

Output the full PDDL problem file. Use this structure:
(define (problem {task['task_id']})
  (:domain blocksworld)
  (:objects {objects_str} - block)
  (:init ...)
  (:goal (and ...))
)"""

    return prompt


def generate_problem_pddl(task: Dict, domain_pddl: str, llm_client) -> str:
    """
    调用 LLM 生成 PDDL problem 文件文本。
    当前为基础版本：仅去除 markdown 围栏。请增加更多鲁棒性处理。
    """
    prompt = build_pddl_prompt(task, domain_pddl)
    response = llm_client.chat(prompt)

    # 清理输出：去除 markdown 围栏和多余空白
    response = response.strip()
    response = re.sub(r'```[a-zA-Z]*\s*', '', response)
    response = re.sub(r'```', '', response)
    response = response.strip()

    # 如果输出不是以 (define 开头，尝试在文本中查找
    if not response.startswith('(define'):
        m = re.search(r'\(define\s*\(problem.*', response, re.DOTALL)
        if m:
            response = m.group(0).strip()

    return response


def solve_pddl(domain_path: str, problem_path: str) -> List[str]:
    """
    调用 PDDL 规划器求解。使用 pyperplan（纯 Python，BFS 搜索）。
    如未安装：pip install pyperplan
    """
    from pyperplan import planner
    from pyperplan.search import breadth_first_search

    plan = planner.search_plan(
        domain_path, problem_path, breadth_first_search, None
    )
    if plan is None:
        raise RuntimeError(
            "pyperplan: 未找到可行计划（问题可能无解或状态描述错误）"
        )

    # str(op) 格式为 "(pickup d)\n  PRE: ..." → 取首行 → "pickup d"
    return [str(op).split("\n")[0].strip("() ") for op in plan]


def plan_with_llm_pddl(task: Dict, domain_path: str, llm_client) -> List[str]:
    """
    完整 Q2 流程：
    1. 读取 domain.pddl
    2. LLM 生成 problem.pddl
    3. 保存 problem.pddl 到 outputs/ 目录
    4. 调用 PDDL 规划器求解
    5. 返回动作序列
    """
    # 1. 读取 domain
    with open(domain_path) as f:
        domain_pddl = f.read()

    # 2-3. LLM 生成 problem.pddl 并保存
    problem_pddl = generate_problem_pddl(task, domain_pddl, llm_client)

    output_dir = Path("outputs") / task["task_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    problem_path = output_dir / "problem.pddl"
    with open(problem_path, "w") as f:
        f.write(problem_pddl)
    print(f"  Problem PDDL 已保存到: {problem_path}")

    # 4-5. 调用规划器，返回动作序列
    plan = solve_pddl(domain_path, str(problem_path))
    return plan
