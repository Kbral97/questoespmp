"""
Text Processing Screen for PMP Questions Generator
"""

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.progressbar import MDProgressBar
from kivy.metrics import dp
from kivy.clock import Clock
import threading
import logging
import os

from ..text_processor import process_text

logger = logging.getLogger(__name__)

class TextProcessorScreen(MDScreen):
    """Screen for processing text files and generating training data."""
    
    def __init__(self, **kwargs):
        """Initialize the text processor screen."""
        super().__init__(**kwargs)
        self.file_manager = None
        self.selected_files = []
        self.processing_thread = None
        self.build_ui()
    
    def build_ui(self):
        """Build the user interface."""
        # Main layout
        layout = MDBoxLayout(
            orientation="vertical",
            spacing=10,
            padding=20
        )
        
        # Title
        title = MDLabel(
            text="Processamento de Textos",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        layout.add_widget(title)
        
        # Description
        description = MDLabel(
            text="Selecione os arquivos de texto para processar e gerar dados de treinamento.",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        layout.add_widget(description)
        
        # File selection card
        file_card = MDCard(
            orientation="vertical",
            padding=15,
            size_hint_y=None,
            height=dp(200),
            radius=[15, 15, 15, 15],
            elevation=2
        )
        
        # File selection layout
        file_layout = MDBoxLayout(
            orientation="vertical",
            spacing=10,
            size_hint_y=None,
            height=dp(170)
        )
        
        # Selected files label
        self.files_label = MDLabel(
            text="Nenhum arquivo selecionado",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        file_layout.add_widget(self.files_label)
        
        # Select files button
        select_btn = MDRaisedButton(
            text="Selecionar Arquivos",
            size_hint_y=None,
            height=dp(50),
            on_release=self.show_file_manager
        )
        file_layout.add_widget(select_btn)
        
        file_card.add_widget(file_layout)
        layout.add_widget(file_card)
        
        # Progress card
        self.progress_card = MDCard(
            orientation="vertical",
            padding=15,
            size_hint_y=None,
            height=dp(150),
            radius=[15, 15, 15, 15],
            elevation=2
        )
        
        # Progress layout
        progress_layout = MDBoxLayout(
            orientation="vertical",
            spacing=10,
            size_hint_y=None,
            height=dp(120)
        )
        
        # File progress
        self.file_progress_label = MDLabel(
            text="Progresso do arquivo:",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        progress_layout.add_widget(self.file_progress_label)
        
        self.file_progress = MDProgressBar(
            value=0,
            size_hint_x=0.8,
            pos_hint={'center_x': 0.5}
        )
        progress_layout.add_widget(self.file_progress)
        
        # Total progress
        self.total_progress_label = MDLabel(
            text="Progresso total:",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        progress_layout.add_widget(self.total_progress_label)
        
        self.total_progress = MDProgressBar(
            value=0,
            size_hint_x=0.8,
            pos_hint={'center_x': 0.5}
        )
        progress_layout.add_widget(self.total_progress)
        
        # Status label
        self.status_label = MDLabel(
            text="",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        progress_layout.add_widget(self.status_label)
        
        # Spinner
        self.spinner = MDSpinner(
            size_hint=(None, None),
            size=(dp(30), dp(30)),
            pos_hint={"center_x": 0.5},
            active=False
        )
        progress_layout.add_widget(self.spinner)
        
        self.progress_card.add_widget(progress_layout)
        layout.add_widget(self.progress_card)
        
        # Controls
        controls = MDBoxLayout(
            orientation="horizontal",
            spacing=10,
            size_hint_y=None,
            height=dp(50)
        )
        
        # Process button
        self.process_btn = MDRaisedButton(
            text="Processar Arquivos",
            size_hint_x=0.5,
            on_release=self.process_files
        )
        controls.add_widget(self.process_btn)
        
        # Back button
        back_btn = MDRaisedButton(
            text="Voltar",
            size_hint_x=0.5,
            on_release=self.go_back
        )
        controls.add_widget(back_btn)
        
        layout.add_widget(controls)
        
        self.add_widget(layout)
    
    def show_file_manager(self, instance):
        """Show the file manager dialog."""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_file_manager,
                select_path=self.select_path
            )
        self.file_manager.show(os.path.expanduser("~"))
    
    def exit_file_manager(self, *args):
        """Close the file manager."""
        self.file_manager.close()
    
    def select_path(self, path):
        """Handle file selection."""
        if os.path.isfile(path) and path.endswith('.txt'):
            if path not in self.selected_files:
                self.selected_files.append(path)
                self.update_files_label()
        self.exit_file_manager()
    
    def update_files_label(self):
        """Update the selected files label."""
        if self.selected_files:
            files_text = "Arquivos selecionados:\n"
            for file in self.selected_files:
                files_text += f"- {os.path.basename(file)}\n"
            self.files_label.text = files_text
        else:
            self.files_label.text = "Nenhum arquivo selecionado"
    
    def process_files(self, instance):
        """Process the selected files."""
        if not self.selected_files:
            self.show_error_dialog("Por favor, selecione pelo menos um arquivo para processar.")
            return
        
        self.process_btn.disabled = True
        self.spinner.active = True
        self.status_label.text = "Iniciando processamento..."
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self._process_files_thread)
        self.processing_thread.start()
    
    def _process_files_thread(self):
        """Process files in a separate thread."""
        try:
            total_files = len(self.selected_files)
            for i, file_path in enumerate(self.selected_files):
                # Update file progress
                Clock.schedule_once(
                    lambda dt, f=file_path: self.file_progress_label.set_text(f"Processando: {os.path.basename(f)}"),
                    0
                )
                
                # Process the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split content into smaller chunks (e.g., paragraphs)
                chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
                
                # Process each chunk
                for j, chunk in enumerate(chunks):
                    # Update progress
                    chunk_progress = (j + 1) / len(chunks)
                    Clock.schedule_once(
                        lambda dt, p=chunk_progress: self.file_progress.set_value(p * 100),
                        0
                    )
                    
                    # Process the chunk
                    process_text(chunk)
                
                # Update total progress
                total_progress = (i + 1) / total_files
                Clock.schedule_once(
                    lambda dt, p=total_progress: self.total_progress.set_value(p * 100),
                    0
                )
                
                # Update status
                Clock.schedule_once(
                    lambda dt, f=file_path: self.status_label.set_text(f"Processado: {os.path.basename(f)}"),
                    0
                )
            
            # Reset UI after processing
            Clock.schedule_once(lambda dt: self.reset_ui(), 0)
            
        except Exception as e:
            logger.error(f"Error processing files: {str(e)}")
            Clock.schedule_once(
                lambda dt: self.show_error_dialog(f"Erro ao processar arquivos: {str(e)}"),
                0
            )
            Clock.schedule_once(lambda dt: self.reset_ui(), 0)
    
    def reset_ui(self):
        """Reset the UI state."""
        self.process_btn.disabled = False
        self.spinner.active = False
        self.file_progress.value = 0
        self.total_progress.value = 0
    
    def show_error_dialog(self, message):
        """Show an error dialog."""
        dialog = MDDialog(
            title="Erro",
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
    
    def go_back(self, instance):
        """Navigate back to the previous screen."""
        self.manager.current = "home" 