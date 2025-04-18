#!/bin/bash

# Configurar diretório base
BASE_DIR=$(pwd)
echo "Diretório base: $BASE_DIR"

# Ativar ambiente virtual
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Ambiente virtual ativado"
else
    echo "Criando ambiente virtual..."
    python -m venv venv
    source venv/bin/activate
    echo "Ambiente virtual criado e ativado"
fi

# Instalar dependências do sistema
echo "Instalando dependências do sistema..."
sudo apt-get update
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
sudo apt-get install -y libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev
sudo apt-get install -y libsdl2-gfx-dev libsdl2-net-dev

# Instalar dependências Python
echo "Instalando dependências Python..."
pip install -r requirements.txt
pip install gunicorn

# Configurar PYTHONPATH
export PYTHONPATH="$BASE_DIR:$BASE_DIR/app"
echo "PYTHONPATH configurado: $PYTHONPATH"

# Verificar estrutura do projeto
echo "Verificando estrutura do projeto..."
echo "Conteúdo do diretório base:"
ls -la
echo "Conteúdo do diretório app:"
ls -la app/
echo "Conteúdo do diretório database:"
ls -la app/database/

# Verificar Python path
echo "Python path atual:"
python -c "import sys; print('\n'.join(sys.path))"

# Testar importação do módulo
echo "Testando importação do módulo:"
python -c "import app.database.db_manager; print('Importação bem-sucedida')"

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

# Iniciar o servidor Gunicorn
echo "Iniciando servidor Gunicorn..."
gunicorn --config gunicorn.conf.py wsgi:app 