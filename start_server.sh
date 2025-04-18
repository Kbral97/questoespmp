#!/bin/bash

# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências do sistema
sudo apt-get update
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
sudo apt-get install -y libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev
sudo apt-get install -y libsdl2-gfx-dev libsdl2-net-dev

# Instalar Gunicorn se não estiver instalado
pip install gunicorn

# Configurar PYTHONPATH corretamente
export PYTHONPATH=$(pwd):$PYTHONPATH
echo "PYTHONPATH: $PYTHONPATH"
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

# Configurar variáveis de ambiente do Kivy
export KIVY_NO_ARGS=1
export KIVY_NO_CONSOLELOG=1
export KIVY_NO_FILELOG=1
export KIVY_GL_BACKEND=sdl2
export KIVY_WINDOW=sdl2
export KIVY_IMAGE=sdl2
export KIVY_AUDIO=sdl2
export KIVY_VIDEO=ffpyplayer
export KIVY_INPUT=sdl2
export KIVY_MTDEV=0
export KIVY_USE_INPUT=1
export KIVY_USE_MOUSE=1
export KIVY_USE_TOUCH=0

# Iniciar o servidor Gunicorn com PYTHONPATH explícito
PYTHONPATH=$(pwd) gunicorn --config gunicorn.conf.py wsgi:app 