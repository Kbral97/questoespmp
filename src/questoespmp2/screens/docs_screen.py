#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tela para processamento de documentos que serão usados como base para as questões.
"""

import threading
import os
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.logger import Logger
from kivy.clock import Clock

from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.app import MDApp

from ..utils.text_processor import TextProcessor
from ..utils.api_manager import APIManager
from ..widgets.file_drop import FileDropWidget

import logging
logger = logging.getLogger(__name__)

class DocsScreen(MDScreen):
    """
    Tela para processamento de documentos.
    """
    
    def __init__(self, **kwargs):
        """Inicializa a tela."""
        super().__init__(**kwargs)
        self.name = "docs"
        self.api_manager = APIManager()
        self.text_processor = TextProcessor()
        self.selected_files = []  # Lista para armazenar múltiplos arquivos
        self.processing = False
        self.processing_thread = None
        self.progress = 0
        self.status_message = ""
        self.dialog = None
        self.file_manager = None
        
        self.setup_ui()
        
        logger.info("Tela de processamento de documentos inicializada")
        
    def setup_ui(self):
        """Set up the user interface."""
        layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        # Title
        title = MDLabel(
            text="Processamento de Documentos",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        layout.add_widget(title)
        
        # Descrição
        description = MDLabel(
            text="Use esta tela para processar documentos que serão usados como base para gerar questões.\nArraste e solte um arquivo ou use o botão para selecionar.",
            size_hint_y=None,
            height=dp(60)
        )
        layout.add_widget(description)
        
        # File Drop Area
        self.file_drop = FileDropWidget(
            size_hint_y=0.6,
            allowed_extensions=['.pdf', '.txt', '.docx']
        )
        self.file_drop.bind(on_file_selected=lambda instance, file_paths: self.on_file_selected(instance, file_paths))
        layout.add_widget(self.file_drop)
        
        # Status Label
        self.status_label = MDLabel(
            text="",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        layout.add_widget(self.status_label)
        
        # Progress Bar (initially hidden)
        self.progress_bar = MDProgressBar(
            size_hint_y=None,
            height=dp(10),
            value=0
        )
        layout.add_widget(self.progress_bar)
        
        # Spinner (initially hidden)
        self.spinner = MDSpinner(
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            pos_hint={'center_x': .5, 'center_y': .5},
            active=False
        )
        layout.add_widget(self.spinner)
        
        # Buttons Layout
        buttons_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10),
            pos_hint={'center_x': .5}
        )
        
        # File Select Button
        select_file_btn = MDRaisedButton(
            text="Selecionar Arquivo",
            on_release=self.show_file_manager,
            size_hint_x=0.5
        )
        buttons_layout.add_widget(select_file_btn)
        
        # Process Button
        self.process_button = MDRaisedButton(
            text="Processar",
            on_release=self.process_file,
            disabled=True,  # Começa desabilitado
            size_hint_x=0.5,
            md_bg_color=(0.7, 0.7, 0.7, 1)  # Começa cinza
        )
        logger.info("Botão de processamento inicializado")
        logger.info(f"Estado inicial do botão: disabled = {self.process_button.disabled}")
        
        buttons_layout.add_widget(self.process_button)
        layout.add_widget(buttons_layout)
        
        # Back button
        back_btn = MDRaisedButton(
            text="Voltar",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.go_back
        )
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
        logger.info("Interface configurada com sucesso")
        
    def show_file_manager(self, instance):
        """Mostra o gerenciador de arquivos."""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_file_manager,
                select_path=self.select_file,
                preview=False,
                ext=['.pdf', '.txt', '.docx']
            )
        
        # Set the initial path to Documents or Home
        initial_path = os.path.expanduser("~/Documents")
        if not os.path.exists(initial_path):
            initial_path = os.path.expanduser("~")
            
        self.file_manager.show(initial_path)
        
    def exit_file_manager(self, *args):
        """Fecha o gerenciador de arquivos."""
        self.file_manager.close()
        
    def select_file(self, path):
        """Seleciona um arquivo do gerenciador de arquivos."""
        self.exit_file_manager()
        self.on_file_selected(None, path)
        
    def on_file_selected(self, widget, file_paths):
        """Callback chamado quando arquivos são selecionados ou removidos."""
        # Log para debug
        logger.info("on_file_selected chamado")
        logger.info(f"Tipo de file_paths: {type(file_paths)}")
        logger.info(f"Conteúdo de file_paths: {file_paths}")
        
        # Atualiza a lista de arquivos selecionados
        self.selected_files = file_paths if isinstance(file_paths, list) else [file_paths]
        
        # Log para debug
        logger.info(f"self.selected_files atualizado: {self.selected_files}")
        
        # Atualiza o estado do botão de processamento
        has_files = bool(self.selected_files)
        logger.info(f"has_files: {has_files}")
        
        self.process_button.disabled = not has_files
        
        # Atualiza a cor do botão
        app = MDApp.get_running_app()
        if has_files:
            self.process_button.md_bg_color = app.theme_cls.primary_color
        else:
            self.process_button.md_bg_color = (0.7, 0.7, 0.7, 1)  # Gray
            
        # Atualiza o status
        if has_files:
            self.status_label.text = f"{len(self.selected_files)} arquivo(s) selecionado(s)"
        else:
            self.status_label.text = ""
            
        logger.info(f"Estado final do botão: disabled = {self.process_button.disabled}")
        
    def process_file(self, *args):
        """Processa os arquivos selecionados."""
        if not self.selected_files:  # Verifica a lista correta de arquivos
            self.show_error_dialog("Erro", "Nenhum arquivo selecionado.")
            return
            
        # Verificar as extensões dos arquivos
        invalid_files = []
        for file_path in self.selected_files:  # Usa a lista correta de arquivos
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in ['.pdf', '.txt', '.docx']:
                invalid_files.append(os.path.basename(file_path))
                
        if invalid_files:
            self.show_error_dialog(
                "Erro",
                "Formato(s) de arquivo não suportado(s):\n" + "\n".join(invalid_files)
            )
            return
            
        self.status_label.text = "Processando arquivos..."
        self.process_button.disabled = True
        self.process_button.md_bg_color = (0.7, 0.7, 0.7, 1)  # Gray
        self.progress_bar.value = 0
        self.spinner.active = True
        
        # Start processing in a separate thread
        self.processing = True
        self.processing_thread = threading.Thread(
            target=self.process_in_thread,
            args=(self.selected_files,)  # Usa a lista correta de arquivos
        )
        self.processing_thread.start()
        
        # Update progress periodically
        Clock.schedule_interval(self.update_progress, 0.1)
        
    def process_in_thread(self, file_paths):
        """Process files in a separate thread."""
        try:
            total_files = len(file_paths)
            total_chunks = 0
            
            for i, file_path in enumerate(file_paths, 1):
                try:
                    def progress_callback(progress):
                        """Callback function to update progress."""
                        # Calcula o progresso total considerando todos os arquivos
                        file_progress = (i - 1) * 100 + progress
                        total_progress = file_progress / total_files
                        self.progress = total_progress
                        
                        # Update message based on progress
                        if progress < 25:
                            self.status_message = f"Lendo arquivo {i}/{total_files}..."
                        elif progress < 50:
                            self.status_message = f"Dividindo texto em trechos... ({int(progress)}%) - Arquivo {i}/{total_files}"
                        elif progress < 75:
                            self.status_message = f"Processando trechos... ({int(progress)}%) - Arquivo {i}/{total_files}"
                        elif progress < 100:
                            self.status_message = f"Salvando resultados... ({int(progress)}%) - Arquivo {i}/{total_files}"
                        else:
                            self.status_message = f"Finalizando arquivo {i}/{total_files}..."
                        
                        # Log progress
                        logger.debug(f"Processing progress: {progress}% - {self.status_message}")
                    
                    # Process the file using text_processor
                    chunks = self.text_processor.process_file(
                        file_path,
                        progress_callback=progress_callback
                    )
                    total_chunks += chunks
                    
                    # Log success
                    logger.info(f"Arquivo processado com sucesso: {file_path}")
                    logger.info(f"Trechos processados: {chunks}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar arquivo {file_path}: {e}")
                    self.status_message = f"Erro ao processar {os.path.basename(file_path)}: {str(e)}"
                    continue
            
            # Update final status
            self.status_message = f"Processamento concluído! {total_chunks} trechos processados de {total_files} arquivo(s)."
            self.progress = 100
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            self.status_message = f"Erro no processamento: {str(e)}"
            
        finally:
            self.processing = False
        
    def update_progress(self, dt):
        """Update progress bar and status message."""
        if not self.processing and self.progress >= 100:
            # Processing is finished
            self.progress_bar.value = 100
            self.status_label.text = self.status_message
            self.spinner.active = False
            
            # Show success message
            self.show_success_dialog(
                "Processamento Concluído",
                f"O arquivo foi processado com sucesso!"
            )
            
            # Unschedule this function
            return False
            
        if not self.processing and self.progress < 100:
            # Processing had an error
            self.status_label.text = self.status_message
            self.spinner.active = False
            
            # Show error message
            self.show_error_dialog(
                "Erro no Processamento",
                self.status_message
            )
            
            # Unschedule this function
            return False
            
        # Update progress bar
        self.progress_bar.value = self.progress
        
        # Update status message
        self.status_label.text = self.status_message
        
        # Continue updating
        return True
        
    def show_success_dialog(self, title, text):
        """Mostrar diálogo de sucesso."""
        if self.dialog:
            self.dialog.dismiss()
            
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()
        
    def show_error_dialog(self, title, text):
        """Mostrar diálogo de erro."""
        if self.dialog:
            self.dialog.dismiss()
            
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()
        
    def go_back(self, instance):
        """Volta para a tela inicial."""
        self.manager.current = 'home' 