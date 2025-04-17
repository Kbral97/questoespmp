#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gerenciador de API para o aplicativo.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from ..database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class APIManager:
    """Gerenciador de API para o aplicativo."""
    
    def __init__(self):
        """Inicializa o gerenciador de API."""
        self.config_dir = os.path.join(os.path.expanduser('~'), '.questoespmp')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.models_file = os.path.join(self.config_dir, 'default_models.json')
        self._ensure_config_dir()
        # Load environment variables from .env file
        load_dotenv()
        # Inicializa o gerenciador de banco de dados
        self.db = DatabaseManager()
        
    def _ensure_config_dir(self):
        """Garante que o diretório de configuração existe."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
    def get_api_key(self) -> Optional[str]:
        """Retorna a chave da API do arquivo .env."""
        return os.getenv('OPENAI_API_KEY')
            
    def save_api_key(self, api_key: str):
        """Salva a chave da API no arquivo .env."""
        try:
            with open('.env', 'w') as f:
                f.write(f"OPENAI_API_KEY='{api_key}'\n")
            # Reload environment variables
            load_dotenv(override=True)
            logger.info("Chave da API salva com sucesso no arquivo .env")
        except Exception as e:
            logger.error(f"Erro ao salvar chave da API: {e}")
            raise
            
    def clear_api_key(self):
        """Remove a chave da API do arquivo .env."""
        try:
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    lines = f.readlines()
                with open('.env', 'w') as f:
                    for line in lines:
                        if not line.startswith('OPENAI_API_KEY='):
                            f.write(line)
                # Reload environment variables
                load_dotenv(override=True)
                logger.info("Chave da API removida com sucesso do arquivo .env")
        except Exception as e:
            logger.error(f"Erro ao remover chave da API: {e}")
            raise
    
    def get_default_models(self) -> Dict[str, str]:
        """Retorna os modelos padrão salvos."""
        try:
            if os.path.exists(self.models_file):
                with open(self.models_file, 'r') as f:
                    models = json.load(f)
                    return models
            return {
                'question': None,
                'answer': None,
                'wrong_answers': None
            }
        except Exception as e:
            logger.error(f"Erro ao ler modelos padrão: {e}")
            return {
                'question': None,
                'answer': None,
                'wrong_answers': None
            }
    
    def save_default_models(self, models: Dict[str, Any]):
        """Salva os modelos padrão."""
        try:
            with open(self.models_file, 'w') as f:
                json.dump(models, f)
            
            logger.info("Modelos padrão salvos com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao salvar modelos padrão: {e}")
            raise
    
    def clear_default_models(self):
        """Remove os modelos padrão salvos."""
        try:
            if os.path.exists(self.models_file):
                os.remove(self.models_file)
                logger.info("Modelos padrão removidos com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao remover modelos padrão: {e}")
            raise 