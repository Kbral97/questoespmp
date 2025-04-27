#!/bin/bash

# Configurar variáveis de ambiente
export FLASK_APP=wsgi.py
export FLASK_ENV=production
export FLASK_DEBUG=0

# Ativar o ambiente virtual
source venv/bin/activate

# Iniciar o servidor Flask
echo "Iniciando o servidor Flask..."
echo "O servidor estará disponível em: http://35.198.33.190:5000"
flask run --host=0.0.0.0 --port=5000 