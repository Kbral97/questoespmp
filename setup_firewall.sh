#!/bin/bash

# Verifica se o script está sendo executado como root
if [ "$EUID" -ne 0 ]; then 
    echo "Por favor, execute este script como root (sudo)"
    exit 1
fi

# Verifica se o ufw está instalado
if ! command -v ufw &> /dev/null; then
    echo "Instalando ufw..."
    apt-get update
    apt-get install -y ufw
fi

# Verifica se o ufw está ativo
if ! ufw status | grep -q "Status: active"; then
    echo "Ativando ufw..."
    ufw enable
fi

# Libera a porta 5000
echo "Liberando a porta 5000..."
ufw allow 5000/tcp

# Mostra o status do firewall
echo "Status do firewall:"
ufw status

echo "Configuração concluída. O servidor Flask deve estar acessível em http://35.198.33.190:5000" 