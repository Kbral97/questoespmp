#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tela inicial do aplicativo Gerador de Questões PMP.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.logger import Logger
from kivy.clock import Clock

from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.snackbar import Snackbar

from ..database.db_manager import DatabaseManager
from ..api.openai_api import OpenAIAPI

import logging
logger = logging.getLogger(__name__)

class TrainingStatusWidget(BoxLayout):
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(150)
        self.padding = dp(5)
        self.spacing = dp(5)
        
        # Título do modelo
        self.title = MDLabel(
            text=title,
            size_hint_y=None,
            height=dp(20),
            font_size=dp(14),
            bold=True
        )
        self.add_widget(self.title)
        
        # Status atual
        self.status_label = MDLabel(
            text='Aguardando início...',
            size_hint_y=None,
            height=dp(20)
        )
        self.add_widget(self.status_label)
        
        # Barra de progresso
        self.progress = MDProgressBar(
            max=100,
            size_hint_y=None,
            height=dp(10)
        )
        self.add_widget(self.progress)
        
        # Detalhes do treinamento
        self.details_label = MDLabel(
            text='',
            size_hint_y=None,
            height=dp(60)
        )
        self.add_widget(self.details_label)
        
        # ID do job
        self.job_id_label = MDLabel(
            text='',
            size_hint_y=None,
            height=dp(20),
            font_size=dp(10)
        )
        self.add_widget(self.job_id_label)
        
    def update_status(self, status, details='', job_id=''):
        """Atualiza o status do widget."""
        self.status_label.text = f"Status: {status}"
        
        # Atualiza detalhes se fornecidos
        if details:
            self.details_label.text = details
        
        # Atualiza ID do job se fornecido
        if job_id:
            self.job_id_label.text = f"Job ID: {job_id}"
        
        # Atualiza a barra de progresso com base no status
        if status == 'validating_files':
            self.progress.value = 10
        elif status == 'queued':
            self.progress.value = 20
        elif status == 'running':
            self.progress.value = 50
        elif status == 'succeeded':
            self.progress.value = 100
        elif status == 'failed':
            self.progress.value = 0
        elif status == 'Concluído':
            self.progress.value = 100
        elif status == 'Erro':
            self.progress.value = 0

class HomeScreen(MDScreen):
    """
    Tela inicial do app com botões para as principais funcionalidades.
    """
    
    def __init__(self, **kwargs):
        """Inicializa a tela."""
        super(HomeScreen, self).__init__(**kwargs)
        self.name = "home"
        self.db_manager = DatabaseManager()
        self.current_jobs = None
        self.api = None
        self.status_check_event = None
        
        self.setup_ui()
        
        logger.info("Tela inicial inicializada")
        
    def setup_ui(self):
        """Set up the user interface."""
        layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        # Title
        title = MDLabel(
            text="Questões PMP",
            font_style="H4",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        layout.add_widget(title)
        
        # Stats Card
        stats_card = MDCard(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(10),
            size_hint=(None, None),
            size=(dp(300), dp(200)),
            pos_hint={'center_x': 0.5}
        )
        
        # Stats Title
        stats_title = MDLabel(
            text="Estatísticas",
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        stats_card.add_widget(stats_title)
        
        # Total Questions
        self.total_questions_label = MDLabel(
            text="Total de Questões: 0",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        stats_card.add_widget(self.total_questions_label)
        
        # Accuracy
        self.accuracy_label = MDLabel(
            text="Precisão Geral: 0%",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        stats_card.add_widget(self.accuracy_label)
        
        # Best Theme
        self.best_theme_label = MDLabel(
            text="Melhor Tema: -",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        stats_card.add_widget(self.best_theme_label)
        
        # Worst Theme
        self.worst_theme_label = MDLabel(
            text="Pior Tema: -",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        stats_card.add_widget(self.worst_theme_label)
        
        layout.add_widget(stats_card)
        
        # Navigation Buttons
        buttons_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(10),
            size_hint_y=None,
            height=dp(300)
        )
        
        # Answer Questions Button
        answer_btn = MDRaisedButton(
            text="Responder Questões",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.navigate_to_answer
        )
        buttons_layout.add_widget(answer_btn)
        
        # Generate Questions Button
        generate_btn = MDRaisedButton(
            text="Gerar Questões",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.navigate_to_generate
        )
        buttons_layout.add_widget(generate_btn)
        
        # View Stats Button
        stats_btn = MDRaisedButton(
            text="Ver Estatísticas",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.navigate_to_stats
        )
        buttons_layout.add_widget(stats_btn)
        
        # Documentation Button
        docs_btn = MDRaisedButton(
            text="Documentação",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.navigate_to_docs
        )
        buttons_layout.add_widget(docs_btn)
        
        # Tune Model Button
        tune_btn = MDRaisedButton(
            text="Ajustar Modelo",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.navigate_to_tune
        )
        buttons_layout.add_widget(tune_btn)
        
        # Check Status Button
        self.check_status_btn = MDRaisedButton(
            text="Verificar Status",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.check_status,
            md_bg_color=(0.2, 0.6, 0.8, 1)  # Azul
        )
        buttons_layout.add_widget(self.check_status_btn)
        
        layout.add_widget(buttons_layout)
        self.add_widget(layout)

    def set_training_jobs(self, jobs, api):
        """Define os jobs de treinamento atuais e a instância da API."""
        self.current_jobs = jobs
        self.api = api
        if jobs and api:
            # Atualiza os widgets de status com as informações iniciais
            self.question_status.update_status(
                jobs['question']['status'],
                'Iniciando validação dos arquivos...',
                jobs['question']['id']
            )
            
            self.answer_status.update_status(
                jobs['answer']['status'],
                'Iniciando validação dos arquivos...',
                jobs['answer']['id']
            )
            
            self.wrong_answers_status.update_status(
                jobs['wrong_answers']['status'],
                'Iniciando validação dos arquivos...',
                jobs['wrong_answers']['id']
            )
            
            # Inicia a verificação automática
            self.start_status_check()
            Snackbar(text="Treinamento iniciado!").open()

    def start_status_check(self):
        """Inicia a verificação automática de status."""
        if self.status_check_event:
            self.status_check_event.cancel()
        self.status_check_event = Clock.schedule_interval(self.check_status, 30)

    def stop_status_check(self):
        """Para a verificação automática de status."""
        if self.status_check_event:
            self.status_check_event.cancel()
            self.status_check_event = None

    def check_status(self, dt):
        """Verifica o status dos treinamentos em andamento."""
        if not self.current_jobs or not self.api:
            logger.warning("Nenhum treinamento em andamento")
            self.stop_status_check()
            return
        
        try:
            # Verifica status do modelo de questões
            question_status = self.api.check_fine_tuning_status(self.current_jobs['question']['id'])
            logger.info(f"Status do modelo de questões: {question_status['status']}")
            self.question_status.update_status(
                question_status['status'],
                f"Trained tokens: {question_status.get('trained_tokens', 0)}\n"
                f"Error rate: {question_status.get('error_rate', 0)}\n"
                f"Training loss: {question_status.get('training_loss', 0)}",
                self.current_jobs['question']['id']
            )
            
            # Verifica status do modelo de respostas
            answer_status = self.api.check_fine_tuning_status(self.current_jobs['answer']['id'])
            logger.info(f"Status do modelo de respostas: {answer_status['status']}")
            self.answer_status.update_status(
                answer_status['status'],
                f"Trained tokens: {answer_status.get('trained_tokens', 0)}\n"
                f"Error rate: {answer_status.get('error_rate', 0)}\n"
                f"Training loss: {answer_status.get('training_loss', 0)}",
                self.current_jobs['answer']['id']
            )
            
            # Verifica status do modelo de respostas incorretas
            wrong_answers_status = self.api.check_fine_tuning_status(self.current_jobs['wrong_answers']['id'])
            logger.info(f"Status do modelo de respostas incorretas: {wrong_answers_status['status']}")
            self.wrong_answers_status.update_status(
                wrong_answers_status['status'],
                f"Trained tokens: {wrong_answers_status.get('trained_tokens', 0)}\n"
                f"Error rate: {wrong_answers_status.get('error_rate', 0)}\n"
                f"Training loss: {wrong_answers_status.get('training_loss', 0)}",
                self.current_jobs['wrong_answers']['id']
            )
            
            # Verifica se todos os jobs foram concluídos
            all_completed = all(
                status['status'] in ['succeeded', 'failed']
                for status in [question_status, answer_status, wrong_answers_status]
            )
            
            if all_completed:
                # Verifica se houve algum erro
                has_error = any(status['status'] == 'failed' for status in [question_status, answer_status, wrong_answers_status])
                if has_error:
                    logger.error("Ocorreu um erro durante o treinamento")
                    Snackbar(text="Erro durante o treinamento!").open()
                else:
                    logger.info("Todos os modelos foram treinados com sucesso!")
                    Snackbar(text="Treinamento concluído com sucesso!").open()
                
                self.current_jobs = None
                self.api = None
                self.stop_status_check()
            
        except Exception as e:
            logger.error(f"Erro ao verificar status do treinamento: {e}")
            Snackbar(text=f"Erro ao verificar status: {str(e)}").open()

    def on_pre_enter(self):
        """Update statistics when entering the screen."""
        self.update_statistics()
        
    def update_statistics(self):
        """Update statistics labels with data from database."""
        try:
            stats = self.db_manager.get_statistics()
            
            # Update total questions and accuracy
            total_questions = stats.get('total_questions', 0)
            accuracy = stats.get('accuracy', 0) * 100
            self.total_questions_label.text = f"Total de questões: {total_questions}"
            self.accuracy_label.text = f"Taxa de acerto: {accuracy:.1f}%"
            
            # Update best topic
            best_topic = stats.get('best_topic')
            if best_topic:
                self.best_theme_label.text = f"Melhor tema: {best_topic}"
            else:
                self.best_theme_label.text = "Melhor tema: N/A"
            
            # Update worst topic
            worst_topic = stats.get('worst_topic')
            if worst_topic:
                self.worst_theme_label.text = f"Pior tema: {worst_topic}"
            else:
                self.worst_theme_label.text = "Pior tema: N/A"
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
            self.total_questions_label.text = "Total de questões: 0"
            self.accuracy_label.text = "Taxa de acerto: 0.0%"
            
    def navigate_to_answer(self, instance):
        """Navigate to answer questions screen."""
        self.manager.current = 'answer_question'
        
    def navigate_to_generate(self, instance):
        """Navigate to generate questions screen."""
        self.manager.current = 'generate'
        
    def navigate_to_stats(self, instance):
        """Navigate to statistics screen."""
        self.manager.current = 'stats'
        
    def navigate_to_docs(self, instance):
        """Navigate to documentation screen."""
        self.manager.current = 'docs'
        
    def navigate_to_tune(self, instance):
        """Navigate to model tuning screen."""
        self.manager.current = 'tuning' 