import os
import sys

# Configurações para ambiente headless
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ['KIVY_NO_FILELOG'] = '1'
os.environ['KIVY_NO_CONFIG'] = '1'
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['DISPLAY'] = ':0'  # Necessário para alguns ambientes headless
os.environ['PYTHONUNBUFFERED'] = '1'  # Para melhor logging

# Configurações do Gunicorn
bind = "0.0.0.0:8000"
workers = 2  # Reduzido para ambiente virtual
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
loglevel = "info"
preload_app = True

# Configurações específicas para VM
worker_connections = 1000
worker_tmp_dir = "/dev/shm"  # Usa memória compartilhada
worker_class = "gevent"  # Usa gevent para melhor performance em VM 