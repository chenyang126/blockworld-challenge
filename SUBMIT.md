# 提交说明

## 1. 运行自测

```bash
export OPENAI_API_KEY="你的key"
export LLM_PROVIDER="openai-compatible"     # 如果用 DeepSeek/Qwen 等
export LLM_BASE_URL="https://api.deepseek.com"
export LLM_MODEL="deepseek-chat"

python evaluate.py --output results.json
```

## 2. 提交内容

将以下内容打包为 `学号_姓名.zip`：

```
学号_姓名.zip
├── my_planner/
│   ├── q1_llm_prompt_planner.py      # Q1 实现
│   ├── q2_llm_pddl_planner.py        # Q2 实现
│   └── prompt_templates/
│       ├── q1_prompt.txt
│       └── q2_pddl_prompt.txt
├── results.json                       # evaluate.py 输出的结果
└── 实验报告.pdf                       # 实验报告
```

## 3. 注意

- `results.json` 必须由 `evaluate.py` 生成，不要手动编辑
- 教师会用相同的 LLM 后端重新评测以验证结果真实性
- 如发现硬编码答案或结果造假，按学术不端处理
