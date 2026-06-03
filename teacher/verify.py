#!/usr/bin/env python3
"""
教师端验证脚本 — 重新评测学生提交，对比自测结果

用法：
  python teacher/verify.py --submission 学号_姓名.zip [--output report.json]

流程：
  1. 解压学生提交
  2. 用教师的 LLM API 重新评测
  3. 与学生的 results.json 对比
  4. 标记差异（防作弊）

环境变量：
  LLM_API_KEY — 教师 API Key（必需）
"""

import argparse
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from env.blocksworld_env import BlocksworldEnv
from llm_client import LLMClient


def load_all_tasks():
    tasks = []
    task_root = PROJECT_ROOT / "tasks"
    for sub in ["public", "hidden", "hard", "extreme", "nl_only"]:
        d = task_root / sub
        if d.is_dir():
            for fp in sorted(d.glob("*.json")):
                with open(fp) as f:
                    t = json.load(f)
                    t["_source"] = sub
                    tasks.append(t)
    return tasks


def import_from_zip(zip_path):
    """从 zip 中提取学生代码。返回 (q1_module, q2_module, student_results, metadata)"""
    import importlib.util
    tmpdir = tempfile.mkdtemp(prefix="verify_")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmpdir)
    root = Path(tmpdir)

    # 查找 my_planner 目录
    planner_dirs = list(root.rglob("my_planner"))
    if not planner_dirs:
        return None, None, None, {"error": "未找到 my_planner/ 目录"}
    pd = planner_dirs[0]
    sys.path.insert(0, str(pd.parent))
    sys.path.insert(0, str(pd))

    # 导入 Q1
    q1_file = pd / "q1_llm_prompt_planner.py"
    if not q1_file.exists():
        return None, None, None, {"error": "未找到 q1_llm_prompt_planner.py"}
    spec = importlib.util.spec_from_file_location("q1_v", str(q1_file))
    q1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q1)

    # 导入 Q2
    q2_file = pd / "q2_llm_pddl_planner.py"
    if not q2_file.exists():
        return None, None, None, {"error": "未找到 q2_llm_pddl_planner.py"}
    spec2 = importlib.util.spec_from_file_location("q2_v", str(q2_file))
    q2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(q2)

    # 读取学生自测结果
    results_files = list(root.rglob("results.json"))
    student_results = None
    if results_files:
        with open(results_files[0]) as f:
            student_results = json.load(f)

    return q1, q2, student_results, {"error": None}


def normalise(plan):
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


def main():
    parser = argparse.ArgumentParser(description="教师端验证学生提交")
    parser.add_argument("--submission", required=True, help="学生 zip 路径")
    parser.add_argument("--output", default=None, help="输出 JSON 路径")
    args = parser.parse_args()

    if not Path(args.submission).exists():
        print(f"[ERROR] 文件不存在: {args.submission}")
        sys.exit(1)

    # LLM
    provider = os.environ.get("LLM_PROVIDER", "openai-compatible")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    api_key = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        print("[ERROR] 请设置 LLM_API_KEY")
        sys.exit(1)
    llm_client = LLMClient(provider=provider, model=model, api_key=api_key, base_url=base_url)

    # 导入学生代码
    q1, q2, student_res, meta = import_from_zip(args.submission)
    if meta["error"]:
        print(f"[ERROR] {meta['error']}")
        sys.exit(1)

    # 评测
    tasks = load_all_tasks()
    domain_path = PROJECT_ROOT / "pddl" / "domain.pddl"
    print(f"评测 {len(tasks)} 个任务...")
    print(f"{'Task':<14} {'Q1_学生':<10} {'Q1_教师':<10} {'Q2_学生':<10} {'Q2_教师':<10} {'状态'}")
    print("-" * 65)

    verify_results = []
    q1_match, q2_match = 0, 0
    q1_goal_t, q2_goal_t = 0, 0

    for task in tasks:
        tid = task["task_id"]
        st = dict(task)
        if st.get("nl_only"):
            st["initial_state"] = []
            st["goal_state"] = []

        # Q1 teacher eval
        t0 = time.time()
        t_q1_goal = False
        try:
            plan = q1.plan_with_llm(st, llm_client)
            if plan:
                env = BlocksworldEnv(task["blocks"])
                env.reset(task["initial_state"])
                env.execute_plan(plan)
                t_q1_goal = env.is_goal_satisfied(task["goal_state"])
        except Exception:
            pass
        t_q1_time = round(time.time() - t0, 2)

        # Q2 teacher eval
        t0 = time.time()
        t_q2_goal = False
        try:
            plan = q2.plan_with_llm_pddl(st, str(domain_path), llm_client)
            if plan:
                nplan = normalise(plan)
                env = BlocksworldEnv(task["blocks"])
                env.reset(task["initial_state"])
                env.execute_plan(nplan)
                t_q2_goal = env.is_goal_satisfied(task["goal_state"])
        except Exception:
            pass
        t_q2_time = round(time.time() - t0, 2)

        if t_q1_goal: q1_goal_t += 1
        if t_q2_goal: q2_goal_t += 1

        # 对比学生自测结果
        s_q1 = None
        s_q2 = None
        if student_res and "details" in student_res:
            for d in student_res["details"]:
                if d["task_id"] == tid:
                    if d["method"] == "q1": s_q1 = d["goal_success"]
                    if d["method"] == "q2": s_q2 = d["goal_success"]

        q1_ok = (s_q1 == t_q1_goal) if s_q1 is not None else "N/A"
        q2_ok = (s_q2 == t_q2_goal) if s_q2 is not None else "N/A"
        if q1_ok is True: q1_match += 1
        if q2_ok is True: q2_match += 1

        flag = ""
        if q1_ok is False: flag += " Q1不一致!"
        if q2_ok is False: flag += " Q2不一致!"

        print(f"{tid:<14} {'✓' if s_q1 else '✗':<10} {'✓' if t_q1_goal else '✗':<10} {'✓' if s_q2 else '✗':<10} {'✓' if t_q2_goal else '✗':<10} {flag}")

        verify_results.append({
            "task_id": tid,
            "q1_student": s_q1, "q1_teacher": t_q1_goal, "q1_match": q1_ok,
            "q2_student": s_q2, "q2_teacher": t_q2_goal, "q2_match": q2_ok,
        })

    n = len(tasks)
    report = {
        "student_file": args.submission,
        "q1_teacher_rate": f"{q1_goal_t}/{n}",
        "q2_teacher_rate": f"{q2_goal_t}/{n}",
        "q1_match_rate": f"{q1_match}/{n}",
        "q2_match_rate": f"{q2_match}/{n}",
        "verified": q1_match == n and q2_match == n,
        "details": verify_results,
    }

    print(f"\n{'='*50}")
    print(f"教师评测 Q1: {q1_goal_t}/{n}  Q2: {q2_goal_t}/{n}")
    print(f"结果一致性 Q1: {q1_match}/{n}  Q2: {q2_match}/{n}")
    print(f"{'✅ 全部一致' if report['verified'] else '⚠️ 存在不一致，需要核查'}")

    if not report["verified"]:
        print("\n⚠️ 不一致详情:")
        for r in verify_results:
            if r["q1_match"] is not True or r["q2_match"] is not True:
                print(f"  {r['task_id']}: Q1(学生={r['q1_student']},教师={r['q1_teacher']}) Q2(学生={r['q2_student']},教师={r['q2_teacher']})")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存: {args.output}")


if __name__ == "__main__":
    main()
