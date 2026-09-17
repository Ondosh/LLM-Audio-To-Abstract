#!/usr/bin/env python3
"""
Кроссплатформенная установка окружения для Meeting Summarizer.
Создаёт .venv, ставит зависимости из requirements.txt, проверяет ffmpeg.

Использование:
    python setup.py
"""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"


def run(cmd, **kwargs):
    print(f"  $ {' '.join(map(str, cmd))}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"  ✗ Команда завершилась с ошибкой (код {result.returncode})")
        sys.exit(result.returncode)


def venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python3"


def create_venv():
    if VENV.exists():
        print(f"[1/3] Виртуальное окружение уже есть: {VENV}")
        return
    print(f"[1/3] Создаю виртуальное окружение: {VENV}")
    run([sys.executable, "-m", "venv", str(VENV)])
    print("    ✓ Готово")


def install_requirements():
    print("[2/3] Устанавливаю Python-зависимости...")
    py = venv_python()
    if not py.exists():
        print(f"  ✗ Не найден python в venv: {py}")
        sys.exit(1)
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    if REQUIREMENTS.exists():
        run([str(py), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    else:
        print(f"  ✗ Не найден {REQUIREMENTS}")
        sys.exit(1)
    print("    ✓ Зависимости установлены")


def check_ffmpeg():
    print("[3/3] Проверяю наличие ffmpeg...")
    path = shutil.which("ffmpeg")
    if path:
        print(f"    ✓ ffmpeg найден: {path}")
        return

    system = platform.system()
    print("    ✗ ffmpeg не найден в PATH.")
    print("    Установи его вручную:")
    if system == "Windows":
        print("      winget install ffmpeg")
        print("      (или: choco install ffmpeg)")
    elif system == "Darwin":
        print("      brew install ffmpeg")
    else:
        print("      sudo apt update && sudo apt install ffmpeg")
        print("      (или через пакетный менеджер твоего дистрибутива)")


def main():
    print(f"\n{'═' * 60}")
    print("  Установка окружения Meeting Summarizer")
    print(f"  ОС: {platform.system()} {platform.release()}")
    print(f"{'═' * 60}\n")

    create_venv()
    install_requirements()
    check_ffmpeg()

    print(f"\n{'═' * 60}")
    print("✓ Установка завершена")
    print("  Запуск:  python run.py meeting.mp4")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
