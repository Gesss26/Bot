# gunicorn.conf.py
# Configurazione Gunicorn per Render
# Aumenta il timeout per permettere il parsing dei PDF (lento)

import multiprocessing

# Timeout richieste in secondi (default 30 → troppo basso per PDF)
timeout = 300

# Graceful timeout
graceful_timeout = 60

# Keep-alive
keepalive = 5

# Numero di worker (1 basta per un bot Telegram)
workers = 1

# Thread per worker (utile per I/O)
threads = 2

# Log
loglevel = 'info'
accesslog = '-'
errorlog = '-'