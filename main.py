#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para executar o aplicativo.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point."""
    try:
        # Adiciona o diretório src ao PYTHONPATH
        src_dir = os.path.join(os.path.dirname(__file__), 'src')
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            
        # Importa e executa o aplicativo
        from questoespmp2 import PMPApp
        app = PMPApp()
        app.run()
        
    except Exception as e:
        logging.error(f"Erro ao iniciar aplicativo: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 