# 课程设计作业：LeWorldModel (LeWM) — TwoRoom 评估

**目标**：部署环境，加载老师提供的模型权重，**跑通 TwoRoom 任务的评估流程**。无需训练模型。
**有 GPU 用 GPU（结果更全），没 GPU 用 CPU 也能跑通。**

---

## 第 1 步：装环境

要求：Linux + Python **3.10**（GPU 可选）。无图形界面的服务器先装渲染库：
```bash
sudo apt-get install -y libegl1 libgl1 libglib2.0-0
```

拉代码、建虚拟环境、装依赖：
```bash
git clone <仓库地址> le-wm && cd le-wm
uv venv --python=3.10 && source .venv/bin/activate   # 没有 uv 则用: python3.10 -m venv .venv && source .venv/bin/activate
uv pip install "stable-worldmodel[train,env]"        # 没有 uv 则用: pip install "stable-worldmodel[train,env]"
```

---

## 第 2 步：放老师提供的文件

数据和权重都从一个根目录读取，默认 `~/.stable_worldmodel`。把老师给的 **3 个文件**按下面结构放好：

```
~/.stable_worldmodel/
├── datasets/
│   └── tworoom.h5                  ← 数据集
└── checkpoints/
    └── tworoom/
        ├── weights_epoch_24.pt     ← 模型权重
        └── config.json             ← 模型结构（必须和权重放一起！）
```

命令：
```bash
ROOT=~/.stable_worldmodel
mkdir -p $ROOT/datasets $ROOT/checkpoints/tworoom
cp /路径/tworoom.h5          $ROOT/datasets/
cp /路径/weights_epoch_24.pt $ROOT/checkpoints/tworoom/
cp /路径/config.json         $ROOT/checkpoints/tworoom/
```

> 想换目录：`export STABLEWM_HOME=/你的路径`（其余结构不变）。

跑之前可先自检：`bash scripts/check_setup.sh`

---

## 第 3 步：运行评估

### ▶ 有 GPU（完整评估，50 回合）
```bash
python eval.py --config-name=tworoom policy=tworoom/weights_epoch_24.pt
```
预期：`success_rate` ≈ **84%**，几十秒完成。

### ▶ 没 GPU（CPU 轻量版，5 回合，约 15 秒）
```bash
python eval.py --config-name=tworoom_cpu policy=tworoom/weights_epoch_24.pt
```
预期：约 15 秒完成，打印出 `success_rate`。
> CPU 版为了速度把回合数和规划规模调小了，成功率数值会和 84% 不同，**这是正常的**——本作业只要求“跑通流程”。
> （不要用 GPU 的完整配置在 CPU 上跑：默认参数在 CPU 上要 **50 分钟以上**。）

`policy=tworoom/weights_epoch_24.pt` 是相对 `checkpoints/` 的路径，**不要**加 `checkpoints/` 前缀。

---

## 第 4 步：确认跑通

终端打印类似：
```
{'success_rate': 84.0, 'episode_successes': array([ True, False, ...]), 'seeds': None}
```
同时在 `~/.stable_worldmodel/checkpoints/tworoom/` 下生成：
- 结果文件 `tworoom_results.txt`（CPU 版为 `tworoom_cpu_results.txt`）
- 每个回合的可视化视频 `env_*.mp4`

**只要看到 `success_rate` 并生成结果文件/视频，即视为评估流程跑通。**

---

## 常见问题

| 现象 | 解决 |
|---|---|
| 加载模型报错 / 找不到 config | `config.json` 必须和 `.pt` 在同一目录。 |
| 找不到 `tworoom.h5` | 数据集没放到 `datasets/`，或 `STABLEWM_HOME` 没设对。 |
| `policy` 路径错误 | 路径相对 `checkpoints/` 写，不要带 `checkpoints/` 前缀。 |
| EGL / 渲染报错 | 执行第 1 步的 `apt-get install`。 |
| 没有 GPU | 用 CPU 轻量版命令（`--config-name=tworoom_cpu`）。 |

---

## 提交要求（建议）
1. 运行截图（含 `success_rate` 那一行）。
2. 结果文件 `tworoom(_cpu)_results.txt`。
3. 任意一个 `env_*.mp4`。
4. 简短报告：部署步骤、遇到的问题及解决、对评估流程（基于世界模型的 MPC 规划 + 成功率指标）的理解。
