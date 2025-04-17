#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
QuestoesPMP - Sistema de geração e gerenciamento de questões para certificação PMP
"""

__version__ = '1.0.0'

from .app import PMPApp
from .screens.home_screen import HomeScreen
from .screens.generate_screen import GenerateScreen
from .screens.stats_screen import StatsScreen
from .screens.docs_screen import DocsScreen
from .screens.tuning_screen import TuningScreen

import os
from pathlib import Path

def ensure_data_directory():
    """Garante que o diretório de dados existe"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Inicializar arquivos se não existirem
    files = {
        "questions.json": "[]",
        "statistics.json": "{}",
        "training_data.json": "[]"
    }
    
    for filename, initial_content in files.items():
        file_path = data_dir / filename
        if not file_path.exists():
            file_path.write_text(initial_content)

# Garantir que o diretório de dados existe ao importar o módulo
ensure_data_directory()

__all__ = [
    'PMPApp',
    'HomeScreen',
    'GenerateScreen',
    'StatsScreen',
    'DocsScreen',
    'TuningScreen',
] 