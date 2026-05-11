$base = "C:\Users\Ondosh\PycharmProjects\LLM-Audio\.venv\Lib\site-packages\nvidia"
$env:PATH = "$base\cublas\bin;$base\cudnn\bin;$base\cuda_runtime\bin;$base\cuda_nvrtc\bin;" + $env:PATH

.venv\Scripts\python.exe main.py $args