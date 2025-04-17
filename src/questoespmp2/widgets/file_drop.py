#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Widget para arrastar e soltar arquivos.
"""

import os
import logging
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivymd.uix.label import MDLabel
from kivymd.uix.chip import MDChip
from kivymd.uix.scrollview import MDScrollView
from kivy.event import EventDispatcher

logger = logging.getLogger(__name__)

class FileDropWidget(BoxLayout, EventDispatcher):
    """Widget para arrastar e soltar arquivos."""
    
    allowed_extensions = ListProperty(['.csv', '.txt', '.pdf', '.docx'])
    selected_files = ListProperty([])
    on_file_selected = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        """Inicializa o widget."""
        super(FileDropWidget, self).__init__(**kwargs)
        self.register_event_type('on_file_selected')
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)
        
        # Configura o fundo do widget
        with self.canvas.before:
            Color(0.9, 0.9, 0.9, 1)  # Cinza claro
            self.rect = Rectangle(pos=self.pos, size=self.size)
            
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # Ao invés de usar um ícone, criar um placeholder colorido
        icon_layout = BoxLayout(
            size_hint=(None, None),
            size=(dp(64), dp(64)),
            pos_hint={'center_x': 0.5}
        )
        with icon_layout.canvas:
            Color(0.2, 0.6, 0.8, 1)  # Azul
            Rectangle(pos=icon_layout.pos, size=icon_layout.size)
            
        self.add_widget(icon_layout)
        
        # Adiciona texto de instrução
        self.instruction_label = MDLabel(
            text='Arraste e solte arquivos aqui\nou clique para selecionar\n(Você pode adicionar vários arquivos)',
            font_size=dp(18),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=dp(70)
        )
        self.add_widget(self.instruction_label)
        
        # Scroll view para os chips de arquivos
        scroll = MDScrollView(
            size_hint_y=None,
            height=dp(50)
        )
        self.files_layout = BoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            spacing=dp(5),
            padding=dp(5)
        )
        self.files_layout.bind(minimum_width=self.files_layout.setter('width'))
        scroll.add_widget(self.files_layout)
        self.add_widget(scroll)
        
        # Adiciona texto de status
        self.status_label = MDLabel(
            text='Formatos suportados: ' + ', '.join(self.allowed_extensions),
            font_size=dp(14),
            theme_text_color="Secondary",
            halign='center',
            valign='bottom',
            size_hint_y=None,
            height=dp(30)
        )
        self.add_widget(self.status_label)
        
        # Registra o evento de soltar arquivo
        Window.bind(on_drop_file=self._on_drop_file)
        
    def on_file_selected(self, *args):
        """Evento padrão para quando arquivos são selecionados."""
        pass
        
    def _update_rect(self, instance, value):
        """Atualiza o retângulo de fundo."""
        self.rect.pos = self.pos
        self.rect.size = self.size
        
    def _add_file_chip(self, file_path):
        """Adiciona um chip representando um arquivo."""
        chip = MDChip(
            text=os.path.basename(file_path),
            icon_right="close",
            size_hint=(None, None),
            height=dp(30)
        )
        chip.file_path = file_path
        chip.bind(on_release=lambda x: self._remove_file(file_path))
        self.files_layout.add_widget(chip)
        
    def _remove_file(self, file_path):
        """Remove um arquivo da lista."""
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            # Remove o chip correspondente
            for child in self.files_layout.children[:]:
                if hasattr(child, 'file_path') and child.file_path == file_path:
                    self.files_layout.remove_widget(child)
            self._update_status()
            
            # Dispara o evento
            self.dispatch('on_file_selected', self.selected_files)
            logger.info(f"Arquivo removido: {file_path}")
        
    def _update_status(self):
        """Atualiza o texto de status."""
        if not self.selected_files:
            self.status_label.text = 'Formatos suportados: ' + ', '.join(self.allowed_extensions)
            self.status_label.theme_text_color = "Secondary"
        else:
            self.status_label.text = f'{len(self.selected_files)} arquivo(s) selecionado(s)'
            self.status_label.theme_text_color = "Primary"
        
    def _on_drop_file(self, window, file_path, x, y):
        """Manipula o evento de soltar arquivo."""
        # Converte as coordenadas para coordenadas relativas ao widget
        widget_x = x - self.x
        widget_y = y - self.y
        
        # Verifica se o ponto está dentro do widget
        if not (0 <= widget_x <= self.width and 0 <= widget_y <= self.height):
            logger.info("Arquivo solto fora do widget")
            return False
            
        try:
            # Converte o caminho do arquivo de bytes para string
            file_path_str = file_path.decode('utf-8')
            logger.info(f"Arquivo recebido: {file_path_str}")
            
            # Obtém a extensão do arquivo
            _, ext = os.path.splitext(file_path_str)
            logger.info(f"Extensão do arquivo: {ext}")
            
            # Verifica se a extensão é permitida
            if ext.lower() not in self.allowed_extensions:
                logger.warning(f"Formato não suportado: {ext}")
                self.status_label.text = f'Formato não suportado: {ext}'
                self.status_label.theme_text_color = "Error"
                return False
                
            # Verifica se o arquivo já foi adicionado
            if file_path_str in self.selected_files:
                logger.warning(f"Arquivo já adicionado: {os.path.basename(file_path_str)}")
                self.status_label.text = f'Arquivo já adicionado: {os.path.basename(file_path_str)}'
                self.status_label.theme_text_color = "Error"
                return False
                
            # Adiciona o arquivo à lista
            self.selected_files.append(file_path_str)
            logger.info(f"Arquivo adicionado à lista: {file_path_str}")
            logger.info(f"Total de arquivos selecionados: {len(self.selected_files)}")
            
            self._add_file_chip(file_path_str)
            self._update_status()
            
            # Dispara o evento
            self.dispatch('on_file_selected', self.selected_files)
            logger.info("Evento on_file_selected disparado")
                
            return True
        
        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {e}")
            self.status_label.text = f'Erro: {str(e)}'
            self.status_label.theme_text_color = "Error"
            return False 