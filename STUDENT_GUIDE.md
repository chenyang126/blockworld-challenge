# Blocksworld 学生指南

用大语言模型（LLM）让积木按要求堆好。你只写 **Prompt 和少量胶水代码**，不用自己实现环境，也不用写搜索算法。

| 题目 | 做法 | 你要改的文件 |
|:---:|------|------|
| **Q1** | 让 LLM 直接输出动作序列 | `my_planner/q1_llm_prompt_planner.py` |
| **Q2** | 让 LLM 生成 PDDL 文件，再交给规划器求解 | `my_planner/q2_llm_pddl_planner.py` |

两题共用同一套环境和 25 个任务（4 个公开 + 21 个隐藏），最后用 `evaluate.py` 统一打分。

---

## 1. 积木世界长什么样

```
 [A]      A 在最上面
 [B]
 [C]
-----     桌面
```

**5 个谓词**描述状态：

| 谓词 | 含义 |
|------|------|
| `ontable(A)` | A 在桌上 |
| `on(A,B)` | A 摞在 B 上 |
| `clear(A)` | A 顶上没东西 |
| `holding(A)` | 手正拿着 A |
| `handempty` | 手是空的 |

**只有 4 个动作**：

| 动作 | 什么时候能用 |
|------|------|
| `PICKUP(x)` | x 在桌上、顶上没东西、手是空的 |
| `PUTDOWN(x)` | 手正拿着 x |
| `UNSTACK(x,y)` | x 摞在 y 上、x 顶上没东西、手是空的 |
| `STACK(x,y)` | 手拿着 x、y 顶上没东西 |

> 动作必须满足"什么时候能用"才合法。LLM 最常犯的错就是用了不满足条件的动作 —— 这正是你要在 Prompt 里解决的。

**规则**：不能写 BFS/DFS/A\* 搜索，不能按 `task_id` 硬编码答案，不能改 `env/`、`pddl/`、`tasks/`、`run_*.py`、`evaluate.py`。

---

## 2. 在哪写代码

只动 `my_planner/` 这一个目录：

```
student/
├── my_planner/
│   ├── q1_llm_prompt_planner.py   ← Q1，填 3 个函数
│   ├── q2_llm_pddl_planner.py     ← Q2，填 4 个函数
│   └── prompt_templates/          ← Prompt 草稿（可选）
├── run_q1.py / run_q2.py          教师提供，调试单个任务用
├── evaluate.py                    教师提供，一键自测全部任务
└── tasks/                         25 个任务
```

每个任务以字典形式传给你：

```python
{
    "blocks": ["A", "B", "C"],
    "natural_language": "把 A 放到 B 上……",   # 所有任务都有
    "initial_state": ["on(C,A)", ...],         # 隐藏任务里是空列表 []
    "goal_state":    ["on(A,B)", ...],         # 隐藏任务里是空列表 []
}
```

> ⚠️ 21 个隐藏任务的 `initial_state`/`goal_state` 是空的，只能从 `natural_language` 里读出状态。**你的 Prompt 必须同时应付"有结构化状态"和"只有自然语言"两种情况。**

---

## 3. Q1：让 LLM 直接输出动作

填这 3 个函数（签名已给好，别改）：

```python
def build_prompt(task) -> str:          # 拼出发给 LLM 的 Prompt
def parse_llm_output(response) -> list:  # 从 LLM 回复里抽出动作序列
def plan_with_llm(task, llm_client):     # 串起来：build → llm_client.chat() → parse
```

调用 LLM 只需一行：`response = llm_client.chat(prompt)`。

**写好 Prompt 的关键**：
1. 把每个动作的"什么时候能用"写进 Prompt（默认模板没写，所以 LLM 会乱用）。
2. 给一个"输入 → 正确输出"的示例（few-shot）。
3. 要求 LLM 一行一个动作，**只输出动作**，不要解释、不要 markdown。
4. 允许 LLM 内部一步步检查，但别把推理过程打印出来。

---

## 4. Q2：让 LLM 写 PDDL，规划器来解

```
任务 →【你的 Prompt】→ LLM 生成 problem.pddl →【规划器】→ 动作序列
```

LLM 不直接想答案，只负责把题目"翻译"成 PDDL；正确性交给规划器保证。填这 4 个函数：

```python
def build_pddl_prompt(task, domain_pddl) -> str:        # 让 LLM 生成 problem.pddl 的 Prompt
def generate_problem_pddl(task, domain_pddl, llm_client): # 调 LLM 并清洗输出
def solve_pddl(domain_path, problem_path) -> list:       # 用 pyperplan 求解
def plan_with_llm_pddl(task, domain_path, llm_client):    # 串起全流程
```

一个合法的 `problem.pddl`：

```lisp
(define (problem task_02)
  (:domain blocksworld)
  (:objects A B C - block)
  (:init (on C A) (ontable A) (ontable B) (clear C) (clear B) (handempty))
  (:goal (and (on A B) (on B C) (ontable C))))
```

注意：参数用**空格**分隔（`(on A B)` ✅，`(on A,B)` ❌）；所有积木都要写进 `:objects`；域名固定 `blocksworld`。

调用规划器（先 `pip install pyperplan`）：

```python
from pyperplan import planner
from pyperplan.search import breadth_first_search
plan = planner.search_plan(domain_path, problem_path, breadth_first_search, None)
# 每个元素 str() 后取第一行，如 "pickup d"
```

---

## 5. 怎么跑（建议先配环境变量）

```bash
export OPENAI_API_KEY="你的key"
export LLM_PROVIDER="openai-compatible"   # openai / anthropic / openai-compatible
export LLM_BASE_URL="https://api.deepseek.com"
export LLM_MODEL="deepseek-chat"
```

在 `student/` 目录下：

```bash
# 调试单个任务（看清楚某题哪里错）
python run_q1.py --task tasks/public/task_01.json
python run_q2.py --task tasks/public/task_02.json

# 一键自测全部 25 个任务，生成 results.json（提交用）
python evaluate.py --output results.json
```

**开发节奏**：先用公开任务（`tasks/public/`）跑通基本流程 → 改 Prompt 提高通过率 → 最后攻克隐藏任务那种"只有自然语言"的情况。

> 最终评分可能换一个模型，所以 Prompt 不要只针对一个模型调，要通用。

---

## 6. 卡住了？对照常见原因

| 现象 | 多半是因为 | 怎么办 |
|------|------|------|
| `Plan valid: False` | LLM 用了不满足条件的动作 | Prompt 里写清前提条件，要求逐步自检 |
| `plan` 是空列表 | `parse_llm_output` 没解析出来 | LLM 可能裹了 markdown/编号，调整解析逻辑 |
| 计划有效但目标没达成 | LLM 方向搞反了 | Prompt 里把目标状态讲清楚 |
| Q2 `planning failed` | 生成的 PDDL 语法错 | 打开 `outputs/<task>/problem.pddl` 看 LLM 到底写了啥 |
| Q2 `no plan found` | 状态翻译有逻辑错（常见 `on` 反了） | 强调 `on(x,y)` = x 在 y 上面 |
| 隐藏任务全挂 | Prompt 没处理"只有自然语言" | 加一个 自然语言 → 谓词/PDDL 的示例 |

**调试小技巧**：在 `plan_with_llm` / `plan_with_llm_pddl` 里加 `print(response[:500])` 看 LLM 原始输出；Q2 生成的 PDDL 在 `outputs/` 下可直接打开检查。

---

## 7. 提交

打包细节见 **[SUBMIT.md](SUBMIT.md)**。简单说要交：`my_planner/`（两个 .py + prompt 模板）、`evaluate.py` 跑出的 `results.json`、以及 `实验报告.pdf`。

报告建议包含：方法思路（Q1/Q2 各自的 Prompt 设计）、25 个任务的结果表、2–3 个失败案例分析、Q1 vs Q2 对比、总结。

| 评分模块 | 分值 |
|------|:---:|
| Q1 Prompt 规划 | 25 |
| Q2 LLM+PDDL | 30 |
| 接口规范（不改教师代码、不硬编码） | 15 |
| 实验分析（对比 + 失败诊断） | 20 |
| 报告质量 | 10 |

---

## 8. 常见问题

**能用网页版 ChatGPT 调 Prompt 吗？** 可以，但最终代码必须走 `llm_client.chat()`，且最好在目标模型上验证。

**Q1 和 Q2 哪个更稳？** 通常 Q2 更稳，因为规划器保证正确性；Q1 全靠 Prompt。报告里要分析这个差异。

**能让 LLM 做思维链（CoT）吗？** 可以，但要保证最终只输出动作（Q1）或纯 PDDL（Q2），其余文字你的解析函数要能过滤掉。
