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

## 第 2 步：下载并放好数据与权重

老师把数据集、模型权重、配置打包成了一个文件：**`tworoom_student_data.zip`（约 92 MB）**。

**① 下载**（地址由老师提供）：
```bash
# 从老师给的链接下载到当前目录，例如：
wget <老师提供的下载链接> -O tworoom_student_data.zip
```

**② 解压到数据根目录**（默认 `~/.stable_worldmodel`），解压后会自动形成正确结构，无需手动拷贝：
```bash
unzip tworoom_student_data.zip -d ~/.stable_worldmodel
```

解压后应是这样：
```
~/.stable_worldmodel/
├── datasets/tworoom.h5                          ← 数据集（精简版）
└── checkpoints/tworoom/
    ├── weights_epoch_24.pt                      ← 模型权重
    └── config.json                              ← 模型结构
```

> 想换目录：先 `export STABLEWM_HOME=/你的路径`，再把上面 `unzip -d` 的目标改成同一路径。

**③ 自检**（确认环境/文件都就位，再跑评估）：
```bash
bash scripts/check_setup.sh
```

> ⚠️ **关于数据集**：为了把体积从 12GB 压到 92MB，这个包是**精简版**，只包含默认评估会用到的图像帧。
> **请不要修改 `seed` 或回合数 `num_eval`** —— 否则会用到没有保留图像的帧，导致结果错误。
> 直接用下面第 3 步的命令即可。

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
预期：约 15 秒完成，打印 `success_rate`（默认 5 个回合，实测 **5/5 成功**）。
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
| 加载模型报错 / 找不到 config | `config.json` 必须和 `.pt` 在同一目录（解压后会自动满足）。 |
| 找不到 `tworoom.h5` | 确认 zip 已解压到 `~/.stable_worldmodel`（或你设的 `STABLEWM_HOME`）。 |
| `goal not in info_dict` / 结果异常 | 你改了 `seed` 或 `num_eval`。精简数据集只支持默认配置，请用原命令。 |
| `policy` 路径错误 | 路径相对 `checkpoints/` 写，不要带 `checkpoints/` 前缀。 |
| EGL / 渲染报错 | 执行第 1 步的 `apt-get install`。 |
| 没有 GPU | 用 CPU 轻量版命令（`--config-name=tworoom_cpu`）。 |

---

## 提交要求（建议）
1. 运行截图（含 `success_rate` 那一行）。
2. 结果文件 `tworoom(_cpu)_results.txt`。
3. 任意一个 `env_*.mp4`。
4. 简短报告：部署步骤、遇到的问题及解决、对评估流程（基于世界模型的 MPC 规划 + 成功率指标）的理解。
