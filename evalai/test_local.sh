#!/bin/bash
# ── 本地模拟 EvalAI 评测流程 ────────────────────────────────────────
# 用法: bash evalai/test_local.sh <学生提交目录>
#
# 学生提交目录中应包含:
#   q1_llm_prompt_planner.py
#   q2_llm_pddl_planner.py
#
# 此脚本模拟 EvalAI 评测环境:
#   1. 复制学生代码到当前目录
#   2. 运行 evalai/evaluate.py
#   3. 恢复原始学生文件
#
# 环境变量:
#   LLM_API_KEY    - LLM API Key（必需）
#   LLM_PROVIDER   - 默认 openai-compatible
#   LLM_BASE_URL   - API 地址
#   LLM_MODEL      - 模型名称

set -e

SUBMISSION_DIR="${1:-}"
if [ -z "$SUBMISSION_DIR" ]; then
    echo "用法: bash evalai/test_local.sh <学生提交目录>"
    echo "示例: bash evalai/test_local.sh /path/to/student_submission/"
    exit 1
fi

if [ ! -f "$SUBMISSION_DIR/q1_llm_prompt_planner.py" ]; then
    echo "[ERROR] 未找到 $SUBMISSION_DIR/q1_llm_prompt_planner.py"
    exit 1
fi

if [ -z "$LLM_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "[ERROR] 请设置 LLM_API_KEY 或 OPENAI_API_KEY 环境变量"
    exit 1
fi

echo "============================================================"
echo " EvalAI 本地评测模拟"
echo "============================================================"
echo " 提交目录: $SUBMISSION_DIR"
echo " LLM: ${LLM_PROVIDER:-openai-compatible} / ${LLM_MODEL:-default}"
echo "============================================================"

# 备份当前 student 代码
cp student/q1_llm_prompt_planner.py student/q1_llm_prompt_planner.py.bak 2>/dev/null || true
cp student/q2_llm_pddl_planner.py student/q2_llm_pddl_planner.py.bak 2>/dev/null || true

# 复制学生提交到项目根目录（模拟 EvalAI 的 cwd）
cp "$SUBMISSION_DIR/q1_llm_prompt_planner.py" ./q1_llm_prompt_planner.py
cp "$SUBMISSION_DIR/q2_llm_pddl_planner.py" ./q2_llm_pddl_planner.py

# 运行评测
echo ""
echo "运行评测中..."
python evalai/evaluate.py

# 恢复原始文件
mv student/q1_llm_prompt_planner.py.bak student/q1_llm_prompt_planner.py 2>/dev/null || true
mv student/q2_llm_pddl_planner.py.bak student/q2_llm_pddl_planner.py 2>/dev/null || true
rm -f ./q1_llm_prompt_planner.py ./q2_llm_pddl_planner.py

echo ""
echo "评测完成。恢复原始 student/ 文件。"
