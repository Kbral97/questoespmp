#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Generate Screen for PMP Questions Generator
"""

import os
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.scrollview import ScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.metrics import dp

from ..utils.file_utils import process_document

class BatchGenerateScreen(MDScreen):
    """Screen for generating questions in batch mode."""
    
    def __init__(self, **kwargs):
        """Initialize the batch generate screen."""
        super().__init__(**kwargs)
        self.dialogs = []
        self.selected_file = None
        self.file_manager = None
        self.difficulty_menu = None
        self.difficulties = ["Fácil", "Média", "Difícil"]
        self.selected_difficulty = "Média"
        self.build_ui()
        
    def on_pre_leave(self):
        """Close any open dialogs when leaving the screen."""
        for dialog in self.dialogs:
            if dialog:
                dialog.dismiss()
        self.dialogs = []
    
    def build_ui(self):
        """Build the user interface."""
        # Main layout
        main_layout = MDBoxLayout(orientation="vertical", padding=20, spacing=10)
        
        # Title
        title = MDLabel(
            text="Geração em Lote de Questões",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(title)
        
        # Instructions
        instructions = MDLabel(
            text="Selecione um arquivo para processar e gerar questões em lote.",
            font_style="Body1",
            halign="center",
            size_hint_y=None,
            height=40
        )
        main_layout.add_widget(instructions)
        
        # File handling layout
        file_layout = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None, height=150)
        
        # File selection buttons
        file_buttons_layout = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        
        # Select file button
        select_file_btn = MDRaisedButton(
            text="Selecionar Arquivo",
            size_hint_x=0.5,
            on_release=self.show_file_manager
        )
        file_buttons_layout.add_widget(select_file_btn)
        
        # Open document button
        open_doc_btn = MDRaisedButton(
            text="Visualizar Documento",
            size_hint_x=0.5,
            disabled=True,
            on_release=self.open_document
        )
        self.open_doc_btn = open_doc_btn
        file_buttons_layout.add_widget(open_doc_btn)
        
        file_layout.add_widget(file_buttons_layout)
        
        # Selected file display
        self.file_label = MDLabel(
            text="Nenhum arquivo selecionado",
            font_style="Body1",
            halign="center",
            size_hint_y=None,
            height=40
        )
        file_layout.add_widget(self.file_label)
        
        # Document type selection
        doc_type_layout = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        doc_type_layout.add_widget(MDLabel(text="Tipo de documento:", size_hint_x=0.4))
        
        doc_types_layout = MDBoxLayout(orientation="horizontal", spacing=5, size_hint_x=0.6)
        
        # PDF checkbox
        pdf_box = MDBoxLayout(orientation="horizontal", spacing=5)
        self.pdf_checkbox = MDCheckbox(active=True, size_hint=(None, None), size=(48, 48))
        pdf_box.add_widget(self.pdf_checkbox)
        pdf_box.add_widget(MDLabel(text="PDF", halign="left"))
        doc_types_layout.add_widget(pdf_box)
        
        # Word checkbox
        word_box = MDBoxLayout(orientation="horizontal", spacing=5)
        self.word_checkbox = MDCheckbox(active=True, size_hint=(None, None), size=(48, 48))
        word_box.add_widget(self.word_checkbox)
        word_box.add_widget(MDLabel(text="Word", halign="left"))
        doc_types_layout.add_widget(word_box)
        
        # Text checkbox
        text_box = MDBoxLayout(orientation="horizontal", spacing=5)
        self.text_checkbox = MDCheckbox(active=True, size_hint=(None, None), size=(48, 48))
        text_box.add_widget(self.text_checkbox)
        text_box.add_widget(MDLabel(text="Texto", halign="left"))
        doc_types_layout.add_widget(text_box)
        
        doc_type_layout.add_widget(doc_types_layout)
        file_layout.add_widget(doc_type_layout)
        
        main_layout.add_widget(file_layout)
        
        # Settings layout
        settings_layout = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None, height=200)
        
        # Number of questions
        num_questions_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        num_questions_layout.add_widget(MDLabel(text="Número de questões:", size_hint_x=0.4))
        self.num_questions = MDTextField(text="10", input_filter="int", size_hint_x=0.6)
        num_questions_layout.add_widget(self.num_questions)
        settings_layout.add_widget(num_questions_layout)
        
        # Difficulty selection
        difficulty_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        difficulty_layout.add_widget(MDLabel(text="Dificuldade:", size_hint_x=0.4))
        self.difficulty_button = MDRaisedButton(
            text=self.selected_difficulty,
            size_hint_x=0.6,
            on_release=self.show_difficulty_menu
        )
        difficulty_layout.add_widget(self.difficulty_button)
        settings_layout.add_widget(difficulty_layout)
        
        # Knowledge area
        knowledge_area_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        knowledge_area_layout.add_widget(MDLabel(text="Área de conhecimento:", size_hint_x=0.4))
        self.knowledge_area = MDTextField(hint_text="Opcional", size_hint_x=0.6)
        knowledge_area_layout.add_widget(self.knowledge_area)
        settings_layout.add_widget(knowledge_area_layout)
        
        # Tags
        tags_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        tags_layout.add_widget(MDLabel(text="Tags (separadas por vírgula):", size_hint_x=0.4))
        self.tags = MDTextField(hint_text="Opcional", size_hint_x=0.6)
        tags_layout.add_widget(self.tags)
        settings_layout.add_widget(tags_layout)
        
        main_layout.add_widget(settings_layout)
        
        # Generate button
        generate_btn = MDRaisedButton(
            text="Gerar Questões",
            size_hint=(1, None),
            height=50,
            on_release=self.generate_questions
        )
        main_layout.add_widget(generate_btn)
        
        # Back button
        back_btn = MDFlatButton(
            text="Voltar",
            size_hint=(1, None),
            height=50,
            on_release=lambda x: self.go_back()
        )
        main_layout.add_widget(back_btn)
        
        self.add_widget(main_layout)
        
    def show_file_manager(self, instance):
        """Show file manager to select a file."""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_file_manager,
                select_path=self.select_file,
                preview=False,
                selector="file",
                search="all",
                ext=[".pdf", ".docx", ".doc", ".txt"]
            )
        
        # Set initial path to the user's documents folder
        if os.name == 'nt':  # Windows
            initial_path = os.path.join(os.path.expanduser('~'), 'Documents')
        else:  # Linux/Mac
            initial_path = os.path.expanduser('~')
            
        # Make sure the path exists
        if not os.path.exists(initial_path):
            initial_path = os.path.expanduser('~')
            
        self.file_manager.show(initial_path)
    
    def exit_file_manager(self, *args):
        """Close the file manager."""
        if self.file_manager:
            self.file_manager.close()
    
    def select_file(self, path):
        """Handle file selection from file manager."""
        self.selected_file = path
        self.file_label.text = os.path.basename(path)
        self.open_doc_btn.disabled = False
        self.exit_file_manager()
    
    def open_document(self, instance):
        """Open the selected document."""
        if not self.selected_file:
            return
        
        # Open file with default application
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.selected_file)
            elif os.name == 'posix':  # Linux/Mac
                import subprocess
                subprocess.call(('xdg-open', self.selected_file))
        except Exception as e:
            self.show_error_dialog(f"Erro ao abrir o arquivo: {e}")
    
    def show_difficulty_menu(self, button):
        """Show difficulty selection menu."""
        if not self.difficulty_menu:
            menu_items = [
                {
                    "text": difficulty,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x=difficulty: self.select_difficulty(x),
                } for difficulty in self.difficulties
            ]
            self.difficulty_menu = MDDropdownMenu(
                caller=button,
                items=menu_items,
                width_mult=4,
            )
        self.difficulty_menu.open()
    
    def select_difficulty(self, difficulty):
        """Select difficulty level."""
        self.selected_difficulty = difficulty
        self.difficulty_button.text = difficulty
        if self.difficulty_menu:
            self.difficulty_menu.dismiss()
    
    def generate_questions(self, instance):
        """Generate questions in batch."""
        if not self.selected_file:
            self.show_error_dialog("Por favor, selecione um arquivo antes de gerar questões.")
            return
        
        try:
            # Get number of questions
            num_questions = int(self.num_questions.text)
            if num_questions <= 0:
                self.show_error_dialog("O número de questões deve ser maior que zero.")
                return
                
            # Process document and generate questions
            app = MDApp.get_running_app()
            
            # Show processing dialog
            processing_dialog = MDDialog(
                title="Processando",
                text="Processando documento e gerando questões...",
                size_hint=(0.8, 0.4)
            )
            self.dialogs.append(processing_dialog)
            processing_dialog.open()
            
            # Process the document
            try:
                document_text = process_document(
                    self.selected_file, 
                    pdf_enabled=self.pdf_checkbox.active,
                    word_enabled=self.word_checkbox.active,
                    text_enabled=self.text_checkbox.active
                )
                
                # Generate questions (mock implementation for now)
                # In a real implementation, this would call the API to generate questions
                # based on the document text, difficulty, etc.
                
                # Close processing dialog
                processing_dialog.dismiss()
                self.dialogs.remove(processing_dialog)
                
                # Show success dialog
                success_dialog = MDDialog(
                    title="Sucesso",
                    text=f"{num_questions} questões foram geradas com sucesso!",
                    buttons=[
                        MDFlatButton(
                            text="OK",
                            on_release=lambda x: success_dialog.dismiss()
                        )
                    ],
                    size_hint=(0.8, 0.4)
                )
                self.dialogs.append(success_dialog)
                success_dialog.open()
                
            except Exception as e:
                processing_dialog.dismiss()
                self.dialogs.remove(processing_dialog)
                self.show_error_dialog(f"Erro ao processar o documento: {e}")
            
        except ValueError:
            self.show_error_dialog("Por favor, insira um número válido de questões.")
    
    def show_error_dialog(self, text):
        """Show error dialog."""
        error_dialog = MDDialog(
            title="Erro",
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: error_dialog.dismiss()
                )
            ],
            size_hint=(0.8, 0.4)
        )
        self.dialogs.append(error_dialog)
        error_dialog.open()
    
    def go_back(self):
        """Return to home screen."""
        MDApp.get_running_app().sm.current = "home" 