#!/bin/bash

# Ativar ambiente virtual
source venv/bin/activate

# Instalar Gunicorn se não estiver instalado
pip install gunicorn

# Exportar variáveis de ambiente necessárias
export KIVY_NO_ARGS=1
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Iniciar o Gunicorn com as configurações
gunicorn --config gunicorn.conf.py "src.questoespmp2.__main__:main()" 