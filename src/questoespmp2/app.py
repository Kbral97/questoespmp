#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main application file for PMP Questions Generator.
"""

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivy.core.window import Window
from kivy.metrics import dp

from questoespmp2.screens.home_screen import HomeScreen
from questoespmp2.screens.generate_screen import GenerateScreen
from questoespmp2.screens.answer_question_screen import AnswerQuestionScreen
from questoespmp2.screens.stats_screen import StatsScreen
from questoespmp2.screens.docs_screen import DocsScreen
from questoespmp2.screens.tuning_screen import TuningScreen
from questoespmp2.screens.model_select_screen import ModelSelectScreen
from questoespmp2.utils.api_manager import APIManager

class PMPApp(MDApp):
    """Main application class."""
    
    def __init__(self, **kwargs):
        """Initialize the application."""
        super().__init__(**kwargs)
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        
        # Set window size
        Window.size = (800, 600)
        Window.minimum_width, Window.minimum_height = 100, 100  # Set to positive values
        
        # Initialize API manager
        self.api_manager = APIManager()
        
    def build(self):
        """Build the application."""
        # Create screen manager
        self.sm = MDScreenManager()
        
        # Add screens
        self.sm.add_widget(HomeScreen(name='home'))
        self.sm.add_widget(GenerateScreen(name='generate'))
        self.sm.add_widget(AnswerQuestionScreen(name='answer_question'))
        self.sm.add_widget(StatsScreen(name='stats'))
        self.sm.add_widget(DocsScreen(name='docs'))
        self.sm.add_widget(TuningScreen(name='tuning'))
        self.sm.add_widget(ModelSelectScreen(name='model_select'))
        
        return self.sm
        
    def on_start(self):
        """Called when the application starts."""
        # Load saved API key if exists
        saved_key = self.api_manager.get_api_key()
        if saved_key:
            self.api_key = saved_key
            
    def save_api_key(self, api_key: str):
        """Save API key."""
        self.api_manager.save_api_key(api_key)
        
    def clear_api_key(self):
        """Clear saved API key."""
        self.api_manager.clear_api_key()
        
if __name__ == '__main__':
    PMPApp().run() 