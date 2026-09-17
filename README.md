# Meeting Summarizer

Видео/Аудио → WAV → транскрипция (Whisper) → конспект (Ollama).
Каждый этап кешируется, повторный запуск пропускает готовые.

Поддерживаемые форматы: .aac, .avi, .flac, .m2ts, .m4a, .mkv, .mov, .mp3, .mp4,
.ogg, .opus, .ts, .wav, .webm, .wma

## Установка

Одна команда ставит venv, все зависимости и проверяет ffmpeg (Windows / Linux / macOS):

```
python setup.py
```

ffmpeg через pip не ставится — если его нет, `setup.py` подскажет команду для
твоей ОС (`winget`/`choco`/`brew`/`apt`).

## Запуск (Windows / Linux / macOS)

Скрипт `run.py` сам находит python внутри `.venv` (не важно, Windows это или
Linux/macOS) и запускает `main.py`:

```
python run.py meeting.mp4
python run.py meeting.mp4 --model mistral-small3.1:24b --lang ru
python run.py meeting.mp4 --force-transcribe
```

Если `.venv` не найден рядом со скриптом, `run.py` запустит `main.py` тем же
интерпретатором, которым запущен сам `run.py`.

Также можно вызывать `main.py` напрямую (тогда используется активный сейчас
интерпретатор, включая CUDA/cuDNN пути из локального `.venv`, если он есть):

```
python main.py meeting.mp4
```

## Аргументы

```
usage: main.py [-h] [--model MODEL] [--whisper-model WHISPER_MODEL] [--lang LANG] [--ollama-url OLLAMA_URL]
               [--force-audio] [--force-transcribe] [--force-summary] [--force]
               input

positional arguments:
  input                 Путь к видео- или аудиофайлу

options:
  -h, --help            show this help message and exit
  --model MODEL         Ollama-модель (по умолчанию: mistral-small3.1:24b)
  --whisper-model WHISPER_MODEL
                        Whisper-модель (по умолчанию: large-v3)
  --lang LANG           Язык аудио (ru, en, ...). По умолчанию — авто
  --ollama-url OLLAMA_URL
                        URL Ollama (по умолчанию: http://localhost:11434)
  --force-audio         Переконвертировать аудио даже если WAV уже есть
  --force-transcribe    Перетранскрибировать даже если transcript уже есть
  --force-summary       Переделать конспект даже если summary уже есть
  --force               Все этапы заново
```
