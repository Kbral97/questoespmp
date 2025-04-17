#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Load Documents Screen for PMP Questions Generator
"""

import os
import time
import threading
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem, TwoLineListItem, MDList
from kivymd.uix.scrollview import ScrollView
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.progressbar import MDProgressBar
from kivy.metrics import dp

from ..utils.file_utils import process_document, save_document_to_temp, delete_temp_file

class LoadDocumentsScreen(MDScreen):
    """Screen for loading and managing documents."""
    
    def __init__(self, **kwargs):
        """Initialize the load documents screen."""
        super().__init__(**kwargs)
        self.dialogs = []
        self.file_manager = None
        self.selected_files = []
        self.document_list = []
        self.build_ui()
        
    def on_pre_leave(self):
        """Close any open dialogs when leaving the screen."""
        for dialog in self.dialogs:
            if dialog:
                dialog.dismiss()
        self.dialogs = []
    
    def on_pre_enter(self):
        """Load document list when entering the screen."""
        self.load_document_list()
    
    def build_ui(self):
        """Build the user interface."""
        # Main layout
        main_layout = MDBoxLayout(orientation="vertical", padding=20, spacing=10)
        
        # Title
        title = MDLabel(
            text="Gerenciador de Documentos",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(title)
        
        # Instructions
        instructions = MDLabel(
            text="Carregue e gerencie documentos para geração de questões.",
            font_style="Body1",
            halign="center",
            size_hint_y=None,
            height=40
        )
        main_layout.add_widget(instructions)
        
        # Add document button
        add_doc_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=50, spacing=10)
        
        add_doc_btn = MDRaisedButton(
            text="Adicionar Documento",
            size_hint_x=0.7,
            on_release=self.show_file_manager
        )
        add_doc_layout.add_widget(add_doc_btn)
        
        process_all_btn = MDRaisedButton(
            text="Processar Todos",
            size_hint_x=0.3,
            on_release=self.process_all_documents
        )
        add_doc_layout.add_widget(process_all_btn)
        
        main_layout.add_widget(add_doc_layout)
        
        # Document list
        list_title = MDLabel(
            text="Documentos Carregados:",
            font_style="Subtitle1",
            halign="left",
            size_hint_y=None,
            height=40
        )
        main_layout.add_widget(list_title)
        
        # Scroll view for document list
        scroll = ScrollView()
        self.doc_list = MDList()
        scroll.add_widget(self.doc_list)
        main_layout.add_widget(scroll)
        
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
        """Show file manager to select a document file."""
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
        self.exit_file_manager()
        
        # Check if file is supported
        file_ext = os.path.splitext(path)[1].lower()
        supported_extensions = ['.pdf', '.docx', '.doc', '.txt', '.rtf']
        
        if file_ext not in supported_extensions:
            self.show_error_dialog(f"Formato de arquivo não suportado. Formatos suportados: {', '.join(supported_extensions)}")
            return
        
        # Add file to list
        self.add_document_to_list(path)
        
        # Ask if user wants to process the document now
        self.show_process_dialog(path)
    
    def add_document_to_list(self, path):
        """Add document to the list."""
        filename = os.path.basename(path)
        file_ext = os.path.splitext(filename)[1].lower()
        file_type = "PDF" if file_ext == '.pdf' else "Word" if file_ext in ['.doc', '.docx'] else "Texto"
        
        # Check if file is already in the list
        for doc in self.document_list:
            if doc['path'] == path:
                self.show_error_dialog("Este documento já foi adicionado.")
                return
        
        # Add to document list
        doc_info = {
            'name': filename,
            'path': path,
            'type': file_type,
            'processed': False
        }
        self.document_list.append(doc_info)
        
        # Add to UI list
        self.update_document_list_ui()
    
    def update_document_list_ui(self):
        """Update the document list in the UI."""
        self.doc_list.clear_widgets()
        
        if not self.document_list:
            no_docs = OneLineListItem(text="Nenhum documento carregado")
            self.doc_list.add_widget(no_docs)
            return
        
        for i, doc in enumerate(self.document_list):
            item = TwoLineListItem(
                text=doc['name'],
                secondary_text=f"Tipo: {doc['type']} | Status: {'Processado' if doc['processed'] else 'Não processado'}",
                on_release=lambda x, doc_idx=i: self.show_document_options(doc_idx)
            )
            self.doc_list.add_widget(item)
    
    def show_document_options(self, doc_index):
        """Show options for the selected document."""
        doc = self.document_list[doc_index]
        
        options_dialog = MDDialog(
            title=doc['name'],
            text=f"Tipo: {doc['type']} | Status: {'Processado' if doc['processed'] else 'Não processado'}",
            buttons=[
                MDFlatButton(
                    text="Fechar",
                    on_release=lambda x: options_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Abrir",
                    on_release=lambda x: (options_dialog.dismiss(), self.open_document(doc['path']))
                ),
                MDRaisedButton(
                    text="Processar",
                    on_release=lambda x: (options_dialog.dismiss(), self.process_document(doc_index))
                ),
                MDFlatButton(
                    text="Remover",
                    on_release=lambda x: (options_dialog.dismiss(), self.remove_document(doc_index))
                )
            ],
            size_hint=(0.8, None)
        )
        self.dialogs.append(options_dialog)
        options_dialog.open()
    
    def open_document(self, path):
        """Open the document with the default application."""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # Linux/Mac
                import subprocess
                subprocess.call(('xdg-open', path))
        except Exception as e:
            self.show_error_dialog(f"Erro ao abrir o documento: {e}")
    
    def process_document(self, doc_index):
        """Process the selected document."""
        doc = self.document_list[doc_index]
        
        # Show processing dialog
        processing_dialog = MDDialog(
            title="Processando",
            text=f"Processando documento: {doc['name']}...",
            size_hint=(0.8, None)
        )
        self.dialogs.append(processing_dialog)
        processing_dialog.open()
        
        try:
            # Determine document type
            is_pdf = doc['type'] == "PDF"
            is_word = doc['type'] == "Word"
            is_text = doc['type'] == "Texto"
            
            # Process document
            processed_text = process_document(
                doc['path'],
                is_pdf=is_pdf,
                is_word=is_word,
                is_text=is_text
            )
            
            # Update document status
            self.document_list[doc_index]['processed'] = True
            self.update_document_list_ui()
            
            # Close processing dialog
            processing_dialog.dismiss()
            self.dialogs.remove(processing_dialog)
            
            # Show success dialog
            success_dialog = MDDialog(
                title="Sucesso",
                text=f"Documento processado com sucesso!\nTextual content: {len(processed_text)} caracteres",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: success_dialog.dismiss()
                    ),
                    MDRaisedButton(
                        text="Gerar Questões",
                        on_release=lambda x: (success_dialog.dismiss(), self.go_to_generate_questions(processed_text))
                    )
                ],
                size_hint=(0.8, None)
            )
            self.dialogs.append(success_dialog)
            success_dialog.open()
            
        except Exception as e:
            # Close processing dialog
            processing_dialog.dismiss()
            self.dialogs.remove(processing_dialog)
            
            # Show error dialog
            self.show_error_dialog(f"Erro ao processar o documento: {e}")
    
    def remove_document(self, doc_index):
        """Remove document from the list."""
        self.document_list.pop(doc_index)
        self.update_document_list_ui()
    
    def process_all_documents(self, instance):
        """Process all unprocessed documents."""
        unprocessed = [doc for doc in self.document_list if not doc['processed']]
        
        if not unprocessed:
            self.show_error_dialog("Todos os documentos já foram processados.")
            return
        
        # Confirm with user
        confirm_dialog = MDDialog(
            title="Processar Todos",
            text=f"Deseja processar {len(unprocessed)} documentos não processados?",
            buttons=[
                MDFlatButton(
                    text="Cancelar",
                    on_release=lambda x: confirm_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Processar",
                    on_release=lambda x: (confirm_dialog.dismiss(), self.execute_process_all())
                )
            ],
            size_hint=(0.8, None)
        )
        self.dialogs.append(confirm_dialog)
        confirm_dialog.open()
    
    def execute_process_all(self):
        """Execute processing of all unprocessed documents."""
        # Show processing dialog
        processing_dialog = MDDialog(
            title="Processando",
            text="Processando documentos...",
            size_hint=(0.8, None)
        )
        self.dialogs.append(processing_dialog)
        processing_dialog.open()
        
        # Process each document
        processed_count = 0
        errors = []
        
        for i, doc in enumerate(self.document_list):
            if not doc['processed']:
                try:
                    # Determine document type
                    is_pdf = doc['type'] == "PDF"
                    is_word = doc['type'] == "Word"
                    is_text = doc['type'] == "Texto"
                    
                    # Process document
                    process_document(
                        doc['path'],
                        is_pdf=is_pdf,
                        is_word=is_word,
                        is_text=is_text
                    )
                    
                    # Update document status
                    self.document_list[i]['processed'] = True
                    processed_count += 1
                    
                except Exception as e:
                    errors.append(f"{doc['name']}: {str(e)}")
        
        # Update UI
        self.update_document_list_ui()
        
        # Close processing dialog
        processing_dialog.dismiss()
        self.dialogs.remove(processing_dialog)
        
        # Show results
        if errors:
            error_text = "Alguns documentos não puderam ser processados:\n" + "\n".join(errors)
            self.show_error_dialog(error_text)
        else:
            success_dialog = MDDialog(
                title="Sucesso",
                text=f"{processed_count} documentos processados com sucesso!",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: success_dialog.dismiss()
                    )
                ],
                size_hint=(0.8, None)
            )
            self.dialogs.append(success_dialog)
            success_dialog.open()
    
    def show_process_dialog(self, path):
        """Show dialog asking if user wants to process the document now."""
        process_dialog = MDDialog(
            title="Processar Documento",
            text="Deseja processar o documento agora?",
            buttons=[
                MDFlatButton(
                    text="Não",
                    on_release=lambda x: process_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Sim",
                    on_release=lambda x: (process_dialog.dismiss(), self.process_document(len(self.document_list) - 1))
                )
            ],
            size_hint=(0.8, None)
        )
        self.dialogs.append(process_dialog)
        process_dialog.open()
    
    def load_document_list(self):
        """Load the list of previously added documents."""
        # In a real implementation, this would load from storage
        # For now, we'll just clear and update the UI
        self.update_document_list_ui()
    
    def go_to_generate_questions(self, document_text):
        """Navigate to generate questions screen with the processed document."""
        # In a real implementation, this would pass the document text to the generate screen
        app = MDApp.get_running_app()
        app.sm.current = "batch_generate"
    
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
            size_hint=(0.8, None)
        )
        self.dialogs.append(error_dialog)
        error_dialog.open()
    
    def go_back(self):
        """Return to home screen."""
        app = MDApp.get_running_app()
        app.sm.current = "home" 