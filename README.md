usage: main.py [-h] [--model MODEL] [--whisper-model WHISPER_MODEL] [--lang LANG] [--ollama-url OLLAMA_URL]
               [--force-audio] [--force-transcribe] [--force-summary] [--force]
               input

Видео/Аудио → WAV → транскрипция (Whisper) → конспект (Ollama) Поддерживаемые форматы: .aac, .avi, .flac, .m2ts, .m4a,
.mkv, .mov, .mp3, .mp4, .ogg, .opus, .ts, .wav, .webm, .wma Каждый этап кешируется, повторный запуск пропускает
готовые.

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
