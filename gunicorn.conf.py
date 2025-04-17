import os
import multiprocessing

# Definir variável de ambiente para o Kivy antes de qualquer import
os.environ['KIVY_NO_ARGS'] = '1'

# Configuração básica
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
timeout = 120
keepalive = 2

# Configuração de logs
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Configurações de segurança
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Configurações de performance
max_requests = 1000
max_requests_jitter = 50
worker_connections = 1000

# Configurações de graceful shutdown
graceful_timeout = 30
forwarded_allow_ips = "*" 