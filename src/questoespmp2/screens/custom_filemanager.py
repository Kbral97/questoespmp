#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gerenciador de arquivos personalizado com ícones menores
"""

from kivymd.uix.filemanager import MDFileManager
from kivy.metrics import dp
from kivy.lang import Builder

# Definindo um estilo personalizado para o gerenciador de arquivos
Builder.load_string('''
<CustomFileManager>:
    MDBoxLayout:
        orientation: 'vertical'
        
        MDToolbar:
            title: root.current_path
            elevation: 10
            left_action_items: [['arrow-left', lambda x: root.back()]]
            right_action_items: [['close', lambda x: root.exit_manager()]]
            
        RecycleView:
            id: rv
            key_viewclass: 'viewclass'
            key_size: 'height'
            bar_width: dp(4)
            bar_color: app.theme_cls.primary_color
            
            RecycleBoxLayout:
                padding: dp(10)
                spacing: dp(10)
                default_size: None, dp(48)  # Altura reduzida para 48dp (era 72dp)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
''')

class CustomFileManager(MDFileManager):
    """
    Gerenciador de arquivos personalizado com ícones menores.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Todas as configurações são herdadas da classe base, apenas o estilo é personalizado 