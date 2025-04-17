#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the PMP Questions Generator application.
"""

import os
import sys
import logging
from kivymd.app import MDApp

from questoespmp2.utils.api_manager import APIManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Definir variável de ambiente para o Kivy antes de qualquer import
os.environ['KIVY_NO_ARGS'] = '1'

def create_app():
    """Create and return the application instance."""
    try:
        # Initialize API manager
        api_manager = APIManager()
        
        # Check if API key exists
        if not api_manager.get_api_key():
            print("Aviso: Chave da API não encontrada. Configure-a no aplicativo.")
            
        # Create and return the application
        return MDApp()
        
    except Exception as e:
        logging.error(f"Erro ao criar aplicativo: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    app = create_app()
    app.run()

if __name__ == '__main__':
    main() 