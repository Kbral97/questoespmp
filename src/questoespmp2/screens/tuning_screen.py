#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tela de ajuste fino do modelo.
"""

import json
import threading
import logging
import os
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.logger import Logger
from kivy.uix.behaviors import DragBehavior
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, BooleanProperty
from kivy.core.window import Window
from datetime import datetime

from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import TwoLineListItem
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.progressbar import MDProgressBar

from ..api.openai_api import OpenAIAPI
from ..api.csv_to_ft import convert_csv_to_fine_tuning
from ..utils.api_manager import APIManager
from ..database.db_manager import DatabaseManager
from ..widgets.file_drop import FileDropWidget

logger = logging.getLogger(__name__)

class DropTarget(Widget):
    """Widget para receber arquivos arrastados."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_file_drop')
        Window.bind(on_drop_file=self._on_file_drop)
    
    def on_file_drop(self, file_path, x, y):
        """Handler padrão para o evento on_file_drop."""
        pass
    
    def _find_tuning_screen(self):
        """Encontrar a instância da TuningScreen."""
        def find_screen(widget):
            if isinstance(widget, TuningScreen):
                return widget
            for child in widget.children:
                result = find_screen(child)
                if result:
                    return result
            return None
        
        return find_screen(self.get_root_window())
    
    def _on_file_drop(self, window, file_path, x, y):
        """Manipula o evento de drop de arquivo."""
        try:
            # Converter o caminho do arquivo de bytes para string
            file_path_str = file_path.decode('utf-8')
            
            # Verificar se é um arquivo CSV
            if file_path_str.lower().endswith('.csv'):
                # Encontrar a instância do TuningScreen
                tuning_screen = self._find_tuning_screen()
                if tuning_screen:
                    tuning_screen.handle_file_drop(file_path_str)
                else:
                    logger.error("Não foi possível encontrar a tela de tuning")
            else:
                tuning_screen = self._find_tuning_screen()
                if tuning_screen:
                    tuning_screen.show_error_dialog("Por favor, selecione um arquivo CSV.")
                else:
                    logger.error("Não foi possível encontrar a tela de tuning")
        except Exception as e:
            logger.error(f"Erro ao processar arquivo dropado: {e}")
            tuning_screen = self._find_tuning_screen()
            if tuning_screen:
                tuning_screen.show_error_dialog(f"Erro ao processar arquivo: {str(e)}")
            else:
                logger.error("Não foi possível encontrar a tela de tuning")

class TuningScreen(MDScreen):
    """
    Tela para ajuste fino do modelo.
    """
    
    def __init__(self, **kwargs):
        """Inicializa a tela."""
        super().__init__(**kwargs)
        self.name = "tuning"
        self.title = "Ajuste do Modelo"
        self.file_manager = None
        self.selected_file_path = None
        self.file_label = None
        self.status_label = None
        self.api_key_input = None
        self.job_id_input = None
        self.tuning_jobs = []  # Lista para armazenar jobs de fine-tuning
        self.job_status_cache = {}  # Cache para status de jobs
        self.api = None
        self.processing = False
        self.processing_thread = None
        self.progress = 0
        self.status_message = ""
        self.dialog = None
        self.db_manager = DatabaseManager()
        self.api_manager = APIManager()
        
        self.setup_ui()
        
        logger.info("Tela de tuning inicializada")
        
    def setup_ui(self):
        """Set up the user interface."""
        main_layout = MDBoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))
        
        # Scroll view para o conteúdo
        scroll_view = ScrollView()
        content_layout = MDBoxLayout(orientation="vertical", spacing=dp(15), size_hint_y=None)
        content_layout.bind(minimum_height=content_layout.setter('height'))
        
        # Título
        title = MDLabel(
            text="Ajuste do Modelo (Fine-Tuning)",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        content_layout.add_widget(title)
        
        # Descrição
        description = MDLabel(
            text="Use esta tela para ajustar os modelos de IA para geração de questões.\nArraste e solte um arquivo CSV ou use o botão para selecionar.",
            size_hint_y=None,
            height=dp(60)
        )
        content_layout.add_widget(description)
        
        # Área de drop file
        self.file_drop = FileDropWidget(
            size_hint_y=None,
            height=dp(150),
            allowed_extensions=['.csv'],
            on_file_selected=self.on_file_selected
        )
        content_layout.add_widget(self.file_drop)
        
        # Seleção de arquivo
        file_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(120)
        )
        
        file_title = MDLabel(
            text="Arquivo de Treinamento",
            font_style="H6",
            size_hint_y=None,
            height=dp(30)
        )
        file_section.add_widget(file_title)
        
        file_buttons = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(50)
        )
        
        select_file_btn = MDRaisedButton(
            text="Selecionar Arquivo",
            on_release=self.show_file_manager,
            size_hint_x=0.5
        )
        file_buttons.add_widget(select_file_btn)
        
        self.file_label = MDLabel(
            text="Nenhum arquivo selecionado",
            size_hint_x=0.5,
            valign="center"
        )
        file_buttons.add_widget(self.file_label)
        
        file_section.add_widget(file_buttons)
        
        # Botão para importar questões
        import_btn = MDRaisedButton(
            text="Importar Questões para o Banco",
            icon="database-import",
            on_release=self.import_questions,
            size_hint=(1, None),
            height=dp(50),
            pos_hint={'center_x': 0.5}
        )
        file_section.add_widget(import_btn)
        
        content_layout.add_widget(file_section)
        
        # API Key
        api_section = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60)
        )
        
        api_label = MDLabel(
            text="Chave de API OpenAI:",
            size_hint_x=0.4
        )
        api_section.add_widget(api_label)
        
        self.api_key_input = MDTextField(
            hint_text="Inserir chave de API OpenAI",
            password=True,
            size_hint_x=0.6
        )
        api_section.add_widget(self.api_key_input)
        
        content_layout.add_widget(api_section)
        
        # Status Label
        self.status_label = MDLabel(
            text="",
            halign="center",
            size_hint_y=None,
            height=dp(40)
        )
        content_layout.add_widget(self.status_label)
        
        # Progress Bar
        self.progress_bar = MDProgressBar(
            size_hint_y=None,
            height=dp(10),
            value=0
        )
        content_layout.add_widget(self.progress_bar)
        
        # Botão de treinamento
        train_btn = MDRaisedButton(
            text="Iniciar Treinamento",
            on_release=self.start_training,
            size_hint=(1, None),
            height=dp(50),
            pos_hint={'center_x': 0.5},
            md_bg_color=(0.2, 0.8, 0.2, 1)  # Verde
        )
        content_layout.add_widget(train_btn)
        
        # Botão voltar
        back_btn = MDRaisedButton(
            text="Voltar",
            on_release=self.go_back,
            size_hint=(1, None),
            height=dp(50)
        )
        content_layout.add_widget(back_btn)
        
        scroll_view.add_widget(content_layout)
        main_layout.add_widget(scroll_view)
        self.add_widget(main_layout)
        
        # Carrega a chave da API, se disponível
        saved_key = self.api_manager.get_api_key()
        if saved_key:
            self.api_key_input.text = saved_key
        
    def show_file_manager(self, instance):
        """Mostra o gerenciador de arquivos."""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_file_manager,
                select_path=self.select_file,
                preview=False,
                ext=['.csv']
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
        
    def on_file_selected(self, widget, file_path):
        """Manipula a seleção ou soltar de arquivo."""
        if not file_path.lower().endswith('.csv'):
            self.show_error_dialog("Erro", "Formato de arquivo não suportado. Por favor, selecione um arquivo CSV.")
            return
            
        self.selected_file_path = file_path
        self.file_label.text = os.path.basename(file_path)
        self.status_label.text = f"Arquivo selecionado: {os.path.basename(file_path)}"
        
    def import_questions(self, instance):
        """Importa questões do arquivo CSV para o banco de dados."""
        if not self.selected_file_path:
            self.show_error_dialog("Erro", "Nenhum arquivo selecionado.")
            return
            
        try:
            # Implementar lógica para importar questões
            self.status_label.text = "Importando questões..."
            self.progress_bar.value = 0
            
            # Iniciar em uma thread separada
            threading.Thread(target=self._import_questions_thread).start()
            
        except Exception as e:
            logger.error(f"Erro ao importar questões: {e}")
            self.show_error_dialog("Erro", f"Erro ao importar questões: {str(e)}")
            
    def _import_questions_thread(self):
        """Thread para importar questões."""
        try:
            # Aqui você deve implementar a lógica para importar as questões para o banco
            # Exemplo básico:
            import csv
            
            with open(self.selected_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                total_rows = sum(1 for _ in open(self.selected_file_path, 'r', encoding='utf-8')) - 1
                imported = 0
                
                # Voltar ao início do arquivo depois de contar as linhas
                f.seek(0)
                next(reader)  # Pular o cabeçalho
                
                for i, row in enumerate(reader):
                    # Processa cada linha do CSV
                    # Supondo que seu CSV tenha colunas "pergunta", "resposta_correta", etc.
                    question_data = {
                        'question': row.get('question', ''),
                        'correct_answer': row.get('correct_answer', ''),
                        'explanation': row.get('explanation', ''),
                        'options': [
                            row.get('option_a', ''),
                            row.get('option_b', ''),
                            row.get('option_c', ''),
                            row.get('option_d', '')
                        ],
                        'topic': row.get('topic', ''),
                        'difficulty': row.get('difficulty', 'medium'),
                        'created_at': datetime.now().isoformat()
                    }
                    
                    # Inserir no banco de dados
                    self.db_manager.insert_question(question_data)
                    imported += 1
                    
                    # Atualizar progresso
                    progress = (i + 1) / total_rows * 100
                    Clock.schedule_once(lambda dt, p=progress: self.update_import_progress(p), 0)
            
            # Atualizar status final
            Clock.schedule_once(lambda dt: self.finish_import(imported), 0)
            
        except Exception as e:
            logger.error(f"Erro ao importar questões: {e}")
            Clock.schedule_once(lambda dt, err=str(e): self.show_error_dialog("Erro", f"Erro ao importar questões: {err}"), 0)
            
    def update_import_progress(self, progress):
        """Atualiza o progresso da importação."""
        self.progress_bar.value = progress
        self.status_label.text = f"Importando... {int(progress)}%"
        
    def finish_import(self, imported):
        """Finaliza a importação."""
        self.progress_bar.value = 100
        self.status_label.text = f"Importação concluída! {imported} questões importadas."
        self.show_success_dialog("Sucesso", f"{imported} questões foram importadas com sucesso!")
        
    def start_training(self, instance):
        """Inicia o processo de treinamento."""
        # Usa a chave da API do input ou a salva no aplicativo
        api_key = self.api_key_input.text.strip()
        
        if not api_key:
            # Tenta usar a chave salva no aplicativo
            api_key = self.api_manager.get_api_key()
            if not api_key:
                self.show_error_dialog("Erro", "Por favor, insira sua chave da API OpenAI.")
                return
        else:
            # Salva a nova chave
            self.api_manager.save_api_key(api_key)
            
        if not self.selected_file_path and not os.path.exists("data/pmp_questions.csv"):
            self.show_error_dialog("Erro", "Nenhum arquivo selecionado para treinamento.")
            return
            
        try:
            # Inicializa a API
            self.api = OpenAIAPI(api_key)
            
            # Atualiza o status
            self.status_label.text = "Preparando arquivos de treinamento..."
            self.progress_bar.value = 10
            
            # Inicia o treinamento em uma thread separada
            self.processing_thread = threading.Thread(
                target=self._training_thread,
                args=(self.selected_file_path or "data/pmp_questions.csv",)
            )
            self.processing_thread.start()
            
        except Exception as e:
            logger.error(f"Erro ao iniciar treinamento: {e}")
            self.show_error_dialog("Erro", f"Erro ao iniciar treinamento: {str(e)}")
            
    def _training_thread(self, csv_file):
        """Thread para o processo de treinamento."""
        try:
            # Gera os arquivos de treinamento
            Clock.schedule_once(lambda dt: self.update_training_status("Gerando arquivos JSONL...", 20), 0)
            
            question_file, answer_file, wrong_answers_file = convert_csv_to_fine_tuning(csv_file)
            
            # Atualiza o progresso
            Clock.schedule_once(lambda dt: self.update_training_status("Iniciando treinamento do modelo de questões...", 30), 0)
            
            # Inicia os jobs de treinamento
            question_job = self.api.start_fine_tuning(question_file)
            
            Clock.schedule_once(lambda dt: self.update_training_status("Iniciando treinamento do modelo de respostas...", 50), 0)
            answer_job = self.api.start_fine_tuning(answer_file)
            
            Clock.schedule_once(lambda dt: self.update_training_status("Iniciando treinamento do modelo de respostas incorretas...", 70), 0)
            wrong_answers_job = self.api.start_fine_tuning(wrong_answers_file)
            
            # Organiza os jobs
            jobs = {
                'question': question_job,
                'answer': answer_job,
                'wrong_answers': wrong_answers_job
            }
            
            # Atualiza o status na tela inicial
            Clock.schedule_once(lambda dt: self.update_training_status("Treinamento iniciado!", 100), 0)
            
            # Passa os jobs para a tela inicial
            Clock.schedule_once(lambda dt: self.pass_jobs_to_home(jobs), 0)
            
        except Exception as e:
            logger.error(f"Erro durante o treinamento: {e}")
            Clock.schedule_once(lambda dt, err=str(e): self.show_error_dialog("Erro", f"Erro durante o treinamento: {err}"), 0)
            
    def update_training_status(self, message, progress):
        """Atualiza o status do treinamento."""
        self.status_label.text = message
        self.progress_bar.value = progress
        
    def pass_jobs_to_home(self, jobs):
        """Passa os jobs para a tela inicial."""
        home_screen = self.manager.get_screen('home')
        home_screen.set_training_jobs(jobs, self.api)
        
        # Mostra mensagem de sucesso
        self.show_success_dialog(
            "Treinamento Iniciado",
            "O treinamento foi iniciado com sucesso!\n\nVocê pode verificar o status na tela inicial."
        )
        
    def show_success_dialog(self, title, text):
        """Mostra diálogo de sucesso."""
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
        """Mostra diálogo de erro."""
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

    def handle_file_drop(self, file_path):
        """Handle file drop event."""
        self.selected_file_path = file_path
        self.file_label.text = os.path.basename(file_path)
        self._load_training_data()

    def _load_training_data(self):
        """Carregar e preparar os dados de treinamento do arquivo CSV."""
        if not self.selected_file_path:
            return
            
        try:
            import csv
            self.training_data = {
                "question_generator": [],
                "answer_generator": [],
                "distractor_generator": []
            }
            
            with open(self.selected_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    # Dados para o gerador de perguntas
                    self.training_data["question_generator"].append({
                        "prompt": f"Tema: {row.get('Tema', '')}",
                        "completion": row.get('Pergunta', '')
                    })
                    
                    # Dados para o gerador de respostas
                    self.training_data["answer_generator"].append({
                        "prompt": f"Tema: {row.get('Tema', '')}\nPergunta: {row.get('Pergunta', '')}",
                        "completion": f"Resposta: {row.get('Resposta correta', '')}\nJustificativa: {row.get('Explicação', '')}"
                    })
                    
                    # Dados para o gerador de distratores
                    self.training_data["distractor_generator"].append({
                        "prompt": f"Tema: {row.get('Tema', '')}\nPergunta: {row.get('Pergunta', '')}\nResposta Correta: {row.get('Resposta correta', '')}",
                        "completion": f"Opção A: {row.get('opção incorreta 1', '')}\nOpção B: {row.get('opção incorreta 2', '')}\nOpção C: {row.get('opção incorreta 3', '')}"
                    })
            
            self.status_label.text = "Dados de treinamento carregados com sucesso!"
            
        except Exception as e:
            self.show_error_dialog(f"Erro ao carregar dados: {str(e)}")
            self.status_label.text = "Erro ao carregar dados."

    def start_tuning(self, instance):
        """Iniciar o processo de fine-tuning para todos os modelos."""
        if not self.training_data:
            self.show_error_dialog("Por favor, carregue os dados de treinamento primeiro.")
            return
            
        api_key = self.api_key_input.text.strip()
        if not api_key:
            self.show_error_dialog("Por favor, insira a chave da API OpenAI.")
            return
            
        # Salvar a chave da API se o config_manager estiver disponível
        if self.api:
            self.api.set_api_key(api_key)
            
        # Iniciar o treinamento em uma thread separada
        threading.Thread(target=self._run_tuning_all_models, args=(api_key,)).start()
        
        # Atualizar a UI
        self.status_label.text = "Iniciando treinamento para todos os modelos..."
        
    def _run_tuning_all_models(self, api_key):
        """Executar o fine-tuning para todos os modelos."""
        try:
            results = {}
            
            # Treinar cada modelo
            for model_type in ["question_generator", "answer_generator", "distractor_generator"]:
                try:
                    # Atualizar status
                    Clock.schedule_once(
                        lambda dt: setattr(self.status_label, 'text', f"Treinando modelo: {model_type}..."),
                        0
                    )
                    
                    # Executar o treinamento
                    result = self._run_tuning(self.training_data[model_type], api_key)
                    results[model_type] = result
                    
                except Exception as e:
                    logger.error(f"Erro ao treinar {model_type}: {str(e)}")
                    results[model_type] = {"error": str(e)}
            
            # Atualizar a UI com os resultados
            Clock.schedule_once(lambda dt: self._update_ui_with_all_results(results), 0)
            
        except Exception as e:
            logger.error(f"Erro no processo de treinamento: {str(e)}")
            Clock.schedule_once(lambda dt: self._handle_tuning_error(str(e)), 0)
            
    def _update_ui_with_all_results(self, results):
        """Atualizar a UI com os resultados de todos os modelos."""
        if not results:
            self.status_label.text = "Erro: Nenhum resultado disponível do treinamento."
            return
            
        status_text = "Resultados do treinamento:\n\n"
        
        for model_type, result in results.items():
            if not result:
                status_text += f"{model_type}: Erro - Resultado indisponível\n"
                continue
                
            if isinstance(result, dict) and "error" in result:
                status_text += f"{model_type}: Erro - {result['error']}\n"
            else:
                status_text += f"{model_type}: Job ID - {result.get('job_id', 'N/A')}\n"
        
        self.status_label.text = status_text
        self.show_success_dialog("Treinamento Iniciado", status_text)
    
    def _run_tuning(self, training_data, api_key=None):
        """Executar o ajuste em uma thread separada."""
        try:
            from ..api.openai_client import tune_model
            
            # Chamar a API para iniciar o ajuste
            result = tune_model(training_data, api_key)
            
            # Atualizar UI na thread principal
            Clock.schedule_once(lambda dt: self._update_ui_with_result(result), 0)
            
        except Exception as e:
            logger.error(f"Erro durante o ajuste do modelo: {e}")
            Clock.schedule_once(lambda dt: self._handle_tuning_error(str(e)), 0)
    
    def _update_ui_with_result(self, result):
        """Atualizar a UI com o resultado do ajuste."""
        if result and 'id' in result:
            # Adicionar job à lista
            self.tuning_jobs.append(result)
            self.job_status_cache[result['id']] = result
            
            # Atualizar UI
            self.status_label.text = f"Ajuste iniciado com sucesso!\nJob ID: {result['id']}\nStatus: {result['status']}"
            self.job_id_input.text = result['id']
            
            # Adicionar à lista de jobs
            self._update_jobs_list()
        else:
            self.status_label.text = "Erro ao iniciar ajuste. Verifique os logs para mais detalhes."
    
    def _handle_tuning_error(self, error_msg):
        """Lidar com erros durante o ajuste."""
        self.status_label.text = "Erro durante o processo de ajuste."
        self.show_error_dialog(f"Erro durante o ajuste do modelo: {error_msg}")
    
    def check_status(self, instance):
        """Verificar o status de um job de fine-tuning."""
        job_id = self.job_id_input.text.strip()
        if not job_id:
            self.show_error_dialog("Por favor, insira um ID de job para verificar.")
            return
        
        api_key = self.api_key_input.text.strip() if self.api_key_input.text.strip() else None
        
        # Atualizar UI
        self.status_label.text = f"Verificando status do job {job_id}..."
        
        # Iniciar thread para não bloquear a UI
        threading.Thread(target=self._run_status_check, args=(job_id, api_key)).start()
    
    def _run_status_check(self, job_id, api_key=None):
        """Executar a verificação de status em uma thread separada."""
        try:
            from ..api.openai_client import get_tuning_status
            
            # Chamar a API para verificar o status
            result = get_tuning_status(job_id, api_key)
            
            # Atualizar UI na thread principal
            Clock.schedule_once(lambda dt: self._update_ui_with_status(result), 0)
            
        except Exception as e:
            logger.error(f"Erro ao verificar status do job: {e}")
            Clock.schedule_once(lambda dt: self._handle_status_error(str(e)), 0)
    
    def _update_ui_with_status(self, result):
        """Atualizar a UI com o status do job."""
        if result and 'id' in result:
            # Atualizar cache
            self.job_status_cache[result['id']] = result
            
            # Formatar texto de status
            status_text = f"Status do job {result['id']}:\n"
            status_text += f"Status: {result['status']}\n"
            if 'fine_tuned_model' in result and result['fine_tuned_model']:
                status_text += f"Modelo: {result['fine_tuned_model']}\n"
                # Salvar informações do modelo no config manager
                if self.api:
                    self.api.set_fine_tuned_model(result['fine_tuned_model'])
                    self.api.set_last_job_id(result['id'])
            if 'created_at' in result:
                status_text += f"Criado em: {result['created_at']}\n"
            if 'finished_at' in result:
                status_text += f"Finalizado em: {result['finished_at']}\n"
            
            # Atualizar UI
            self.status_label.text = status_text
            
            # Atualizar lista de jobs
            found = False
            for i, job in enumerate(self.tuning_jobs):
                if job['id'] == result['id']:
                    self.tuning_jobs[i] = result
                    found = True
                    break
            
            if not found:
                self.tuning_jobs.append(result)
                
            self._update_jobs_list()
            
            # Se o fine-tuning foi concluído com sucesso, mostrar mensagem
            if result.get('status') == 'succeeded' and result.get('fine_tuned_model'):
                self.show_success_dialog(
                    "Fine-tuning concluído com sucesso!",
                    f"O modelo {result['fine_tuned_model']} foi salvo e está pronto para uso."
                )
            
        else:
            self.status_label.text = "Erro ao verificar status. Verifique os logs para mais detalhes."
    
    def _handle_status_error(self, error_msg):
        """Lidar com erros durante a verificação de status."""
        self.status_label.text = "Erro ao verificar status do job."
        self.show_error_dialog(f"Erro ao verificar status: {error_msg}")
    
    def _update_jobs_list(self):
        """Atualizar a lista de jobs na UI."""
        # Limpar lista atual
        self.jobs_list.clear_widgets()
        
        if not self.tuning_jobs:
            empty_label = MDLabel(
                text="Nenhum job de fine-tuning encontrado.",
                halign="center"
            )
            self.jobs_list.add_widget(empty_label)
            return
        
        # Adicionar cada job à lista
        for job in self.tuning_jobs:
            job_id = job.get('id', 'Unknown')
            status = job.get('status', 'Unknown')
            model = job.get('fine_tuned_model', 'N/A')
            
            job_item = TwoLineListItem(
                text=f"Job ID: {job_id}",
                secondary_text=f"Status: {status} | Modelo: {model}",
                on_release=lambda x, j=job: self._select_job(j)
            )
            self.jobs_list.add_widget(job_item)
    
    def _select_job(self, job):
        """Selecionar um job da lista."""
        self.job_id_input.text = job['id']
        
        # Mostrar detalhes do job
        status_text = f"Job selecionado: {job['id']}\n"
        status_text += f"Status: {job['status']}\n"
        if 'fine_tuned_model' in job and job['fine_tuned_model']:
            status_text += f"Modelo: {job['fine_tuned_model']}\n"
        if 'created_at' in job:
            status_text += f"Criado em: {job['created_at']}\n"
        
        self.status_label.text = status_text

    def _select_model_type(self, model_type):
        """Selecionar o tipo de modelo para ajuste."""
        self.model_type = model_type
        model_names = {
            "question_generator": "Gerador de Perguntas",
            "answer_generator": "Gerador de Respostas e Justificativas",
            "distractor_generator": "Gerador de Distratores"
        }
        self.status_label.text = f"Modelo selecionado: {model_names.get(model_type, 'Desconhecido')}" 