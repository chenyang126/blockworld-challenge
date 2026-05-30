import os
import subprocess
import sys


def _install(package):
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            check=True, capture_output=True,
        )
        print(f"[EvalAI] Installed {package}")
    except subprocess.CalledProcessError as e:
        print(f"[EvalAI] Failed to install {package}: {e.stderr}")


# Install dependencies needed by our evaluation script
_install("openai")
_install("pyperplan")

# Import evaluate from main.py
from .main import evaluate
