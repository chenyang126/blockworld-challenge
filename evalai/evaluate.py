#!/usr/bin/env python3
"""
EvalAI Evaluation Script — Blocksworld 课程设计

此脚本在 EvalAI 评测环境中运行，负责：
1. 设置 Blocksworld 环境
2. 加载学生提交的 Q1 / Q2 代码
3. 使用教师提供的 LLM API 在所有隐藏任务上评测
4. 输出 EvalAI 标准格式的评分结果

学生提交内容：
  - q1_llm_prompt_planner.py
  - q2_llm_pddl_planner.py

环境变量（EvalAI 中由教师配置）：
  - LLM_API_KEY           LLM API Key
  - LLM_PROVIDER          LLM 后端（默认 openai-compatible）
  - LLM_BASE_URL          API 地址
  - LLM_MODEL             模型名称
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path

# ── 路径设置 ─────────────────────────────────────────────────────────
# EvalAI 环境中，当前工作目录是包含所有 challenge 文件的根目录
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, os.getcwd())  # EvalAI 的工作目录（学生代码在这里）

# ── 导入教师模块 ────────────────────────────────────────────────────
from env.blocksworld_env import BlocksworldEnv
from llm_client import LLMClient

# ── LLM 客户端初始化 ────────────────────────────────────────────────
_provider = os.environ.get("LLM_PROVIDER", "openai")
_model = os.environ.get("LLM_MODEL", "gpt-4o")
_api_key = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
_base_url = os.environ.get("LLM_BASE_URL", None)

llm_client = LLMClient(
    provider=_provider,
    model=_model,
    api_key=_api_key,
    base_url=_base_url,
)

# ── 加载隐藏任务 ────────────────────────────────────────────────────
def load_all_tasks():
    """加载全部 21 个隐藏/困难/极限/NL-only 任务"""
    task_dirs = ["tasks/hidden", "tasks/hard", "tasks/extreme", "tasks/nl_only"]
    tasks = []
    for td in task_dirs:
        tpath = BASE_DIR / td
        if tpath.is_dir():
            for fpath in sorted(tpath.glob("*.json")):
                with open(fpath) as f:
                    t = json.load(f)
                    t["_source"] = td  # 记录来源
                    tasks.append(t)
    return tasks


def make_student_task(task):
    """NL-only 任务：剥离结构化状态"""
    st = dict(task)
    if st.get("nl_only"):
        st["initial_state"] = []
        st["goal_state"] = []
    return st


# ── Q1 评测 ─────────────────────────────────────────────────────────
def evaluate_q1(task, q1_module):
    """评测单个任务上的 Q1。返回 dict。"""
    student_task = make_student_task(task)
    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])

    start = time.time()
    try:
        plan = q1_module.plan_with_llm(student_task, llm_client)
    except Exception as e:
        return {
            "task_id": task["task_id"],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "error": str(e)[:200],
            "time_s": round(time.time() - start, 2),
        }

    elapsed = round(time.time() - start, 2)

    if not plan:
        return {
            "task_id": task["task_id"],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "error": "Empty plan",
            "time_s": elapsed,
        }

    result = env.execute_plan(plan)
    goal_ok = env.is_goal_satisfied(task["goal_state"])

    return {
        "task_id": task["task_id"],
        "plan_valid": result["plan_valid"],
        "goal_success": goal_ok,
        "num_steps": len(plan),
        "error": None,
        "time_s": elapsed,
    }


# ── Q2 评测 ─────────────────────────────────────────────────────────
def evaluate_q2(task, q2_module, domain_path):
    """评测单个任务上的 Q2。返回 dict。"""
    student_task = make_student_task(task)
    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])

    start = time.time()
    try:
        plan = q2_module.plan_with_llm_pddl(student_task, str(domain_path), llm_client)
    except Exception as e:
        return {
            "task_id": task["task_id"],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "pddl_success": False,
            "error": str(e)[:200],
            "time_s": round(time.time() - start, 2),
        }

    elapsed = round(time.time() - start, 2)

    if not plan:
        return {
            "task_id": task["task_id"],
            "plan_valid": False,
            "goal_success": False,
            "num_steps": 0,
            "pddl_success": False,
            "error": "Empty plan",
            "time_s": elapsed,
        }

    # 格式规范化（planner 输出小写 → 大写）
    normalised = _normalise_plan(plan)
    result = env.execute_plan(normalised)
    goal_ok = env.is_goal_satisfied(task["goal_state"])

    return {
        "task_id": task["task_id"],
        "plan_valid": result["plan_valid"],
        "goal_success": goal_ok,
        "num_steps": len(normalised),
        "pddl_success": True,
        "error": None,
        "time_s": elapsed,
    }


def _normalise_plan(plan):
    """小写 planner 输出 → 大写 BlocksworldEnv 格式"""
    out = []
    for action in plan:
        action = action.strip().lower().replace("-", "")
        parts = action.split(None, 1)
        if not parts:
            continue
        name = parts[0].upper()
        args_raw = parts[1] if len(parts) > 1 else ""
        args_list = [a.strip().upper() for a in args_raw.split() if a.strip()]
        out.append(f"{name}({','.join(args_list)})")
    return out


# ── 主评测流程 ──────────────────────────────────────────────────────
def main():
    # 1. 加载任务
    tasks = load_all_tasks()
    if not tasks:
        print(json.dumps({
            "result": [{"split": "test", "metrics": {"error": "No tasks found"}}]
        }))
        sys.exit(1)

    print(f"[EvalAI] 加载了 {len(tasks)} 个评测任务", file=sys.stderr)
    print(f"[EvalAI] LLM: {_provider}/{llm_client.model}", file=sys.stderr)

    # 2. 导入学生代码
    try:
        import q1_llm_prompt_planner as q1_module
        print("[EvalAI] Q1 module loaded", file=sys.stderr)
    except ImportError as e:
        print(f"[EvalAI] Q1 import failed: {e}", file=sys.stderr)
        q1_module = None

    try:
        import q2_llm_pddl_planner as q2_module
        print("[EvalAI] Q2 module loaded", file=sys.stderr)
    except ImportError as e:
        print(f"[EvalAI] Q2 import failed: {e}", file=sys.stderr)
        q2_module = None

    # 3. 逐任务评测
    domain_path = BASE_DIR / "pddl" / "domain.pddl"
    q1_results = []
    q2_results = []

    for task in tasks:
        tid = task["task_id"]
        src = task.get("_source", "unknown")

        # Q1
        if q1_module:
            try:
                r = evaluate_q1(task, q1_module)
                q1_results.append(r)
                status = "✓" if r["goal_success"] else "✗"
                print(f"  [Q1] {tid} ({src}): {status} steps={r['num_steps']}", file=sys.stderr)
            except Exception as e:
                print(f"  [Q1] {tid}: ERROR {e}", file=sys.stderr)
                q1_results.append({
                    "task_id": tid, "plan_valid": False, "goal_success": False,
                    "num_steps": 0, "error": str(e)[:200], "time_s": 0
                })
        else:
            q1_results.append({
                "task_id": tid, "plan_valid": False, "goal_success": False,
                "num_steps": 0, "error": "Q1 module not loaded", "time_s": 0
            })

        # Q2
        if q2_module:
            try:
                r = evaluate_q2(task, q2_module, domain_path)
                q2_results.append(r)
                status = "✓" if r["goal_success"] else "✗"
                print(f"  [Q2] {tid} ({src}): {status} steps={r['num_steps']}", file=sys.stderr)
            except Exception as e:
                print(f"  [Q2] {tid}: ERROR {e}", file=sys.stderr)
                q2_results.append({
                    "task_id": tid, "plan_valid": False, "goal_success": False,
                    "num_steps": 0, "pddl_success": False, "error": str(e)[:200], "time_s": 0
                })
        else:
            q2_results.append({
                "task_id": tid, "plan_valid": False, "goal_success": False,
                "num_steps": 0, "pddl_success": False, "error": "Q2 module not loaded", "time_s": 0
            })

    # 4. 计算指标
    n_total = len(tasks)

    q1_goal = sum(1 for r in q1_results if r["goal_success"])
    q1_valid = sum(1 for r in q1_results if r["plan_valid"])
    q1_steps = sum(r["num_steps"] for r in q1_results)
    q1_errors = sum(1 for r in q1_results if r.get("error"))
    q1_time = sum(r.get("time_s", 0) for r in q1_results)

    q2_goal = sum(1 for r in q2_results if r["goal_success"])
    q2_valid = sum(1 for r in q2_results if r["plan_valid"])
    q2_steps = sum(r["num_steps"] for r in q2_results)
    q2_errors = sum(1 for r in q2_results if r.get("error"))
    q2_time = sum(r.get("time_s", 0) for r in q2_results)

    # 5. 按来源分组统计
    sources = ["tasks/hidden", "tasks/hard", "tasks/extreme", "tasks/nl_only"]
    source_metrics = {}
    for src in sources:
        src_q1 = [r for r, t in zip(q1_results, tasks) if t.get("_source") == src]
        src_q2 = [r for r, t in zip(q2_results, tasks) if t.get("_source") == src]
        src_n = len(src_q1)
        source_metrics[src.replace("tasks/", "")] = {
            "count": src_n,
            "q1_goal": sum(1 for r in src_q1 if r["goal_success"]),
            "q2_goal": sum(1 for r in src_q2 if r["goal_success"]),
        }

    # 6. 输出 EvalAI 标准格式
    result = {
        "result": [
            {
                "split": "test",
                "metrics": {
                    # 主要指标
                    "q1_goal_success_rate": round(q1_goal / n_total, 4) if n_total else 0,
                    "q2_goal_success_rate": round(q2_goal / n_total, 4) if n_total else 0,
                    "q1_plan_valid_rate": round(q1_valid / n_total, 4) if n_total else 0,
                    "q2_plan_valid_rate": round(q2_valid / n_total, 4) if n_total else 0,

                    # 综合得分（Q1 25 分 + Q2 30 分 = 55 分机器评分部分）
                    "q1_score": round(25 * q1_goal / n_total, 1) if n_total else 0,
                    "q2_score": round(30 * q2_goal / n_total, 1) if n_total else 0,
                    "machine_total": round(
                        25 * q1_goal / n_total + 30 * q2_goal / n_total, 1
                    ) if n_total else 0,

                    # 辅助指标
                    "q1_avg_steps": round(q1_steps / n_total, 1) if n_total else 0,
                    "q2_avg_steps": round(q2_steps / n_total, 1) if n_total else 0,
                    "q1_errors": q1_errors,
                    "q2_errors": q2_errors,
                    "q1_total_time_s": round(q1_time, 1),
                    "q2_total_time_s": round(q2_time, 1),

                    # 分层统计
                    "hidden_q1": source_metrics.get("hidden", {}).get("q1_goal", 0),
                    "hidden_q2": source_metrics.get("hidden", {}).get("q2_goal", 0),
                    "hard_q1": source_metrics.get("hard", {}).get("q1_goal", 0),
                    "hard_q2": source_metrics.get("hard", {}).get("q2_goal", 0),
                    "extreme_q1": source_metrics.get("extreme", {}).get("q1_goal", 0),
                    "extreme_q2": source_metrics.get("extreme", {}).get("q2_goal", 0),
                    "nl_only_q1": source_metrics.get("nl_only", {}).get("q1_goal", 0),
                    "nl_only_q2": source_metrics.get("nl_only", {}).get("q2_goal", 0),
                }
            }
        ]
    }

    # EvalAI 要求输出 JSON 到 stdout
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 同时输出易读的摘要到 stderr（不影响 EvalAI 解析）
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Q1 Goal Success: {q1_goal}/{n_total} ({100*q1_goal/n_total:.0f}%)", file=sys.stderr)
    print(f"Q2 Goal Success: {q2_goal}/{n_total} ({100*q2_goal/n_total:.0f}%)", file=sys.stderr)
    print(f"Machine Score:    {round(25*q1_goal/n_total+30*q2_goal/n_total,1)}/55", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)


if __name__ == "__main__":
    main()
