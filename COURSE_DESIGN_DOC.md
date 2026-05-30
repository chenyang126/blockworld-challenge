# Blocksworld 课程设计文档

> 基于大语言模型的 Blocksworld 任务规划实验 —— 教师端与学生端完整说明

---

## 一、项目概述

本课程设计由教师提供完整的 Blocksworld 任务规划环境，学生在同一环境上完成两个规划任务：

| 题目 | 名称 | 核心技术 |
|:---:|------|----------|
| **Q1** | 纯 LLM Prompt 规划 | LLM 直接输出动作序列 |
| **Q2** | LLM + PDDL 规划 | LLM 生成 PDDL problem → 经典规划器求解 |

两个任务生成的动作序列均在教师提供的 Blocksworld 环境中验证。学生不实现环境、不写搜索算法，核心工作是 **Prompt 设计**与**LLM 输出处理**。

---

## 二、目录结构

```
blockworld/
│
├── env/                              # [教师维护] 环境层，学生不可修改
│   ├── __init__.py                   # 包导出
│   ├── blocksworld_env.py            # 核心环境类 BlocksworldEnv
│   ├── action_parser.py              # 动作格式解析与校验
│   └── validator.py                  # 前提条件验证 + 动作效果
│
├── pddl/
│   └── domain.pddl                   # [教师维护] 固定 PDDL 域文件
│
├── tasks/                            # [教师维护] 任务集
│   ├── public/                       # 4 个公开任务（结构化状态，教学用）
│   ├── hidden/                       # 3 个隐藏测试（NL-only）
│   ├── hard/                         # 3 个困难测试（NL-only）
│   ├── extreme/                      # 10 个极限测试（NL-only）
│   └── nl_only/                      # 5 个纯自然语言测试（NL-only）
│
├── student/                          # [学生完成] 学生提交目录
│   ├── q1_llm_prompt_planner.py      # Q1 Planner（3 个函数）
│   ├── q2_llm_pddl_planner.py        # Q2 Planner（4 个函数）
│   └── prompt_templates/
│       ├── q1_prompt.txt             # Q1 Prompt 模板
│       └── q2_pddl_prompt.txt        # Q2 PDDL Prompt 模板
│
├── reference/                        # [教师参考] 参考实现（发布时删除）
│   ├── q1_llm_prompt_planner.py      # Q1 强 Prompt 参考
│   ├── q2_llm_pddl_planner.py        # Q2 强 Prompt 参考
│   ├── weak_q1.py                    # Q1 弱 Prompt 参考（用于测试）
│   └── weak_q2.py                    # Q2 弱 Prompt 参考（用于测试）
│
├── llm_client.py                     # [教师维护] LLM API 客户端
├── run_q1.py                         # [教师维护] Q1 单任务运行器
├── run_q2.py                         # [教师维护] Q2 单任务运行器
├── evaluate.py                       # [教师维护] 批量评测器
├── test_env.py                       # [教师工具] 环境正确性验证（无需 LLM）
├── outputs/                          # [运行时生成] 生成的 problem.pddl 等
└── readme.md                         # 课程设计说明书
```

---

## 三、教师端功能详解

### 3.1 环境层 `env/`

教师需要维护但**不需要频繁修改**的模块。

#### `blocksworld_env.py` — 核心环境

```
class BlocksworldEnv:
    def __init__(self, blocks: List[str])    # 初始化：传入积木名列表
    def reset(self, initial_state)           # 重置：设置初始状态谓词集
    def step(self, action) -> Dict           # 单步执行一个动作
    def execute_plan(self, plan) -> Dict     # 批量执行动作序列
    def is_goal_satisfied(self, goal) -> bool # 判断目标是否达成
    def render(self) -> str                  # ASCII 可视化当前积木排列
```

**状态表示**：`Set[str]`，谓词格式如 `"on(C,B)"`、`"ontable(A)"`、`"clear(A)"`、`"holding(A)"`、`"handempty"`。

**4 个动作**及前提条件：

| 动作 | 前提条件 | 效果 |
|------|----------|------|
| `PICKUP(x)` | ontable(x), clear(x), handempty | holding(x) |
| `PUTDOWN(x)` | holding(x) | ontable(x), clear(x), handempty |
| `UNSTACK(x,y)` | on(x,y), clear(x), handempty | holding(x), clear(y) |
| `STACK(x,y)` | holding(x), clear(y) | on(x,y), clear(x), handempty |

#### `action_parser.py` — 动作解析

```python
parse_action(action: str) -> Optional[Tuple[str, List[str]]]
validate_action_format(action: str) -> bool
```

正则解析 `PICKUP(A)` / `UNSTACK(C,A)` 等格式，校验动作名和参数数量。

#### `validator.py` — 验证器

```python
validate_step(state, blocks, action_name, args) -> (bool, str)
get_action_preconditions(action_name, args) -> Set[str]
get_action_effects(action_name, args) -> (Set[str], Set[str])
```

检查动作是否满足前提条件、施加效果后的状态变化。

---

### 3.2 PDDL 域文件 `pddl/domain.pddl`

固定的 Blocksworld 域定义，使用 `:strips :typing`，包含 5 个谓词（`on`、`ontable`、`clear`、`holding`、`handempty`）和 4 个动作。学生不可修改此文件。

**教师注意事项**：务必与学生发布的版本一致。如果修改 domain.pddl，所有 reference plan 需要重新生成。

---

### 3.3 LLM 客户端 `llm_client.py`

统一封装三种 LLM 后端：

| Provider | 模型示例 | 环境变量 |
|----------|---------|----------|
| `openai` | gpt-4o | `OPENAI_API_KEY` |
| `anthropic` | claude-sonnet-4-6 | `ANTHROPIC_API_KEY` |
| `openai-compatible` | deepseek-chat / v4-pro | `OPENAI_API_KEY` + `LLM_BASE_URL` |

学生可以通过命令行参数 `--provider`、`--model`、`--api-key`、`--base-url` 配置，也可以通过环境变量 `LLM_PROVIDER`、`LLM_MODEL` 等配置。学生无需修改此文件。

---

### 3.4 运行脚本

#### `run_q1.py` — 单任务运行器（Q1）

```bash
python run_q1.py --task tasks/public/task_02.json \
    --api-key sk-xxx --provider openai-compatible \
    --base-url https://api.deepseek.com --model deepseek-chat
```

流程：加载任务 → 创建 `LLMClient` → 导入 `student.q1_llm_prompt_planner.plan_with_llm()` → 调学生 Planner → `BlocksworldEnv.execute_plan()` → `is_goal_satisfied()` → 输出结果。

**NL-only 处理**：当任务 JSON 中包含 `"nl_only": true` 时，脚本会将 `initial_state` 和 `goal_state` 设空再传给学生的 `plan_with_llm()`，但环境验证仍使用原始结构化状态。

#### `run_q2.py` — 单任务运行器（Q2）

```bash
python run_q2.py --task tasks/public/task_02.json \
    --api-key sk-xxx --provider openai-compatible \
    --base-url https://api.deepseek.com --model deepseek-chat
```

流程类似，额外读取 `domain.pddl` 传入学生 Planner。Q2 还包含动作格式规范化——PDDL 规划器输出小写格式（如 `"unstack c a"`），脚本自动转换为大写格式（`"UNSTACK(C,A)"`）。

**NL-only 处理**：与 run_q1.py 一致。

#### `evaluate.py` — 批量评测器

```bash
python evaluate.py --method q1 --task_dir tasks/public \
    --api-key sk-xxx --provider openai-compatible \
    --base-url https://api.deepseek.com --model deepseek-chat
python evaluate.py --method q2 --task_dir tasks/hidden
```

按目录批量运行所有任务，输出汇总表格：

```
======================================================================
EVALUATION SUMMARY
======================================================================
Task ID      Valid    Goal     Steps    Time(s)    Error
----------------------------------------------------------------------
task_01      ✓        ✓        2        1.05
task_02      ✓        ✓        6        16.66
...
======================================================================
Total tasks:        4
Plan valid:         4/4  (100%)
Goal achieved:      4/4  (100%)
======================================================================
```

支持 `--output results.json` 将详细结果导出 JSON。

**NL-only 处理**：`make_student_task()` 函数对 `nl_only: true` 的任务剥离结构化状态，学生只拿到自然语言描述。

---

### 3.5 任务文件格式

#### 标准任务（公开任务）

```json
{
  "task_id": "task_02",
  "blocks": ["A", "B", "C"],
  "natural_language": "There are three blocks A, B, and C...",
  "initial_state": ["on(C,A)", "ontable(A)", "ontable(B)", "clear(C)", "clear(B)", "handempty"],
  "goal_state": ["on(A,B)", "on(B,C)", "ontable(C)"]
}
```

#### NL-only 任务（隐藏/困难/极限任务）

```json
{
  "task_id": "task_08",
  "blocks": ["A", "B", "C", "D", "E", "F"],
  "nl_only": true,
  "natural_language": "Six blocks arranged as two separate towers. The left tower...",
  "initial_state": ["on(C,B)", "on(B,A)", "ontable(A)", "clear(C)", ...],
  "goal_state": ["on(E,C)", "on(C,A)", "ontable(A)", ...]
}
```

`initial_state` 和 `goal_state` **仅用于环境验证**，当 `nl_only: true` 时不会传给学生的 Planner 函数。学生只能从 `natural_language` 字段中提取状态信息。

---

### 3.6 教师工具

#### `test_env.py` — 环境正确性测试

```bash
python test_env.py
```

无需 LLM API key，用预定义的 reference plans 验证所有 25 个任务在环境中均可正确执行。**修改任何任务或环境代码后都应运行此测试**。

输出示例：
```
============================================================
Blocksworld Environment Smoke Test
============================================================
  [task_01] OK — 2 steps, goal satisfied
  [task_02] OK — 6 steps, goal satisfied
  ...
============================================================
Results: 25 passed, 0 failed out of 25
============================================================
```

Reference plans 定义在 `test_env.py` 的 `REFERENCE_PLANS` 字典中。**新增任务时必须同步更新此字典**。

---

## 四、任务体系设计

### 4.1 任务分层

| 层级 | 目录 | 数量 | 类型 | 积木数 | 步数范围 | 用途 |
|------|------|:---:|------|:---:|:---:|------|
| **Public** | `tasks/public/` | 4 | 结构化状态 | 2-4 | 2-8 | 学生学习 & 调试 |
| **Hidden** | `tasks/hidden/` | 3 | NL-only | 4-5 | 4-10 | 隐藏测试 |
| **Hard** | `tasks/hard/` | 3 | NL-only | 6-7 | 8-16 | 困难测试 |
| **Extreme** | `tasks/extreme/` | 10 | NL-only | 5-9 | 2-26 | 极限测试 |
| **NL-only** | `tasks/nl_only/` | 5 | NL-only | 3-7 | 4-18 | 纯自然语言测试 |

**设计理念**：
- 公开任务给学生用于 Prompt 开发调试，提供结构化状态
- 隐藏/困难/极限任务全部 NL-only，学生无法通过结构化状态投机取巧
- NL-only 任务测试学生 Prompt 的 NL→谓词翻译能力，这是真正的区分点

### 4.2 25 个任务详细清单

| # | ID | 积木 | 最优步数 | 关键难点 |
|---|-----|:---:|:---:|------|
| 1 | task_01 | 2 | 2 | 入门：单步堆叠 |
| 2 | task_02 | 3 | 6 | 入门：三块重排 |
| 3 | task_03 | 4 | 8 | 塔反转 |
| 4 | task_04 | 4 | 6 | 干扰物 D 不移动 |
| 5 | task_05 | 5 | 8 | NL：五块建高塔 |
| 6 | task_06 | 4 | 10 | NL：复杂重组 |
| 7 | task_07 | 5 | 4 | NL：前提条件陷阱（B 在 C 上，先 UNSTACK 才能 STACK） |
| 8 | task_08 | 6 | 16 | NL：两塔互换 |
| 9 | task_09 | 6 | 8 | NL：干扰物+塔反转 |
| 10 | task_10 | 7 | 18 | NL：三塔合并 |
| 11 | task_11 | 5 | 10 | NL：跨塔重组 |
| 12 | task_12 | 6 | 16 | NL：两独立塔顶部互换 |
| 13 | task_13 | 7 | 8 | NL：最小变动（已有塔不动） |
| 14 | task_14 | 7 | 12 | NL：塔反转+建新塔 |
| 15 | task_15 | 8 | 16 | NL：8 块塔完全反转 |
| 16 | task_16 | 7 | 12 | NL：三塔变两塔 |
| 17 | task_17 | 7 | 18 | NL：完全打散重排 |
| 18 | task_18 | 7 | 2 | NL：过度移动陷阱（只加一块） |
| 19 | task_19 | 8 | 16 | NL：两座四塔同时反转 |
| 20 | task_20 | 9 | 22 | NL：九块终极挑战 |
| NL1 | nl_task_01 | 3 | 4 | NL：代词+隐含状态 |
| NL2 | nl_task_02 | 4 | 6 | NL：叙事风格+不扰动物 |
| NL3 | nl_task_03 | 5 | 10 | NL：从下往上读+方向容易反 |
| NL4 | nl_task_04 | 6 | 14 | NL：左右塔描述+串到一起 |
| NL5 | nl_task_05 | 7 | 18 | NL：三堆变两堆+重新分配 |

### 4.3 预期区分度

基于评测数据（deepseek-chat 模拟弱模型，deepseek-v4-pro 模拟强模型）：

| 组合 | Q1 通过率 | Q2 通过率 | 画像 |
|------|:---:|:---:|------|
| 弱模型 + 好 Prompt | ~28% | ~64% | **核心目标**：Q2 > Q1 差异显著 |
| 强模型 + 弱 Prompt | ~32% | ~16% | 强模型无法靠蛮力通关 |
| 强模型 + 好 Prompt | ~100% | ~100% | 极限情况，通过报告分析拉开 |

**核心教学结论**（学生报告中应呈现）：LLM + PDDL 规划器（Q2）在正确 Prompt 下远优于纯 LLM（Q1），这证明了符号规划器在可靠性上的优势。

---

## 五、学生端功能说明

### 5.1 学生需要完成的 4 个文件

| 文件 | 内容 | 说明 |
|------|------|------|
| `student/q1_llm_prompt_planner.py` | Q1 规划器实现（3 个函数） | 核心文件 |
| `student/q2_llm_pddl_planner.py` | Q2 规划器实现（4 个函数） | 核心文件 |
| `student/prompt_templates/q1_prompt.txt` | Q1 Prompt 文本模板 | 辅助，可被代码引用 |
| `student/prompt_templates/q2_pddl_prompt.txt` | Q2 Prompt 文本模板 | 辅助，可被代码引用 |

### 5.2 Q1 接口规范 `q1_llm_prompt_planner.py`

```python
def build_prompt(task: dict) -> str:
    """
    输入：task = {
        "task_id": str,
        "blocks": ["A", "B", "C"],
        "natural_language": "...",      # 对所有任务都有
        "initial_state": ["on(C,A)", ...],  # NL-only 任务中为空列表 []
        "goal_state": ["on(A,B)", ...]      # NL-only 任务中为空列表 []
    }
    输出：发给 LLM 的完整 Prompt 字符串
    """

def parse_llm_output(response: str) -> list[str]:
    """
    输入：LLM 返回的原始文本
    输出：动作序列列表，如 ["UNSTACK(C,A)", "PUTDOWN(C)", ...]
    需要处理：markdown 代码块、行号、多余文字等噪音
    """

def plan_with_llm(task: dict, llm_client) -> list[str]:
    """
    完整流程：build_prompt → llm_client.chat() → parse_llm_output
    llm_client 有一个 .chat(prompt: str) -> str 方法
    """
```

**限制**：
- 不能调用 PDDL 规划器
- 不能写 BFS / DFS / A* 等搜索算法
- 不能根据 task_id 硬编码答案
- 可以对 LLM 要求固定输出格式
- 可以让 LLM 在 Prompt 中自检前提条件（但不输出推理过程）

### 5.3 Q2 接口规范 `q2_llm_pddl_planner.py`

```python
def build_pddl_prompt(task: dict, domain_pddl: str) -> str:
    """
    输入：task（同 Q1）+ domain.pddl 的文本内容
    输出：让 LLM 生成 problem.pddl 的 Prompt
    """

def generate_problem_pddl(task: dict, domain_pddl: str, llm_client) -> str:
    """
    调用 LLM 生成 problem.pddl 文本
    需要清理 LLM 输出：去除 markdown fence、验证语法等
    """

def solve_pddl(domain_path: str, problem_path: str) -> list[str]:
    """
    调用 PDDL 规划器求解
    推荐：pyperplan（纯 Python，pip install pyperplan）
    备选：fast-downward
    pyperplan API: planner.search_plan(domain_path, problem_path, breadth_first_search, None)
    返回：动作列表，如 ["pickup d", "stack d e", ...]
    """

def plan_with_llm_pddl(task: dict, domain_path: str, llm_client) -> list[str]:
    """
    完整流程：
    1. 读取 domain.pddl
    2. build_pddl_prompt → llm_client.chat() → 清洗 → 得到 problem.pddl
    3. 保存 problem.pddl 到临时文件
    4. solve_pddl() 调规划器
    5. 返回动作序列
    """
```

**限制**：
- domain.pddl 由教师提供，不可修改
- 学生只需让 LLM 生成 problem.pddl
- 必须调用 PDDL 规划器（Q2 的核心是用规划器而非 LLM 求解）
- 不允许根据 task_id 硬编码 problem 文件或动作序列

**NL-only 挑战**：当 task 中 `initial_state` 和 `goal_state` 为空时，学生需要让 LLM 从 `natural_language` 中提取状态并翻译成 PDDL 谓词。这是 Q2 的真正难点。

### 5.4 Prompt 模板文件

`prompt_templates/q1_prompt.txt` 和 `prompt_templates/q2_pddl_prompt.txt` 是学生的 Prompt 草稿文件。可在代码中通过 `open()` 读取，也可以直接在 `build_prompt()` 函数中内联。**不作为评分强制项**，但有助于学生组织 Prompt 结构。

### 5.5 其他学生提交内容

除代码外，学生还需提交**实验报告**（PDF），包括：
1. 实验目标
2. Blocksworld 环境说明
3. Q1 纯 LLM Prompt 规划方法（Prompt 设计思路 + 关键决策）
4. Q2 LLM+PDDL 规划方法（Prompt 设计 + 规划器选择 + 流程说明）
5. 实验结果（25 个任务的对比表格）
6. 失败案例分析
7. Q1 vs Q2 两种方法对比
8. 总结与反思

---

## 六、评分标准（100 分）

| 模块 | 分值 | 评分要点 |
|------|:---:|------|
| Q1 Prompt 规划 | 25 | LLM 调用正常、输出格式规范、公开任务通过、Prompt 设计质量 |
| Q2 LLM+PDDL | 30 | PDDL problem 生成正确、规划器调用成功、NL-only 任务表现 |
| 接口规范 | 15 | 函数签名正确、不修改环境/评测器、不硬编码答案 |
| 实验分析 | 20 | Q1/Q2 对比分析深度、失败案例诊断、错误类型统计 |
| 报告质量 | 10 | 结构清晰、表达规范、图表完整、有总结反思 |

---

## 七、常见问题与注意事项

### 7.1 教师发布前检查清单

- [ ] 删除 `reference/` 目录（参考实现不应给学生）
- [ ] 删除 `.claude/` 目录
- [ ] 删除 `outputs/` 目录中的文件
- [ ] 删除 `__pycache__/` 目录
- [ ] 确认 `student/q1_llm_prompt_planner.py` 和 `student/q2_llm_pddl_planner.py` 是空壳（只有函数签名和 TODO 注释）
- [ ] 运行 `python test_env.py` 验证所有任务
- [ ] 确认 `readme.md` 是面向学生的说明书
- [ ] 确认 `COURSE_DESIGN_DOC.md`（本文档）不发给学生

### 7.2 学生环境配置

学生需要安装的 Python 包：
```bash
pip install openai         # LLM API 调用
pip install pyperplan      # PDDL 规划器（Q2 必需）
```

可选安装：
```bash
pip install anthropic      # 如果用 Anthropic Claude
```

### 7.3 新增任务指南

1. 在对应目录创建 `task_XX.json` 文件
2. 在 `test_env.py` 的 `REFERENCE_PLANS` 中添加验证用参考计划
3. 在 `test_env.py` 的 `main()` 中确保新目录被扫描
4. 运行 `python test_env.py` 验证
5. 如果是 NL-only 任务，确保 `"nl_only": true` 且 NL 描述包含所有必要信息

### 7.4 NL-only 设计原则

- **不直接给出谓词**：使用自然语言描述空间关系
- **隐含 handempty**：用 "机械手空闲"、"手没拿东西" 等表述
- **隐含 clear**：用 "顶部暴露"、"上面没东西"、"可以抓取" 等表述
- **包含干扰信息**：叙事风格中加入无关细节
- **用代词**："它"、"那个"、"其上面" — 测试 LLM 的指代消解
- **但不要歧义**：最终必须能唯一确定初始状态和目标状态

### 7.5 API 限制说明

如果学生使用学校统一提供的 API（共享 key），需注意并发限制和速率限制。建议在 `evaluate.py` 的批量评测中加入可选的 `--delay` 参数控制请求间隔。

---

## 八、教师需要维护的代码清单

| 文件 | 修改频率 | 修改场景 |
|------|:---:|------|
| `env/blocksworld_env.py` | 低 | 修复 bug、增加渲染功能等 |
| `env/action_parser.py` | 低 | 扩展动作格式支持 |
| `env/validator.py` | 低 | 修改前提条件逻辑 |
| `pddl/domain.pddl` | **极低** | 除非域定义有误，否则不动 |
| `llm_client.py` | 低 | 新增 LLM 后端支持 |
| `run_q1.py` | 低 | 调整输出格式、参数 |
| `run_q2.py` | 低 | 调整输出格式、参数 |
| `evaluate.py` | 中 | 新增评测指标、调整输出表格 |
| `test_env.py` | **高** | **每次新增/修改任务必须同步更新参考计划** |
| `tasks/**/*.json` | 中 | 调整任务难度、新增任务 |
| `student/*.py`（空壳版） | 低 | 修改函数签名规范 |
| `readme.md` | 中 | 课程说明调整 |

---

## 九、快速命令参考

```bash
# 环境验证（每次修改后运行）
python test_env.py

# 单任务调试 Q1
python run_q1.py --task tasks/public/task_02.json \
    --api-key sk-xxx --provider openai-compatible \
    --base-url https://api.deepseek.com --model deepseek-chat

# 单任务调试 Q2
python run_q2.py --task tasks/public/task_02.json \
    --api-key sk-xxx --provider openai-compatible \
    --base-url https://api.deepseek.com --model deepseek-chat

# 批量评测全部任务
for d in public hidden hard extreme nl_only; do
    python evaluate.py --method q1 --task_dir tasks/$d \
        --api-key sk-xxx --provider openai-compatible \
        --base-url https://api.deepseek.com --model deepseek-chat
    python evaluate.py --method q2 --task_dir tasks/$d \
        --api-key sk-xxx --provider openai-compatible \
        --base-url https://api.deepseek.com --model deepseek-chat
done

# 仅评测隐藏任务（用于最终评分）
python evaluate.py --method q1 --task_dir tasks/hidden --output q1_hidden.json
python evaluate.py --method q2 --task_dir tasks/hidden --output q2_hidden.json
python evaluate.py --method q1 --task_dir tasks/hard --output q1_hard.json
python evaluate.py --method q2 --task_dir tasks/hard --output q2_hard.json
python evaluate.py --method q1 --task_dir tasks/extreme --output q1_extreme.json
python evaluate.py --method q2 --task_dir tasks/extreme --output q2_extreme.json
python evaluate.py --method q1 --task_dir tasks/nl_only --output q1_nlonly.json
python evaluate.py --method q2 --task_dir tasks/nl_only --output q2_nlonly.json
```
