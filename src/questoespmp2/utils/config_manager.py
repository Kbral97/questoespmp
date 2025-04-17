from pathlib import Path
import os
from dotenv import load_dotenv, set_key

class ConfigManager:
    """Manages application configuration and API keys."""
    
    def __init__(self):
        self.env_path = Path('.env')
        if not self.env_path.exists():
            self.env_path.touch()
        load_dotenv(self.env_path)
    
    def get_openai_key(self):
        """Get OpenAI API key."""
        return os.getenv('OPENAI_API_KEY')
    
    def get_gemini_key(self):
        """Get Gemini API key."""
        return os.getenv('GEMINI_API_KEY')
    
    def save_openai_key(self, key):
        """Save OpenAI API key."""
        set_key(self.env_path, 'OPENAI_API_KEY', key)
        os.environ['OPENAI_API_KEY'] = key
    
    def save_gemini_key(self, key):
        """Save Gemini API key."""
        set_key(self.env_path, 'GEMINI_API_KEY', key)
        os.environ['GEMINI_API_KEY'] = key
    
    def has_required_keys(self):
        """Check if all required API keys are set."""
        return bool(self.get_openai_key() and self.get_gemini_key())
    
    def set_api_key(self, key):
        """Set OpenAI API key."""
        self.save_openai_key(key) 