import os
import multiprocessing

# Configurar PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, 'app')
os.environ['PYTHONPATH'] = f"{current_dir}:{app_dir}"

# Configurações do Kivy para modo headless
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ['KIVY_NO_FILELOG'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_BCM_DISPMANX_ID'] = '0'
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_IMAGE'] = 'sdl2'
os.environ['KIVY_AUDIO'] = 'sdl2'
os.environ['KIVY_VIDEO'] = 'ffpyplayer'

# Desabilitar MTDev e configurar driver de entrada
os.environ['KIVY_INPUT'] = 'sdl2'
os.environ['KIVY_MTDEV'] = '0'
os.environ['KIVY_USE_INPUT'] = '1'
os.environ['KIVY_USE_MOUSE'] = '1'
os.environ['KIVY_USE_TOUCH'] = '0'

# Configuração básica
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 120
keepalive = 5

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

# Configurações do worker
worker_class = "gthread"
threads = 2

# Configurações de reload e debugging
reload = True
reload_engine = "auto"
spew = False
check_config = False

# Configurações do ambiente
raw_env = [
    f"PYTHONPATH={os.getcwd()}",
    "KIVY_NO_ARGS=1",
    "KIVY_NO_CONSOLELOG=1",
    "KIVY_NO_FILELOG=1",
    "KIVY_GL_BACKEND=sdl2",
    "KIVY_WINDOW=sdl2",
    "KIVY_IMAGE=sdl2",
    "KIVY_AUDIO=sdl2",
    "KIVY_VIDEO=ffpyplayer",
    "KIVY_INPUT=sdl2",
    "KIVY_MTDEV=0",
    "KIVY_USE_INPUT=1",
    "KIVY_USE_MOUSE=1",
    "KIVY_USE_TOUCH=0"
] 