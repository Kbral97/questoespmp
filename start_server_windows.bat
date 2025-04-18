@echo off

REM Ativar ambiente virtual
call venv\Scripts\activate.bat

REM Configurar PYTHONPATH
set PYTHONPATH=%cd%;%PYTHONPATH%

REM Configurar variáveis de ambiente do Kivy
set KIVY_NO_ARGS=1
set KIVY_NO_CONSOLELOG=1
set KIVY_NO_FILELOG=1
set KIVY_GL_BACKEND=sdl2
set KIVY_WINDOW=sdl2
set KIVY_IMAGE=sdl2
set KIVY_AUDIO=sdl2
set KIVY_VIDEO=ffpyplayer
set KIVY_INPUT=sdl2
set KIVY_MTDEV=0
set KIVY_USE_INPUT=1
set KIVY_USE_MOUSE=1
set KIVY_USE_TOUCH=0

REM Iniciar o servidor Flask
python -m flask run --host=0.0.0.0 --port=8000 