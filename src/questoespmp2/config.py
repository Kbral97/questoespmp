import os
import json
import logging
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        """
        Inicializa o objeto de configuração.
        """
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        self._load_config()
    
    def _load_config(self):
        """
        Carrega as configurações do arquivo.
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = self._get_default_config()
                self._save_config()
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {str(e)}")
            self.config = self._get_default_config()
    
    def _save_config(self):
        """
        Salva as configurações no arquivo.
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {str(e)}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Retorna as configurações padrão.
        
        Returns:
            Dicionário com as configurações padrão
        """
        return {
            "models": {
                "question_model": {
                    "name": "gpt-3.5-turbo",
                    "temperature": 0.8,
                    "max_tokens": 200
                },
                "answer_model": {
                    "name": "gpt-3.5-turbo",
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                "wrong_answers_model": {
                    "name": "gpt-3.5-turbo",
                    "temperature": 0.5,
                    "max_tokens": 300
                }
            },
            "database": {
                "path": "data/questions.json"
            },
            "api": {
                "timeout": 30,
                "retries": 3
            }
        }
    
    def get_model(self, model_key: str) -> Dict[str, Any]:
        """
        Obtém as configurações de um modelo específico.
        
        Args:
            model_key: Chave do modelo
            
        Returns:
            Dicionário com as configurações do modelo
        """
        return self.config.get("models", {}).get(model_key, {})
    
    def get_database_path(self) -> str:
        """
        Obtém o caminho do banco de dados.
        
        Returns:
            Caminho do banco de dados
        """
        return self.config.get("database", {}).get("path", "data/questions.json")
    
    def get_api_timeout(self) -> int:
        """
        Obtém o timeout da API.
        
        Returns:
            Timeout em segundos
        """
        return self.config.get("api", {}).get("timeout", 30)
    
    def get_api_retries(self) -> int:
        """
        Obtém o número de tentativas da API.
        
        Returns:
            Número de tentativas
        """
        return self.config.get("api", {}).get("retries", 3)
    
    def update_model_config(self, model_key: str, config: Dict[str, Any]):
        """
        Atualiza as configurações de um modelo.
        
        Args:
            model_key: Chave do modelo
            config: Novas configurações
        """
        if "models" not in self.config:
            self.config["models"] = {}
        self.config["models"][model_key] = config
        self._save_config()
    
    def update_database_path(self, path: str):
        """
        Atualiza o caminho do banco de dados.
        
        Args:
            path: Novo caminho
        """
        if "database" not in self.config:
            self.config["database"] = {}
        self.config["database"]["path"] = path
        self._save_config()
    
    def update_api_config(self, timeout: int = None, retries: int = None):
        """
        Atualiza as configurações da API.
        
        Args:
            timeout: Novo timeout em segundos
            retries: Novo número de tentativas
        """
        if "api" not in self.config:
            self.config["api"] = {}
        if timeout is not None:
            self.config["api"]["timeout"] = timeout
        if retries is not None:
            self.config["api"]["retries"] = retries
        self._save_config() 