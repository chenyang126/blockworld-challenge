# Blocksworld 课程设计 — 学生开发指南

## 一、你要做什么

用大语言模型（LLM）完成 Blocksworld 积木世界规划任务，分两道题：

| 题目 | 方法 | 你写的代码 | 核心挑战 |
|:---:|------|------|------|
| **Q1** | 纯 LLM Prompt 规划 | `student/q1_llm_prompt_planner.py` | LLM 直接输出动作序列，Prompt 设计决定成败 |
| **Q2** | LLM + PDDL 规划器 | `student/q2_llm_pddl_planner.py` | LLM 生成 PDDL problem 文件，由规划器求解 |

两道题共用一个 Blocksworld 环境和 25 个任务（4 公开 + 21 隐藏），最终用教师提供的评测脚本统一打分。

---

## 二、环境速览

### 2.1 积木世界基本概念

```
 [A]          ← 积木 A
 [B]          ← 积木 B  
 [C]          ← 积木 C
-----         ← 桌面
table
```

**5 种谓词**描述状态：

| 谓词 | 含义 | 示例 |
|------|------|------|
| `ontable(x)` | x 在桌面上 | `ontable(A)` |
| `on(x,y)` | x 放在 y 上面 | `on(A,B)` |
| `clear(x)` | x 上面没有东西 | `clear(A)` |
| `holding(x)` | 机械手拿着 x | `holding(A)` |
| `handempty` | 机械手为空 | `handempty` |

**4 种动作**（你只能使用这些）：

| 动作 | 前提条件 | 效果 |
|------|----------|------|
| `PICKUP(x)` | x 在桌上 **且** x 上面没东西 **且** 手为空 | 手拿着 x |
| `PUTDOWN(x)` | 手拿着 x | x 放到桌上，手变空 |
| `UNSTACK(x,y)` | x 在 y 上 **且** x 上面没东西 **且** 手为空 | 手拿着 x，y 变空 |
| `STACK(x,y)` | 手拿着 x **且** y 上面没东西 | x 放到 y 上，手变空 |

### 2.2 你不可以做的事

- 不能写 BFS / DFS / A* 等搜索算法
- 不能根据 `task_id` 硬编码答案
- 不能修改 `env/`、`pddl/domain.pddl`、`evaluate.py`、`run_q*.py`
- Q1 不能调 PDDL 规划器
- Q2 不能改 `domain.pddl`（但必须调用 PDDL 规划器）

---

## 三、项目结构（你只需要关注 `student/`）

```
blockworld/
├── env/                          # 教师提供 — 不修改
├── pddl/domain.pddl              # 教师提供 — 不修改
├── tasks/                        # 教师提供 — 不修改
├── run_q1.py                     # 教师提供 — 用于单任务调试
├── run_q2.py                     # 教师提供 — 用于单任务调试
├── evaluate.py                   # 教师提供 — 用于批量评测
├── llm_client.py                 # 教师提供 — LLM API 封装
│
└── student/                      # ← 你只需要改这个目录
    ├── q1_llm_prompt_planner.py  # Q1 实现（3 个函数）
    ├── q2_llm_pddl_planner.py    # Q2 实现（4 个函数）
    └── prompt_templates/
        ├── q1_prompt.txt         # Q1 Prompt 草稿（可选）
        └── q2_pddl_prompt.txt    # Q2 Prompt 草稿（可选）
```

---

## 四、Q1 开发指南：纯 LLM Prompt 规划

### 4.1 你要实现的 3 个函数

```python
def build_prompt(task: dict) -> str:
    """输入任务字典，返回发给 LLM 的 Prompt 字符串"""

def parse_llm_output(response: str) -> list[str]:
    """输入 LLM 返回的文本，输出动作序列列表"""

def plan_with_llm(task: dict, llm_client) -> list[str]:
    """串联上面两步，返回动作序列"""
```

### 4.2 `task` 字典结构

```python
{
    "task_id": "task_02",
    "blocks": ["A", "B", "C"],
    "natural_language": "There are three blocks A, B, and C...",
    "initial_state": ["on(C,A)", "ontable(A)", ...],  # 可能为空 []
    "goal_state":    ["on(A,B)", "on(B,C)", ...],      # 可能为空 []
}
```

**重要**：对于一部分任务（隐藏测试），`initial_state` 和 `goal_state` 是空列表，你只能从 `natural_language` 中提取状态信息。你的 Prompt 需要处理这两种情况。

### 4.3 `llm_client` 用法

```python
response = llm_client.chat(prompt)  # 发送 Prompt，返回 LLM 文本
```

`llm_client` 是教师提供的 `LLMClient` 实例，你不需要关心它的实现细节，直接调 `.chat()` 即可。

### 4.4 Q1 开发步骤

**第 1 步**：让公开任务跑通

```bash
python run_q1.py --task tasks/public/task_01.json \
    --api-key <你的key> --provider openai-compatible \
    --base-url <API地址> --model <模型名>
```

公开任务提供了结构化状态，先确保基本流程正常工作：
- Prompt 能发给 LLM
- `parse_llm_output()` 能从 LLM 回复中正确提取动作
- 动作序列能在环境中通过

**第 2 步**：优化 Prompt

默认 Prompt 只告诉 LLM 动作名称，**没有解释前提条件**。这就是为什么它会犯错。你需要：

1. **说明每个动作的前提条件**（什么时候能用）
2. **给输出格式示例**（Few-shot：给一个正确的输入输出对）
3. **要求 LLM 内部逐步检查状态**，但不输出推理过程

**第 3 步**：处理 NL-only 任务

当 `initial_state` 和 `goal_state` 为空时，你的 Prompt 必须引导 LLM 从自然语言中自行提取状态。

### 4.5 Q1 常见失败原因

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| `Plan valid: False` | LLM 生成的动作不满足前提条件 | 在 Prompt 中详细说明前提条件，要求 LLM 逐步检查 |
| `plan` 为空列表 | `parse_llm_output` 解析失败 | 检查正则表达式是否匹配 LLM 的输出格式；LLM 可能输出 markdown 围栏或编号 |
| 目标未达成但计划有效 | LLM 生成的计划方向错了 | Prompt 中提供更清晰的目标状态描述 |
| NL-only 任务全挂 | Prompt 没有处理无结构化状态的情况 | 让 LLM 从 NL 自行提取状态再规划 |

---

## 五、Q2 开发指南：LLM + PDDL 规划器

### 5.1 整体流程

```
任务描述 → [你的 Prompt] → LLM 生成 problem.pddl → [PDDL 规划器] → 动作序列
```

Q2 的核心思想：**LLM 不直接输出动作，而是把问题翻译成 PDDL 格式，交给经典规划器求解**。规划器保证计划的正确性（前提是 problem.pddl 写对了）。

### 5.2 你要实现的 4 个函数

```python
def build_pddl_prompt(task: dict, domain_pddl: str) -> str:
    """输入任务 + domain.pddl 文本，返回让 LLM 生成 problem.pddl 的 Prompt"""

def generate_problem_pddl(task: dict, domain_pddl: str, llm_client) -> str:
    """调 LLM 生成 problem.pddl 文本，清洗输出（去 markdown 等）"""

def solve_pddl(domain_path: str, problem_path: str) -> list[str]:
    """调 PDDL 规划器（pyperplan）对 domain + problem 求解"""

def plan_with_llm_pddl(task: dict, domain_path: str, llm_client) -> list[str]:
    """串联全流程"""
```

### 5.3 PDDL 速成

**domain.pddl** 定义了积木世界的"规则"（教师提供，不修改）。**problem.pddl** 定义了一个具体的"题目"，你需要让 LLM 生成它。

一个合法的 problem.pddl 长这样：

```lisp
(define (problem task_02)
  (:domain blocksworld)
  (:objects A B C - block)
  (:init
    (on C A)
    (ontable A)
    (ontable B)
    (clear C)
    (clear B)
    (handempty)
  )
  (:goal (and
    (on A B)
    (on B C)
    (ontable C)
  ))
)
```

关键语法规则：
- 谓词用**空格**分隔参数：`(on A B)` ✅，不是 `(on A,B)` ❌
- 所有积木必须在 `:objects` 中声明
- `:goal` 用 `(and ...)` 包裹
- 域名必须是 `blocksworld`

### 5.4 调用 PDDL 规划器

```python
from pyperplan import planner
from pyperplan.search import breadth_first_search

plan = planner.search_plan(domain_path, problem_path, breadth_first_search, None)
# plan 是一个 Operator 对象列表
# str(op) → "(pickup d)\n  PRE: ..." → 取第一行 → "pickup d"
```

安装 pyperplan：`pip install pyperplan`

### 5.5 Q2 开发步骤

**第 1 步**：让公开任务跑通

```bash
python run_q2.py --task tasks/public/task_02.json \
    --api-key <你的key> --provider openai-compatible \
    --base-url <API地址> --model <模型名>
```

预期输出：
```
Planner plan:
  1. unstack c a
  2. putdown c
  ...
Plan valid: True
Goal achieved: True
```

先确保 LLM 生成的 problem.pddl 能被规划器正确解析和求解。

**第 2 步**：优化 PDDL Prompt

默认 Prompt 只给了 domain.pddl 的文本，**没有提供完整的 PDDL 示例**。你需要：

1. **在 Prompt 中给出一个正确的 problem.pddl 完整示例**（最有效）
2. 强调谓词语法：空格分隔参数，不是逗号
3. 提醒 LLM 检查 `:objects` 是否包含所有积木
4. 要求 LLM 不要输出 markdown 围栏

**第 3 步**：处理 NL-only 任务

当没有结构化状态时，你需要让 LLM：
1. 从自然语言中推断初始状态和目标状态
2. 将其翻译为 PDDL 谓词
3. 生成正确的 problem.pddl

这是 Q2 最困难的部分。在 Prompt 中提供一个 NL→PDDL 的转换示例很有帮助。

**第 4 步**：清洗 LLM 输出

LLM 不总是按你的要求输出纯净 PDDL。你需要在 `generate_problem_pddl()` 中处理：
- markdown 代码围栏（\`\`\`lisp ... \`\`\`）
- 多余的解释文字
- 输出不以 `(define` 开头时，尝试在文本中查找

### 5.6 Q2 常见失败原因

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| `PDDL planning failed` | LLM 生成了语法错误的 problem.pddl | 检查生成的 problem.pddl 文件（在 `outputs/` 下），修复 Prompt |
| planner 返回 "no plan found" | LLM 翻译的状态有逻辑错误（如 `on` 方向反了） | 在 Prompt 中强调 on(x,y) 的含义：x 在 y 上面 |
| NL-only 任务失败 | Prompt 没有教 LLM 如何处理纯 NL 输入 | 增加 NL→PDDL 的转换示例 |
| `:objects` 缺少积木 | LLM 漏声明了积木 | Prompt 中强调列出所有积木 |

---

## 六、LLM 配置

### 命令行参数（一次性）

```bash
python run_q1.py --task ... \
    --api-key <key> \
    --provider openai-compatible \
    --base-url <API地址> \
    --model <模型名>
```

### 环境变量（持久化，推荐）

```bash
export OPENAI_API_KEY="<你的key>"
export LLM_PROVIDER="openai-compatible"
export LLM_BASE_URL="<API地址>"
export LLM_MODEL="<模型名>"
```

支持的后端：`openai`（OpenAI 官方）、`anthropic`（Claude）、`openai-compatible`（DeepSeek / Qwen / 任何 OpenAI 兼容 API）。

### 注意

- 强模型（如 deepseek-v4-pro / gpt-4o / claude-opus）规划能力好，但费用高
- 弱模型（如 deepseek-chat / gpt-4o-mini）费用低，但对 Prompt 质量要求更高
- **最终评测可能使用与你调试时不同的模型**，因此 Prompt 的泛化性很重要

---

## 七、调试技巧

### 7.1 单任务调试

```bash
# Q1 调试 task_02
python run_q1.py --task tasks/public/task_02.json \
    --api-key <key> --provider openai-compatible \
    --base-url <API> --model <模型>

# Q2 调试 task_02
python run_q2.py --task tasks/public/task_02.json \
    --api-key <key> --provider openai-compatible \
    --base-url <API> --model <模型>
```

### 7.2 查看环境状态

`BlocksworldEnv.render()` 输出 ASCII 图：

```
arm: empty
 [A]
 [B]
 [C]
-----
table
```

### 7.3 Q2 检查生成的 PDDL

运行 Q2 后，生成的 `problem.pddl` 保存在 `outputs/<task_id>/problem.pddl`。打开检查 LLM 到底生成了什么。

### 7.4 打印 LLM 原始输出

在 `plan_with_llm()` 或 `plan_with_llm_pddl()` 中加一行：

```python
print("LLM raw response:", response[:500])  # 打印前 500 字符
```

### 7.5 批量自测

```bash
# 一次性测所有公开任务
python evaluate.py --method q1 --task_dir tasks/public \
    --api-key <key> --provider openai-compatible \
    --base-url <API> --model <模型>

python evaluate.py --method q2 --task_dir tasks/public \
    --api-key <key> --provider openai-compatible \
    --base-url <API> --model <模型>
```

---

## 八、评分标准（100 分）

| 模块 | 分值 | 考察什么 |
|------|:---:|------|
| Q1 Prompt 规划 | 25 | Prompt 设计质量、动作序列正确性、公开+隐藏任务通过率 |
| Q2 LLM+PDDL | 30 | PDDL 生成正确性、规划器调用、NL-only 任务表现 |
| 接口规范 | 15 | 函数签名正确、不修改教师代码、不硬编码 |
| 实验分析 | 20 | Q1 vs Q2 对比深度、失败案例诊断、错误统计 |
| 报告质量 | 10 | 结构清晰、表达规范、图表完整 |

---

## 九、提交清单

```
student/
├── q1_llm_prompt_planner.py      # Q1 实现
├── q2_llm_pddl_planner.py        # Q2 实现
└── prompt_templates/
    ├── q1_prompt.txt             # Q1 Prompt 模板（可选）
    └── q2_pddl_prompt.txt        # Q2 Prompt 模板（可选）

实验报告.pdf                        # 实验报告
```

### 报告内容建议

1. **实验目标**：你要解决什么问题
2. **Blocksworld 环境说明**：动作空间、状态表示
3. **Q1 方法**：Prompt 设计思路、关键决策、Prompt 文本
4. **Q2 方法**：PDDL 生成策略、规划器选择、Prompt 文本
5. **实验结果**：25 个任务在两个方法上的通过情况表格
6. **失败案例分析**：挑 2-3 个典型失败任务，分析原因
7. **两种方法对比**：成功率、步数、错误类型、适用场景
8. **总结**：收获与反思

---

## 十、FAQ

**Q: 我可以用 ChatGPT 网页版调试 Prompt 吗？**

可以，但最终代码必须调用 API（通过 `llm_client.chat()`）。注意不同 LLM 行为可能不同，建议在目标模型上测试。

**Q: Q1 和 Q2 哪个更重要？**

Q1 考察 Prompt 工程能力（25 分），Q2 考察 LLM + 符号方法结合能力（30 分）。Q2 通常会比 Q1 更稳定（因为规划器保证正确性），你需要在报告中分析这个差异。

**Q: NL-only 任务占多少比例？**

25 个任务中，4 个公开任务提供结构化状态，21 个隐藏任务是 NL-only。你的 Prompt 必须能够处理两种输入。

**Q: 我能让 LLM 在 Prompt 里做链式思考（Chain-of-Thought）吗？**

可以，但要确保最终输出只包含动作序列（Q1）或 PDDL 文件（Q2）。如果 LLM 输出混入了推理文本，你的 `parse_llm_output` / `generate_problem_pddl` 必须能过滤掉。
