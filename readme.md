课程设计题目

基于大语言模型的 Blocksworld 任务规划实验

一、课题定位

本课程设计中，教师预先构建一个简化版 Blocksworld 环境，并设计若干任务。学生不需要自己实现环境，也不需要自己写搜索算法，而是围绕同一套环境完成两个规划任务：

第一题：纯 LLM Prompt 规划
学生通过编写 Prompt，调用大语言模型 API，使模型直接输出动作序列。
第二题：LLM + PDDL 规划
学生通过 Prompt 让 LLM 将任务转换为 PDDL problem 文件，再调用 PDDL 规划器生成动作序列。

最终，两个方法生成的动作序列都需要交给教师提供的 Blocksworld 环境验证。

二、教师提供的内容

教师需要提前提供如下文件结构：

blocksworld_course/
│
├── env/
│   ├── blocksworld_env.py        # 教师提供，学生不可修改
│   ├── action_parser.py          # 教师提供，学生不可修改
│   └── validator.py              # 教师提供，学生不可修改
│
├── pddl/
│   └── domain.pddl               # 教师提供，学生不可修改
│
├── tasks/
│   ├── public/
│   │   ├── task_01.json
│   │   ├── task_02.json
│   │   ├── task_03.json
│   │   └── task_04.json
│   │
│   └── hidden/
│       ├── task_05.json
│       ├── task_06.json
│       └── task_07.json
│
├── student/
│   ├── q1_llm_prompt_planner.py  # 学生完成
│   ├── q2_llm_pddl_planner.py    # 学生完成
│   └── prompt_templates/
│       ├── q1_prompt.txt         # 学生完成
│       └── q2_pddl_prompt.txt    # 学生完成
│
├── run_q1.py                     # 教师提供
├── run_q2.py                     # 教师提供
├── evaluate.py                   # 教师提供
└── README.md

其中，学生主要修改：

student/q1_llm_prompt_planner.py
student/q2_llm_pddl_planner.py
student/prompt_templates/q1_prompt.txt
student/prompt_templates/q2_pddl_prompt.txt

其他环境文件、任务文件和评测文件不允许修改。

三、Blocksworld 环境设计
1. 对象

每个任务中包含若干个积木，例如：

A, B, C, D
2. 状态谓词

环境采用经典 Blocksworld 表示：

ontable(x)     表示 x 在桌面上
on(x, y)       表示 x 在 y 上
clear(x)       表示 x 上方没有其他积木
holding(x)     表示机械手正在拿着 x
handempty      表示机械手为空
3. 动作空间

环境只允许四类动作：

PICKUP(x)
PUTDOWN(x)
UNSTACK(x, y)
STACK(x, y)
四、教师提供的环境接口

教师提供 BlocksworldEnv，学生不需要改。

class BlocksworldEnv:
    def __init__(self, blocks):
        """
        blocks: List[str]
        例如 ["A", "B", "C"]
        """

    def reset(self, initial_state):
        """
        initial_state: List[str]
        例如 ["on(C,A)", "ontable(A)", "ontable(B)", "clear(C)", "clear(B)", "handempty"]
        """

    def step(self, action):
        """
        action: str
        例如 "UNSTACK(C,A)"

        返回：
        {
            "success": True / False,
            "message": "action executed" / "precondition not satisfied",
            "state": 当前状态
        }
        """

    def execute_plan(self, plan):
        """
        plan: List[str]
        例如：
        [
            "UNSTACK(C,A)",
            "PUTDOWN(C)",
            "PICKUP(B)",
            "STACK(B,C)"
        ]

        返回：
        {
            "plan_valid": True / False,
            "failed_step": None 或出错步骤编号,
            "failed_action": None 或出错动作,
            "final_state": 当前最终状态
        }
        """

    def is_goal_satisfied(self, goal_state):
        """
        goal_state: List[str]

        返回 True / False
        """

    def render(self):
        """
        输出当前积木堆叠情况，方便调试。
        """
五、任务文件格式

每个任务用一个 JSON 文件描述。

例如 task_02.json：

{
  "task_id": "task_02",
  "blocks": ["A", "B", "C"],
  "natural_language": "There are three blocks A, B, and C. Initially, C is on A, A is on the table, and B is on the table. The goal is to make A on B and B on C.",
  "initial_state": [
    "on(C,A)",
    "ontable(A)",
    "ontable(B)",
    "clear(C)",
    "clear(B)",
    "handempty"
  ],
  "goal_state": [
    "on(A,B)",
    "on(B,C)",
    "ontable(C)"
  ]
}

教师可以同时给学生两种输入：

结构化状态：
"initial_state": [...]
"goal_state": [...]
自然语言任务描述：
"natural_language": "..."

第一题和第二题都可以使用这些信息，但学生不能直接硬编码答案。

六、教师设计的任务集

建议设置 4 个公开任务，3 个隐藏测试任务。

Task 01：单步堆叠任务
Blocks: A, B

Initial:
ontable(A), ontable(B), clear(A), clear(B), handempty

Goal:
on(A, B)

目标图：

A
B
---------
table

参考最短计划：

PICKUP(A)
STACK(A,B)
Task 02：三积木重排任务
Blocks: A, B, C

Initial:
on(C,A), ontable(A), ontable(B), clear(C), clear(B), handempty

Goal:
on(A,B), on(B,C), ontable(C)

初始状态：

C
A     B
---------
table

目标状态：

A
B
C
---------
table

参考计划：

UNSTACK(C,A)
PUTDOWN(C)
PICKUP(B)
STACK(B,C)
PICKUP(A)
STACK(A,B)
Task 03：四积木反转任务
Blocks: A, B, C, D

Initial:
on(D,C), on(C,B), on(B,A), ontable(A), clear(D), handempty

Goal:
on(A,B), on(B,C), on(C,D), ontable(D)

初始状态：

D
C
B
A
---------
table

目标状态：

A
B
C
D
---------
table

这个任务可以测试 LLM 是否能处理较长的拆塔和重组过程。

Task 04：带无关积木的任务
Blocks: A, B, C, D

Initial:
on(C,A), ontable(A), ontable(B), ontable(D), clear(C), clear(B), clear(D), handempty

Goal:
on(A,B), on(B,C), ontable(C), ontable(D)

这里 D 是干扰物体，不需要移动。这个任务可以测试 LLM 是否会做多余动作。

七、第一题：纯 LLM Prompt 规划
任务要求

学生需要编写 Prompt，并调用 LLM API，使模型直接输出一个动作序列。

输入：

task = {
    "blocks": ["A", "B", "C"],
    "natural_language": "...",
    "initial_state": [...],
    "goal_state": [...]
}

输出：

[
    "UNSTACK(C,A)",
    "PUTDOWN(C)",
    "PICKUP(B)",
    "STACK(B,C)",
    "PICKUP(A)",
    "STACK(A,B)"
]
学生需要实现的接口

文件：student/q1_llm_prompt_planner.py

def build_prompt(task: dict) -> str:
    """
    输入一个任务，返回给 LLM 的 Prompt。
    学生需要重点设计这个函数。
    """
    pass


def parse_llm_output(response: str) -> list[str]:
    """
    将 LLM 的文本输出解析成动作序列。
    例如将：
    UNSTACK(C,A)
    PUTDOWN(C)

    解析为：
    ["UNSTACK(C,A)", "PUTDOWN(C)"]
    """
    pass


def plan_with_llm(task: dict, llm_client) -> list[str]:
    """
    调用 LLM API，返回动作序列。
    """
    prompt = build_prompt(task)
    response = llm_client.chat(prompt)
    plan = parse_llm_output(response)
    return plan
第一题限制

为了保证第一题是“纯 Prompt 规划”，可以设置如下限制：

学生不能调用 PDDL 规划器；
学生不能写 BFS、DFS、A* 等搜索算法；
学生不能根据 task_id 硬编码答案；
学生可以优化 Prompt；
学生可以要求 LLM 输出固定格式；
学生可以让 LLM 在 Prompt 中进行自检，但最终只能输出动作序列。
第一题推荐 Prompt 方向

学生可以在 Prompt 中说明：

You are solving a Blocksworld planning task.

Available actions are:
PICKUP(x), PUTDOWN(x), UNSTACK(x,y), STACK(x,y).

You must obey action preconditions.
You must output only a valid sequence of actions.
Do not explain.
Do not output markdown.

Initial state:
...

Goal state:
...

Output format:
One action per line.

更高质量的 Prompt 可以要求模型先内部检查前提条件，但不输出推理过程：

Before producing the final answer, internally check whether each action is executable.
Only output the final action sequence.
八、第二题：LLM + PDDL 规划
任务要求

第二题中，学生不再让 LLM 直接输出动作计划，而是让 LLM 生成 PDDL problem 文件，然后调用经典规划器求解。

整体流程：

任务描述
   ↓
LLM 生成 problem.pddl
   ↓
PDDL planner 求解
   ↓
得到动作序列
   ↓
送入 BlocksworldEnv 验证
教师提供固定 domain.pddl

学生不需要写 domain。

(define (domain blocksworld)
  (:requirements :strips :typing)
  (:types block)

  (:predicates
    (on ?x - block ?y - block)
    (ontable ?x - block)
    (clear ?x - block)
    (holding ?x - block)
    (handempty)
  )

  (:action pickup
    :parameters (?x - block)
    :precondition (and
      (ontable ?x)
      (clear ?x)
      (handempty)
    )
    :effect (and
      (holding ?x)
      (not (ontable ?x))
      (not (clear ?x))
      (not (handempty))
    )
  )

  (:action putdown
    :parameters (?x - block)
    :precondition (and
      (holding ?x)
    )
    :effect (and
      (ontable ?x)
      (clear ?x)
      (handempty)
      (not (holding ?x))
    )
  )

  (:action unstack
    :parameters (?x - block ?y - block)
    :precondition (and
      (on ?x ?y)
      (clear ?x)
      (handempty)
    )
    :effect (and
      (holding ?x)
      (clear ?y)
      (not (on ?x ?y))
      (not (clear ?x))
      (not (handempty))
    )
  )

  (:action stack
    :parameters (?x - block ?y - block)
    :precondition (and
      (holding ?x)
      (clear ?y)
    )
    :effect (and
      (on ?x ?y)
      (clear ?x)
      (handempty)
      (not (holding ?x))
      (not (clear ?y))
    )
  )
)
学生需要实现的接口

文件：student/q2_llm_pddl_planner.py

def build_pddl_prompt(task: dict, domain_pddl: str) -> str:
    """
    输入任务和 domain.pddl，构造让 LLM 生成 problem.pddl 的 Prompt。
    """
    pass


def generate_problem_pddl(task: dict, domain_pddl: str, llm_client) -> str:
    """
    调用 LLM API，生成 problem.pddl 文本。
    """
    prompt = build_pddl_prompt(task, domain_pddl)
    response = llm_client.chat(prompt)
    return response


def solve_pddl(domain_path: str, problem_path: str) -> list[str]:
    """
    调用 PDDL planner，返回动作序列。
    可以使用 pyperplan 或 fast-downward。
    """
    pass


def plan_with_llm_pddl(task: dict, domain_path: str, llm_client) -> list[str]:
    """
    完整流程：
    1. 读取 domain.pddl
    2. 调用 LLM 生成 problem.pddl
    3. 调用 PDDL planner
    4. 返回动作序列
    """
    pass
第二题限制
domain.pddl 由教师提供，学生不能修改；
学生只需要让 LLM 生成 problem.pddl；
学生必须调用 PDDL planner 得到动作序列；
最终动作序列必须通过教师提供的环境验证；
不允许根据任务 ID 硬编码 problem 文件或动作序列。
第二题推荐 Prompt 方向
You are given a Blocksworld planning task.

Your job is to generate a valid PDDL problem file.

The domain is fixed and shown below:
[domain.pddl]

Task:
Blocks: A, B, C

Initial state:
on(C,A), ontable(A), ontable(B), clear(C), clear(B), handempty

Goal state:
on(A,B), on(B,C), ontable(C)

Requirements:
1. Use the domain name blocksworld.
2. Declare all blocks as objects of type block.
3. Use only predicates defined in the domain.
4. Output only the PDDL problem file.
5. Do not include explanations or markdown.
九、统一评测方式

教师提供统一评测器，学生提交的两个 planner 都会被同一个环境验证。

评测流程：

env = BlocksworldEnv(task["blocks"])
env.reset(task["initial_state"])

plan = student_planner(task)

result = env.execute_plan(plan)
goal_success = env.is_goal_satisfied(task["goal_state"])

输出格式：

{
  "task_id": "task_02",
  "method": "q1_llm_prompt",
  "plan": [
    "UNSTACK(C,A)",
    "PUTDOWN(C)",
    "PICKUP(B)",
    "STACK(B,C)",
    "PICKUP(A)",
    "STACK(A,B)"
  ],
  "plan_valid": true,
  "goal_success": true,
  "num_steps": 6,
  "failed_step": null,
  "failed_action": null
}
十、运行接口设计
第一题运行方式
python run_q1.py --task tasks/public/task_02.json

输出：

Task: task_02
Method: LLM Prompt Planner

Generated plan:
1. UNSTACK(C,A)
2. PUTDOWN(C)
3. PICKUP(B)
4. STACK(B,C)
5. PICKUP(A)
6. STACK(A,B)

Plan valid: True
Goal achieved: True
Number of steps: 6
第二题运行方式
python run_q2.py --task tasks/public/task_02.json

输出：

Task: task_02
Method: LLM + PDDL Planner

Generated problem file:
outputs/task_02/problem.pddl

Planner plan:
1. UNSTACK(C,A)
2. PUTDOWN(C)
3. PICKUP(B)
4. STACK(B,C)
5. PICKUP(A)
6. STACK(A,B)

Plan valid: True
Goal achieved: True
Number of steps: 6
批量评测方式
python evaluate.py --method q1 --task_dir tasks/public
python evaluate.py --method q2 --task_dir tasks/public

教师隐藏测试时：

python evaluate.py --method q1 --task_dir tasks/hidden
python evaluate.py --method q2 --task_dir tasks/hidden
十一、评价指标

建议评价以下指标：

指标	含义
Plan Validity	动作序列是否每一步都满足前提条件
Goal Success	最终状态是否满足目标
Plan Length	动作序列长度
Invalid Action Count	非法动作数量
PDDL Generation Success	LLM 是否成功生成可解析的 PDDL problem
Planner Success	PDDL planner 是否成功求解
十二、两题的核心区别
对比项	第一题：纯 LLM Prompt	第二题：LLM + PDDL
LLM 作用	直接生成动作序列	生成 PDDL problem
是否使用规划器	不使用	使用
计划合法性	不稳定，需要环境验证	通常更稳定
错误类型	前提条件错误、遗漏动作、目标未达成	PDDL语法错误、谓词错误、对象遗漏
考察重点	Prompt设计能力	LLM符号建模 + 规划器调用能力
十三、学生最终提交内容

学生需要提交：

student/q1_llm_prompt_planner.py
student/q2_llm_pddl_planner.py
student/prompt_templates/q1_prompt.txt
student/prompt_templates/q2_pddl_prompt.txt
实验报告.pdf

实验报告建议包括：

1. 实验目标
2. Blocksworld环境说明
3. 第一题：纯LLM Prompt规划方法
4. 第二题：LLM+PDDL规划方法
5. 实验结果
6. 失败案例分析
7. 两种方法对比
8. 总结
十四、评分标准

总分 100 分。

模块	分值	说明
第一题 Prompt 规划	25	能调用 LLM，输出格式规范，计划通过环境验证
第二题 LLM+PDDL	30	能正确生成 PDDL problem，并调用规划器求解
接口规范	15	严格遵守教师提供的接口，不修改环境和评测器
实验分析	20	对比两种方法的成功率、错误类型和计划长度
报告质量	10	结构清晰，表达规范，有总结和反思
十五、可以写进课程设计说明书的正式版本

可以这样表述：

本课程设计由教师提供一个完整的 Blocksworld 任务规划环境，包括状态表示、动作空间、状态转移函数、任务集和统一评测器。学生需要在该环境上完成两个规划任务。第一题要求学生仅通过设计 Prompt 并调用大语言模型 API，直接生成满足目标条件的动作序列；第二题要求学生结合大语言模型与 PDDL 规划方法，利用大语言模型将任务描述转换为 PDDL problem 文件，再调用经典规划器生成动作序列。两个任务生成的计划均需要在教师提供的 Blocksworld 环境中执行和验证。通过该课程设计，学生可以理解大语言模型在符号规划任务中的能力与局限，并掌握将大语言模型与经典规划器结合解决规划问题的基本方法。

这样设计之后，课题边界会非常清晰：

教师负责：环境、任务、接口、验证器、评分。
学生负责：Prompt 设计、API 调用、LLM 输出解析、LLM+PDDL 流程实现。