#!/usr/bin/env bash
# 学生作业自检脚本：跑评估前先确认环境/数据/权重都就位。
# 用法：先 `source .venv/bin/activate`，再 `bash scripts/check_setup.sh`
set -u

ROOT="${STABLEWM_HOME:-$HOME/.stable_worldmodel}"
CKPT_DIR="$ROOT/checkpoints/tworoom"
ok=1

echo "==================== 环境自检 ===================="
echo "STABLEWM_HOME = $ROOT"
echo

# 1. Python 版本
pyver=$(python -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null)
if [ "$pyver" = "3.10" ]; then echo "[✓] Python 版本 $pyver";
else echo "[✗] Python 版本是 $pyver，要求 3.10"; ok=0; fi

# 2. 关键依赖
if python -c 'import stable_worldmodel' 2>/dev/null; then echo "[✓] stable_worldmodel 已安装";
else echo "[✗] 未安装 stable_worldmodel，请先 pip install 'stable-worldmodel[train,env]'"; ok=0; fi

# 3. CUDA（可选：有 GPU 用完整配置，无 GPU 用 CPU 轻量配置）
if python -c 'import torch,sys;sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
  echo "[✓] PyTorch CUDA 可用 → 可用完整配置 (--config-name=tworoom)"; HAS_GPU=1;
else echo "[!] 未检测到 GPU → 用 CPU 轻量配置 (--config-name=tworoom_cpu)"; HAS_GPU=0; fi

# 4. 数据集
if [ -f "$ROOT/datasets/tworoom.h5" ]; then echo "[✓] 数据集 datasets/tworoom.h5 存在";
else echo "[✗] 缺少 $ROOT/datasets/tworoom.h5"; ok=0; fi

# 5. 权重 + config
shopt -s nullglob
pts=("$CKPT_DIR"/*.pt)
if [ ${#pts[@]} -ge 1 ]; then echo "[✓] 找到权重: $(basename "${pts[0]}")";
else echo "[✗] $CKPT_DIR 下没有 .pt 权重文件"; ok=0; fi
if [ -f "$CKPT_DIR/config.json" ]; then echo "[✓] config.json 存在";
else echo "[✗] 缺少 $CKPT_DIR/config.json（必须和权重在同一目录）"; ok=0; fi

echo
if [ "$ok" = "1" ]; then
  ckpt="$(basename "${pts[0]:-weights_epoch_24.pt}")"
  echo "==> 全部就绪！运行评估："
  if [ "${HAS_GPU:-0}" = "1" ]; then
    echo "    python eval.py --config-name=tworoom     policy=tworoom/$ckpt   # GPU 完整版"
  else
    echo "    python eval.py --config-name=tworoom_cpu policy=tworoom/$ckpt   # CPU 轻量版"
  fi
else
  echo "==> 存在问题，请按上面 [✗] 项修复后重试。参考 docs/ASSIGNMENT_tworoom.md"
fi
echo "================================================="
exit $((1 - ok))
