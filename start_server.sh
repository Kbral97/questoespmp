#!/bin/bash

# Configurar variáveis de ambiente
export FLASK_APP=wsgi.py
export FLASK_ENV=production
export FLASK_DEBUG=0
export SECRET_KEY=questoespmp_secret_key_2024

# Ativar o ambiente virtual
    source venv/bin/activate

# Limpar cache do navegador (instruções)
echo "Para resolver problemas de CSRF, por favor:"
echo "1. Limpe o cache do seu navegador"
echo "2. Use uma janela anônima/privativa"
echo "3. Tente acessar novamente"

# Iniciar o servidor Flask
echo "Iniciando o servidor Flask..."
echo "O servidor estará disponível em: http://34.151.197.25:5000"
flask run --host=0.0.0.0 --port=5000 