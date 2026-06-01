#!/usr/bin/env python3
import os
from pathlib import Path

#_nvidia_base = r"C:\Users\Ondosh\PycharmProjects\LLM-Audio\.venv\Lib\site-packages\nvidia" - shitty path

_nvidia_base = Path(__file__).parent  / ".venv" / "Lib" / "site-packages" / "nvidia"
for _d in [r"cublas\bin", r"cudnn\bin", r"cuda_runtime\bin", r"cuda_nvrtc\bin"]:
    _full = os.path.join(_nvidia_base, _d)
    if os.path.exists(_full):
        os.add_dll_directory(_full)

"""
Meeting summarizer pipeline with per-stage caching:
  MP4/audio → WAV → transcript.txt → summary.md

Каждый этап сохраняется рядом с исходным файлом.
При повторном запуске уже готовые этапы пропускаются.
Every stage is saving near original file. If this file was already tried to process,
it will skip stages which was completed.

Usage:
    python main.py meeting.mp4
    python main.py meeting.mp3
    python main.py meeting.wav
    python main.py meeting.mp4 --model mistral-small3.1:24b --lang ru
    python main.py meeting.mp4 --force-transcribe   # transcribe again
    python main.py meeting.mp4 --force-summary      # make summary again
    python main.py meeting.mp4 --force              # again all
"""

import argparse
import subprocess
import sys
import json
import requests
from pathlib import Path

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
OLLAMA_URL            = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL  = "mistral-small3.1:24b"
DEFAULT_WHISPER_MODEL = "large-v3"
DEFAULT_LANG          = None

# Поддерживаемые форматы
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m2ts", ".ts"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".aac", ".opus", ".wma"}
WAV_EXTENSION    = ".wav"

SUMMARY_PROMPT = """Ты — помощник по созданию конспектов лекций и совещаний.

Ниже приведена транскрипция. Составь структурированный конспект:

1. **Резюме среднего размера** (5-8 предложений о чём была лекция/совещание)
2. **Ключевые темы и понятия** (маркированный список)
3. **Принятые решения** (если есть)
4. **Задачи и ответственные** (если упоминались)
5. **Открытые вопросы** (если остались нерешёнными)

Пиши на том же языке, что и транскрипция.

Транскрипция:
---
{transcript}
---

Конспект:"""


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def detect_input_type(input_path: Path) -> str:
    """Определяет тип входного файла: 'video', 'audio', 'wav' или завершает с ошибкой."""
    suffix = input_path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix == WAV_EXTENSION:
        return "wav"
    print(f"ERROR: unsupported format of file: '{suffix}'.")
    print(f"  Видео: {', '.join(sorted(VIDEO_EXTENSIONS))}")
    print(f"  Аудио: {', '.join(sorted(AUDIO_EXTENSIONS))}")
    print(f"  WAV:   .wav")
    sys.exit(1)


def stage_paths(input_path: Path, input_type: str) -> dict:
    """Возвращает пути к файлам каждого этапа."""
    stem = input_path.stem
    d    = input_path.parent
    paths = {
        "transcript": d / f"{stem}_transcript.txt",
        "summary":    d / f"{stem}_summary.md",
    }
    if input_type == "wav":
        # WAV-файл используется напрямую, этап конвертации пропускается
        paths["wav"] = input_path
    else:
        paths["wav"] = d / f"{stem}.wav"
    return paths


def check_stages(paths: dict, input_type: str) -> dict:
    """Проверяет какие этапы уже выполнены."""
    status = {k: v.exists() and v.stat().st_size > 0 for k, v in paths.items()}
    # Для WAV-входа этап конвертации считается выполненным всегда
    if input_type == "wav":
        status["wav"] = True
    return status


def print_status(status: dict, input_type: str):
    icons  = {True: "✓", False: "·"}
    labels = {"transcript": "Транскрипт", "summary": "Конспект"}
    if input_type != "wav":
        labels = {"wav": "Аудио (WAV)", **labels}

    print("\n  Состояние этапов:")
    for key, label in labels.items():
        print(f"    [{icons[status[key]]}] {label}")
    print()


# ─────────────────────────────────────────
# STAGE 1: видео/аудио → WAV
# ─────────────────────────────────────────
def convert_to_wav(input_path: Path, audio_path: Path, input_type: str) -> None:
    action = "Извлечение аудио" if input_type == "video" else "Конвертация аудио"
    print(f"[1/3] {action} из {input_path.name} ...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Ошибка ffmpeg:")
        print(result.stderr)
        sys.exit(1)
    print(f"    ✓ WAV сохранён: {audio_path}")


# ─────────────────────────────────────────
# STAGE 2: WAV → transcript
# ─────────────────────────────────────────
def transcribe(audio_path: Path, transcript_path: Path, whisper_model: str, language: str | None) -> str:
    print(f"[2/3] Транскрипция (модель: {whisper_model}) ...")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Ошибка: установи faster-whisper:  pip install faster-whisper")
        sys.exit(1)

    model = WhisperModel(whisper_model, device="auto", compute_type="auto")

    kwargs = {"beam_size": 5}
    if language:
        kwargs["language"] = language

    segments, info = model.transcribe(str(audio_path), **kwargs)
    print(f"    Определён язык: {info.language} (вероятность {info.language_probability:.0%})")

    transcript_parts = []
    for seg in segments:
        timestamp = f"[{seg.start:06.1f}s → {seg.end:06.1f}s]"
        transcript_parts.append(f"{timestamp} {seg.text.strip()}")

    transcript = "\n".join(transcript_parts)
    transcript_path.write_text(transcript, encoding="utf-8")
    print(f"    ✓ Транскрипт сохранён: {transcript_path} ({len(transcript)} символов)")
    return transcript


# ─────────────────────────────────────────
# STAGE 3: transcript → summary
# ─────────────────────────────────────────
def summarize_with_ollama(transcript: str, summary_path: Path, model: str, ollama_url: str) -> str:
    print(f"[3/3] Генерация конспекта (Ollama / {model}) ...")

    # Проверяем доступность Ollama и наличие модели
    try:
        r = requests.get(f"{ollama_url}/api/tags", timeout=5)
        r.raise_for_status()
        available = [m["name"] for m in r.json().get("models", [])]
        if model not in available:
            print(f"  Ошибка: модель '{model}' не найдена в Ollama.")
            print(f"  Доступные модели: {', '.join(available) or 'нет'}")
            print(f"  Скачай модель:  ollama pull {model}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"  Ошибка: не удалось подключиться к Ollama по адресу {ollama_url}")
        print(f"  Убедись что Ollama запущена")
        sys.exit(1)
    except Exception as e:
        print(f"  Ошибка Ollama: {e}")
        sys.exit(1)

    prompt = SUMMARY_PROMPT.format(transcript=transcript)

    response = requests.post(
        f"{ollama_url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": True},
        stream=True,
        timeout=600,
    )
    response.raise_for_status()

    summary_parts = []
    print("\n" + "─" * 60)
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        token = chunk.get("response", "")
        print(token, end="", flush=True)
        summary_parts.append(token)
        if chunk.get("done"):
            break

    print("\n" + "─" * 60 + "\n")

    summary = "".join(summary_parts)
    summary_path.write_text(summary, encoding="utf-8")
    print(f"    ✓ Конспект сохранён: {summary_path}")
    return summary


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    all_supported = sorted(VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | {WAV_EXTENSION})

    parser = argparse.ArgumentParser(
        description=(
            "Видео/Аудио → WAV → транскрипция (Whisper) → конспект (Ollama)\n"
            f"Поддерживаемые форматы: {', '.join(all_supported)}\n"
            "Каждый этап кешируется, повторный запуск пропускает готовые."
        )
    )
    parser.add_argument("input",              help="Путь к видео- или аудиофайлу")
    parser.add_argument("--model",            default=DEFAULT_OLLAMA_MODEL,  help=f"Ollama-модель (по умолчанию: {DEFAULT_OLLAMA_MODEL})")
    parser.add_argument("--whisper-model",    default=DEFAULT_WHISPER_MODEL, help=f"Whisper-модель (по умолчанию: {DEFAULT_WHISPER_MODEL})")
    parser.add_argument("--lang",             default=DEFAULT_LANG,          help="Язык аудио (ru, en, ...). По умолчанию — авто")
    parser.add_argument("--ollama-url",       default=OLLAMA_URL,            help=f"URL Ollama (по умолчанию: {OLLAMA_URL})")
    parser.add_argument("--force-audio",      action="store_true", help="Переконвертировать аудио даже если WAV уже есть")
    parser.add_argument("--force-transcribe", action="store_true", help="Перетранскрибировать даже если transcript уже есть")
    parser.add_argument("--force-summary",    action="store_true", help="Переделать конспект даже если summary уже есть")
    parser.add_argument("--force",            action="store_true", help="Все этапы заново")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Файл не найден: {input_path}")
        sys.exit(1)

    input_type = detect_input_type(input_path)
    paths      = stage_paths(input_path, input_type)
    status     = check_stages(paths, input_type)

    type_label = {"video": "Видео", "audio": "Аудио", "wav": "WAV"}[input_type]

    print(f"\n{'═' * 60}")
    print(f"  Meeting Summarizer")
    print(f"  Файл:    {input_path.name} ({type_label})")
    print(f"  Whisper: {args.whisper_model}")
    print(f"  Ollama:  {args.model} @ {args.ollama_url}")
    print_status(status, input_type)

    force_audio      = args.force or args.force_audio
    force_transcribe = args.force or args.force_transcribe
    force_summary    = args.force or args.force_summary

    # ── Этап 1: конвертация в WAV (пропускается для .wav-входа) ──
    if input_type == "wav":
        print(f"[1/3] Входной файл уже WAV, конвертация не нужна → {input_path.name}")
    elif not status["wav"] or force_audio:
        convert_to_wav(input_path, paths["wav"], input_type)
    else:
        print(f"[1/3] WAV уже есть, пропускаю → {paths['wav'].name}")

    # ── Этап 2: транскрипция ──
    if not status["transcript"] or force_transcribe:
        transcript = transcribe(paths["wav"], paths["transcript"], args.whisper_model, args.lang)
    else:
        print(f"[2/3] Транскрипт уже есть, пропускаю → {paths['transcript'].name}")
        transcript = paths["transcript"].read_text(encoding="utf-8")

    # ── Этап 3: конспект ──
    if not status["summary"] or force_summary:
        summarize_with_ollama(transcript, paths["summary"], args.model, args.ollama_url)
    else:
        print(f"[3/3] Конспект уже есть, пропускаю → {paths['summary'].name}")

    print(f"{'═' * 60}")
    print(f"✓ Готово!")
    print(f"  Транскрипт: {paths['transcript']}")
    print(f"  Конспект:   {paths['summary']}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()