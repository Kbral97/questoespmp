#!/bin/bash

# Exportar variáveis de ambiente necessárias
export KIVY_NO_ARGS=1
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Iniciar o Gunicorn com as configurações
gunicorn --config gunicorn.conf.py "src.questoespmp2.__main__:main()" 