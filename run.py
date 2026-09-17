#!/usr/bin/env python3
"""
Кроссплатформенный лаунчер (замена llm-stt.ps1).
Находит python внутри локального .venv (Windows/Linux/macOS)
и запускает main.py с переданными аргументами.

Использование:
    python run.py meeting.mp4 --lang ru
"""
import sys
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
VENV = ROOT / ".venv"


def find_venv_python() -> Path:
    candidates = [
        VENV / "Scripts" / "python.exe",   # Windows
        VENV / "bin" / "python3",          # Linux/macOS
        VENV / "bin" / "python",
    ]
    for c in candidates:
        if c.exists():
            return c
    # venv не найден — работаем текущим интерпретатором
    return Path(sys.executable)


def main():
    python = find_venv_python()
    main_py = ROOT / "main.py"
    cmd = [str(python), str(main_py), *sys.argv[1:]]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
