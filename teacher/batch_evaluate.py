#!/usr/bin/env python3
"""
教师端批量评测脚本

用法：
  python teacher/batch_evaluate.py --submissions teacher/submissions/ [--output results.csv]

工作流程：
  1. 扫描 submissions/ 下的所有 zip 文件
  2. 对每个 zip 解压，导入 student 代码
  3. 在全部 25 个任务（public + hidden + hard + extreme + nl_only）上评测 Q1 和 Q2
  4. 输出汇总 CSV 表格

环境变量：
  LLM_API_KEY     — LLM API Key（必需）
  LLM_PROVIDER    — 默认 openai-compatible
  LLM_BASE_URL    — 默认 https://api.deepseek.com
  LLM_MODEL       — 默认 deepseek-chat
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from env.blocksworld_env import BlocksworldEnv
from llm_client import LLMClient


def load_tasks():
    tasks = []
    task_root = PROJECT_ROOT / "tasks"
    for sub in ["public", "hidden", "hard", "extreme", "nl_only"]:
        d = task_root / sub
        if d.is_dir():
            for fp in sorted(d.glob("*.json")):
                with open(fp) as f:
                    t = json.load(f)
                    t["_source"] = f"tasks/{sub}"
                    tasks.append(t)
    return tasks


def make_student_task(task):
    st = dict(task)
    if st.get("nl_only"):
        st["initial_state"] = []
        st["goal_state"] = []
    return st


def import_student_code(zip_path):
    """从 zip 中提取并导入学生代码。返回 (q1_module, q2_module, error)"""
    import importlib.util
    tmpdir = tempfile.mkdtemp(prefix="eval_")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)

        # 查找 my_planner 目录
        planner_dirs = list(Path(tmpdir).rglob("my_planner"))
        if not planner_dirs:
            return None, None, "未找到 my_planner/ 目录"

        pd = planner_dirs[0]
        sys.path.insert(0, str(pd.parent))
        sys.path.insert(0, str(pd))

        # Q1
        q1_file = pd / "q1_llm_prompt_planner.py"
        if not q1_file.exists():
            return None, None, "未找到 q1_llm_prompt_planner.py"
        spec = importlib.util.spec_from_file_location("q1_student", str(q1_file))
        q1 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(q1)

        # Q2
        q2_file = pd / "q2_llm_pddl_planner.py"
        if not q2_file.exists():
            return None, None, "未找到 q2_llm_pddl_planner.py"
        spec2 = importlib.util.spec_from_file_location("q2_student", str(q2_file))
        q2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(q2)

        return q1, q2, None
    except Exception as e:
        return None, None, str(e)


def eval_one_task_q1(task, q1_module, llm_client):
    st = make_student_task(task)
    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])
    t0 = time.time()
    try:
        plan = q1_module.plan_with_llm(st, llm_client)
    except Exception as e:
        return {"goal": False, "valid": False, "steps": 0, "error": str(e)[:100], "time": round(time.time()-t0, 1)}
    if not plan:
        return {"goal": False, "valid": False, "steps": 0, "error": "Empty plan", "time": round(time.time()-t0, 1)}
    r = env.execute_plan(plan)
    return {"goal": env.is_goal_satisfied(task["goal_state"]), "valid": r["plan_valid"],
            "steps": len(plan), "error": None, "time": round(time.time()-t0, 1)}


def eval_one_task_q2(task, q2_module, llm_client, domain_path):
    st = make_student_task(task)
    env = BlocksworldEnv(task["blocks"])
    env.reset(task["initial_state"])
    t0 = time.time()
    try:
        plan = q2_module.plan_with_llm_pddl(st, str(domain_path), llm_client)
    except Exception as e:
        return {"goal": False, "valid": False, "steps": 0, "error": str(e)[:100], "time": round(time.time()-t0, 1)}
    if not plan:
        return {"goal": False, "valid": False, "steps": 0, "error": "Empty plan", "time": round(time.time()-t0, 1)}
    # normalise
    nplan = []
    for a in plan:
        a = a.strip().lower().replace("-", "")
        parts = a.split(None, 1)
        if not parts: continue
        name = parts[0].upper()
        args = parts[1].split() if len(parts) > 1 else []
        args = [x.upper() for x in args]
        nplan.append(f"{name}({','.join(args)})")
    r = env.execute_plan(nplan)
    return {"goal": env.is_goal_satisfied(task["goal_state"]), "valid": r["plan_valid"],
            "steps": len(nplan), "error": None, "time": round(time.time()-t0, 1)}


def main():
    parser = argparse.ArgumentParser(description="批量评测学生提交")
    parser.add_argument("--submissions", required=True, help="学生 zip 文件目录")
    parser.add_argument("--output", default="results.csv", help="输出 CSV 路径")
    parser.add_argument("--single", help="仅评测单个学生 zip")
    args = parser.parse_args()

    # LLM
    provider = os.environ.get("LLM_PROVIDER", "openai-compatible")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    api_key = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        print("[ERROR] 请设置 LLM_API_KEY 环境变量")
        sys.exit(1)
    llm_client = LLMClient(provider=provider, model=model, api_key=api_key, base_url=base_url)
    print(f"LLM: {provider}/{model}")

    # Tasks
    tasks = load_tasks()
    print(f"任务数: {len(tasks)}")

    # Find submissions
    sub_dir = Path(args.submissions)
    zips = sorted(sub_dir.glob("*.zip")) if not args.single else [Path(args.single)]
    if not zips:
        print(f"[ERROR] {sub_dir} 下没有找到 zip 文件")
        sys.exit(1)
    print(f"学生数: {len(zips)}")

    domain_path = PROJECT_ROOT / "pddl" / "domain.pddl"
    results = []

    for zip_path in zips:
        student_id = zip_path.stem
        print(f"\n{'='*50}")
        print(f"评测: {student_id}")
        print(f"{'='*50}")

        q1, q2, err = import_student_code(zip_path)
        if err:
            print(f"  [ERROR] {err}")
            results.append({
                "student": student_id,
                "q1_goal": 0, "q1_valid": 0, "q1_steps": 0, "q1_time": 0,
                "q2_goal": 0, "q2_valid": 0, "q2_steps": 0, "q2_time": 0,
                "total_tasks": len(tasks), "error": err
            })
            continue

        n = len(tasks)
        q1_goal, q1_valid, q1_steps, q1_time = 0, 0, 0, 0
        q2_goal, q2_valid, q2_steps, q2_time = 0, 0, 0, 0

        for task in tasks:
            # Q1
            r1 = eval_one_task_q1(task, q1, llm_client)
            if r1["goal"]: q1_goal += 1
            if r1["valid"]: q1_valid += 1
            q1_steps += r1["steps"]
            q1_time += r1["time"]

            # Q2
            r2 = eval_one_task_q2(task, q2, llm_client, domain_path)
            if r2["goal"]: q2_goal += 1
            if r2["valid"]: q2_valid += 1
            q2_steps += r2["steps"]
            q2_time += r2["time"]

            print(f"  {task['task_id']}: Q1={'✓' if r1['goal'] else '✗'} Q2={'✓' if r2['goal'] else '✗'}")

        row = {
            "student": student_id,
            "q1_goal": q1_goal, "q1_valid": q1_valid,
            "q1_steps": q1_steps, "q1_time": round(q1_time, 1),
            "q2_goal": q2_goal, "q2_valid": q2_valid,
            "q2_steps": q2_steps, "q2_time": round(q2_time, 1),
            "total_tasks": n, "error": ""
        }
        row["q1_rate"] = f"{q1_goal/n*100:.0f}%"
        row["q2_rate"] = f"{q2_goal/n*100:.0f}%"
        row["score"] = round(25*q1_goal/n + 30*q2_goal/n, 1)
        results.append(row)
        print(f"  结果: Q1={q1_goal}/{n} Q2={q2_goal}/{n} 机器评分={row['score']}/55")

    # 写入 CSV
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "student", "q1_goal", "q1_valid", "q1_rate", "q1_steps", "q1_time",
            "q2_goal", "q2_valid", "q2_rate", "q2_steps", "q2_time",
            "total_tasks", "score", "error"
        ])
        w.writeheader()
        w.writerows(results)
    print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
