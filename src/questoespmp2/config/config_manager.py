"""
Configuration manager for the application
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return {}
        return {}
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get_api_key(self):
        """Get the OpenAI API key."""
        return self.config.get('api_key')
    
    def set_api_key(self, api_key):
        """Set the OpenAI API key."""
        self.config['api_key'] = api_key
        self._save_config()
    
    def get_model_name(self):
        """Get the model name for fine-tuning."""
        return self.config.get('model_name', 'gpt-3.5-turbo')
    
    def set_model_name(self, model_name):
        """Set the model name for fine-tuning."""
        self.config['model_name'] = model_name
        self._save_config()
    
    def get_fine_tuned_model(self):
        """Get the fine-tuned model ID."""
        return self.config.get('fine_tuned_model')
    
    def set_fine_tuned_model(self, model_id):
        """Set the fine-tuned model ID."""
        self.config['fine_tuned_model'] = model_id
        self._save_config()
    
    def get_last_job_id(self):
        """Get the last fine-tuning job ID."""
        return self.config.get('last_job_id')
    
    def set_last_job_id(self, job_id):
        """Set the last fine-tuning job ID."""
        self.config['last_job_id'] = job_id
        self._save_config() 