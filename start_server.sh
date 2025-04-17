#!/bin/bash

# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências do sistema
sudo apt-get update
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
sudo apt-get install -y libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev

# Instalar Gunicorn se não estiver instalado
pip install gunicorn

# Exportar variáveis de ambiente necessárias
export KIVY_NO_ARGS=1
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Iniciar o Gunicorn com as configurações
gunicorn --config gunicorn.conf.py "src.questoespmp2.__main__:main()" 