from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from questoespmp2.utils.config_manager import ConfigManager

class ConfigScreen(MDScreen):
    """Initial configuration screen for API keys."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "config"
        self.config_manager = ConfigManager()
        self.setup_ui()
        
        # Load existing keys if any
        openai_key = self.config_manager.get_openai_key()
        gemini_key = self.config_manager.get_gemini_key()
        
        if openai_key:
            self.openai_key.text = openai_key
        if gemini_key:
            self.gemini_key.text = gemini_key
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20))
        
        # Title
        title = MDLabel(
            text="Configuração Inicial",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        layout.add_widget(title)
        
        # Description
        description = MDLabel(
            text="Por favor, insira suas chaves de API para continuar.",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        layout.add_widget(description)
        
        # Input Card
        input_card = MDCard(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(20),
            size_hint=(None, None),
            size=(dp(400), dp(250)),
            pos_hint={'center_x': 0.5}
        )
        
        # OpenAI API Key Input
        self.openai_key = MDTextField(
            hint_text="Chave da API OpenAI",
            helper_text="Digite sua chave da OpenAI",
            helper_text_mode="on_error",
            password=True,
            size_hint_x=None,
            width=dp(360)
        )
        input_card.add_widget(self.openai_key)
        
        # Gemini API Key Input
        self.gemini_key = MDTextField(
            hint_text="Chave da API Gemini",
            helper_text="Digite sua chave do Gemini",
            helper_text_mode="on_error",
            password=True,
            size_hint_x=None,
            width=dp(360)
        )
        input_card.add_widget(self.gemini_key)
        
        # Save Button
        save_button = MDRaisedButton(
            text="Salvar e Continuar",
            pos_hint={'center_x': 0.5},
            on_release=lambda x: self.save_config()
        )
        input_card.add_widget(save_button)
        
        layout.add_widget(input_card)
        self.add_widget(layout)
    
    def save_config(self):
        """Save API keys and continue to main screen."""
        openai_key = self.openai_key.text.strip()
        gemini_key = self.gemini_key.text.strip()
        
        if not openai_key:
            self.openai_key.error = True
            self.openai_key.helper_text = "A chave da OpenAI é obrigatória"
            return
        
        if not gemini_key:
            self.gemini_key.error = True
            self.gemini_key.helper_text = "A chave do Gemini é obrigatória"
            return
        
        # Save keys
        self.config_manager.save_openai_key(openai_key)
        self.config_manager.save_gemini_key(gemini_key)
        
        # Continue to main screen
        self.manager.current = 'home' 