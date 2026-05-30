"""
EvalAI Evaluation Main Script — Blocksworld Challenge

评测入口：evaluate(submission_path, annotation_path, output_path)
EvalAI 评测环境会调用此函数。

学生提交内容 (submission_path 下):
  - q1_llm_prompt_planner.py
  - q2_llm_pddl_planner.py

环境变量:
  - LLM_API_KEY        LLM API Key
  - LLM_PROVIDER       LLM 后端
  - LLM_BASE_URL       API 地址
  - LLM_MODEL          模型名称
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path

# 将 evaluation_script 目录加入 path（包含 env/, pddl/, tasks/, llm_client.py）
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from env.blocksworld_env import BlocksworldEnv
from llm_client import LLMClient


def evaluate(submission_path, annotation_path, output_path, submission_metadata=None, **kwargs):
    """EvalAI 评测入口。"""
    try:
        _run_evaluation(submission_path, annotation_path, output_path)
    except Exception as e:
        _write_error(output_path, f"Evaluation crashed: {str(e)}\n{traceback.format_exc()}")


def _run_evaluation(submission_path, annotation_path, output_path):
    # 1. 将 submission 目录加入 import path
    sys.path.insert(0, str(submission_path))

    # 2. 初始化 LLM 客户端（默认使用 DeepSeek，也可通过环境变量覆盖）
    provider = os.environ.get("LLM_PROVIDER", "openai-compatible")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    api_key = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "sk-4c33138d8c5f4343ba3bb22a3484c4ef"))
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")

    if not api_key:
        _write_error(output_path, "LLM_API_KEY not set in environment")
        return

    llm_client = LLMClient(
        provider=provider, model=model,
        api_key=api_key, base_url=base_url,
    )

    # 3. 导入学生模块
    try:
        sys.path.insert(0, submission_path)
        import q1_llm_prompt_planner as q1_module
    except ImportError as e:
        _write_error(output_path, f"Q1 import failed: {e}")
        return

    try:
        import q2_llm_pddl_planner as q2_module
    except ImportError as e:
        _write_error(output_path, f"Q2 import failed: {e}")
        return

    # 4. 加载所有隐藏任务
    tasks = _load_tasks()
    if not tasks:
        _write_error(output_path, "No tasks found")
        return

    # 5. 逐任务评测
    domain_path = SCRIPT_DIR / "pddl" / "domain.pddl"
    q1_results, q2_results = [], []

    for task in tasks:
        # Q1
        try:
            q1_results.append(_eval_q1(task, q1_module, llm_client))
        except Exception as e:
            q1_results.append(_error_result(task["task_id"], str(e)))

        # Q2
        try:
            q2_results.append(_eval_q2(task, q2_module, llm_client, domain_path))
        except Exception as e:
            q2_results.append(_error_result(task["task_id"], str(e)))

    # 6. 计算得分并输出
    n = len(tasks)
    q1_goal = sum(1 for r in q1_results if r["goal_success"])
    q2_goal = sum(1 for r in q2_results if r["goal_success"])
    q1_valid = sum(1 for r in q1_results if r["plan_valid"])
    q2_valid = sum(1 for r in q2_results if r["plan_valid"])
    q1_errs = sum(1 for r in q1_results if r.get("error"))
    q2_errs = sum(1 for r in q2_results if r.get("error"))
    q1_time = sum(r.get("time_s", 0) for r in q1_results)
    q2_time = sum(r.get("time_s", 0) for r in q2_results)

    # 按来源分层
    sources = {}
    for r, t in zip(q1_results, tasks):
        src = t.get("_source", "unknown")
        sources.setdefault(src, {"q1": 0, "q2": 0, "n": 0})
        sources[src]["n"] += 1
        if r["goal_success"]:
            sources[src]["q1"] += 1
    for r, t in zip(q2_results, tasks):
        src = t.get("_source", "unknown")
        if r["goal_success"]:
            sources.setdefault(src, {"q1": 0, "q2": 0, "n": 0})["q2"] += 1

    result = {
        "result": [{
            "split": "test",
            "metrics": {
                "q1_goal_success_rate": round(q1_goal / n, 4) if n else 0,
                "q2_goal_success_rate": round(q2_goal / n, 4) if n else 0,
                "q1_plan_valid_rate": round(q1_valid / n, 4) if n else 0,
                "q2_plan_valid_rate": round(q2_valid / n, 4) if n else 0,
                "q1_score": round(25 * q1_goal / n, 1) if n else 0,
                "q2_score": round(30 * q2_goal / n, 1) if n else 0,
                "machine_total": round(25 * q1_goal / n + 30 * q2_goal / n, 1) if n else 0,
                "q1_errors": q1_errs,
                "q2_errors": q2_errs,
                "q1_total_time_s": round(q1_time, 1),
                "q2_total_time_s": round(q2_time, 1),
                "hidden_q1": sources.get("tasks/hidden", {}).get("q1", 0),
                "hidden_q2": sources.get("tasks/hidden", {}).get("q2", 0),
                "hard_q1": sources.get("tasks/hard", {}).get("q1", 0),
                "hard_q2": sources.get("tasks/hard", {}).get("q2", 0),
                "extreme_q1": sources.get("tasks/extreme", {}).get("q1", 0),
                "extreme_q2": sources.get("tasks/extreme", {}).get("q2", 0),
                "nl_only_q1": sources.get("tasks/nl_only", {}).get("q1", 0),
                "nl_only_q2": sources.get("tasks/nl_only", {}).get("q2", 0),
            }
        }]
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[EvalAI] Results written to {output_path}")


# ── helpers ─────────────────────────────────────────────────────────

def _load_tasks():
    tasks = []
    task_root = SCRIPT_DIR / "tasks"
    for sub in ["hidden", "hard", "extreme", "nl_only"]:
        d = task_root / sub
        if d.is_dir():
            for fp in sorted(d.glob("*.json")):
                with open(fp) as f:
                    t = json.load(f)
                    t["_source"] = f"tasks/{sub}"
                    tasks.append(t)
    return tasks


def _make_student_task(task):
    st = dict(task)
    if st.get("nl_only"):
        st["initial_state"] = []
        st["goal_state"] = []
    return st


def _eval_q1(task, q1_module, llm_client):
    st = _make_student_task(task)
    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])
    t0 = time.time()
    try:
        plan = q1_module.plan_with_llm(st, llm_client)
    except Exception as e:
        return _error_result(task["task_id"], str(e), time.time() - t0)
    elapsed = round(time.time() - t0, 2)
    if not plan:
        return {"task_id": task["task_id"], "plan_valid": False, "goal_success": False, "num_steps": 0, "error": "Empty plan", "time_s": elapsed}
    r = env.execute_plan(plan)
    return {"task_id": task["task_id"], "plan_valid": r["plan_valid"], "goal_success": env.is_goal_satisfied(task["goal_state"]), "num_steps": len(plan), "error": None, "time_s": elapsed}


def _eval_q2(task, q2_module, llm_client, domain_path):
    st = _make_student_task(task)
    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])
    t0 = time.time()
    try:
        plan = q2_module.plan_with_llm_pddl(st, str(domain_path), llm_client)
    except Exception as e:
        return _error_result(task["task_id"], str(e), time.time() - t0)
    elapsed = round(time.time() - t0, 2)
    if not plan:
        return {"task_id": task["task_id"], "plan_valid": False, "goal_success": False, "num_steps": 0, "error": "Empty plan", "time_s": elapsed}
    nplan = _normalise(plan)
    r = env.execute_plan(nplan)
    return {"task_id": task["task_id"], "plan_valid": r["plan_valid"], "goal_success": env.is_goal_satisfied(task["goal_state"]), "num_steps": len(nplan), "error": None, "time_s": elapsed}


def _normalise(plan):
    out = []
    for a in plan:
        a = a.strip().lower().replace("-", "")
        parts = a.split(None, 1)
        if not parts: continue
        name = parts[0].upper()
        args = parts[1].split() if len(parts) > 1 else []
        args = [x.upper() for x in args]
        out.append(f"{name}({','.join(args)})")
    return out


def _error_result(task_id, msg, elapsed=0):
    return {"task_id": task_id, "plan_valid": False, "goal_success": False, "num_steps": 0, "error": msg[:200], "time_s": round(elapsed, 2)}


def _write_error(output_path, msg):
    with open(output_path, "w") as f:
        json.dump({"result": [{"split": "test", "metrics": {"error": msg}}]}, f)
    print(f"[EvalAI ERROR] {msg}")
