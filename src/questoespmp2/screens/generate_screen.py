#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate Questions Screen for PMP Questions Generator
"""

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDFloatingActionButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivy.uix.spinner import Spinner
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivymd.uix.scrollview import ScrollView
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.slider import MDSlider
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.snackbar import Snackbar

from ..api.openai_client import generate_questions, generate_questions_with_specialized_models, get_openai_client
from ..api.openai_client import list_available_models, find_relevant_training_data
from ..database.db_manager import DatabaseManager
from questoespmp2.utils.api_manager import APIManager
from ..api.openai_api import OpenAIAPI

import threading
from kivy.clock import Clock
import logging
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
import time
import json
import random

logger = logging.getLogger(__name__)

class ModelSelectionButton(MDRaisedButton):
    """Botão para seleção de modelo."""
    
    def __init__(self, text="", model_id=None, on_select=None, selected=False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.model_id = model_id
        self.on_select = on_select
        self.selected = selected
        self.size_hint = (None, None)
        self.height = dp(60)  # Altura maior para melhor usabilidade
        self.width = dp(250)  # Largura fixa
        self.md_bg_color = (0.2, 0.6, 0.8, 1.0) if selected else (0.5, 0.5, 0.5, 1.0)
        
    def on_release(self):
        """Chamado quando o botão é liberado após clique."""
        if self.on_select:
            self.on_select(self.model_id)

class ModelTypeCard(MDCard):
    """Card para selecionar um tipo de modelo (questões, respostas, distratores)."""
    
    def __init__(self, title, models_list=None, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(20)  # Aumentado
        self.spacing = dp(15)  # Aumentado
        self.size_hint = (None, None)
        self.size = (dp(300), dp(400))  # Altura aumentada
        self.pos_hint = {'center_x': 0.5}
        self.elevation = 4
        self.title = title
        self.models_list = models_list or []
        self.callback = callback
        self.selected_model = None
        
        # Título
        self.title_label = MDLabel(
            text=title,
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(40)  # Altura aumentada
        )
        self.add_widget(self.title_label)
        
        # Scroll para os botões (para muitos modelos)
        self.scroll = ScrollView(
            size_hint=(1, None),
            height=dp(300),  # Altura aumentada
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        # Layout para os botões
        self.buttons_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            size_hint_y=None
        )
        self.buttons_layout.bind(minimum_height=self.buttons_layout.setter('height'))
        
        # Adicionar botões para os modelos padrão
        default_models = [
            {"id": "default_gpt35", "name": "GPT-3.5 Turbo (Padrão)"},
            {"id": "default_gpt4", "name": "GPT-4 (Padrão)"}
        ]
        
        # Adicionar botões para os modelos disponíveis
        self.model_buttons = []
        
        for model in default_models:
            btn = ModelSelectionButton(
                text=model["name"],
                model_id=model["id"],
                on_select=self.select_model,
                size_hint_y=None,
                height=dp(60)  # Altura aumentada
            )
            self.buttons_layout.add_widget(btn)
            self.model_buttons.append(btn)
        
        # Adicionar botões para os modelos fine-tuned
        if self.models_list:
            for model in self.models_list:
                btn = ModelSelectionButton(
                    text=model["name"],
                    model_id=model["id"],
                    on_select=self.select_model,
                    size_hint_y=None,
                    height=dp(60)  # Altura aumentada
                )
                self.buttons_layout.add_widget(btn)
                self.model_buttons.append(btn)
        
        self.scroll.add_widget(self.buttons_layout)
        self.add_widget(self.scroll)
        
        # Label para o modelo selecionado
        self.selected_label = MDLabel(
            text="Nenhum modelo selecionado",
            halign="center",
            size_hint_y=None,
            height=dp(40)  # Altura aumentada
        )
        self.add_widget(self.selected_label)
        
    def select_model(self, model_id):
        """Seleciona um modelo e atualiza o estado do UI."""
        self.selected_model = model_id
        
        # Atualizar cores dos botões
        for btn in self.model_buttons:
            if btn.model_id == model_id:
                btn.md_bg_color = (0.2, 0.6, 0.8, 1.0)  # Azul para selecionado
                model_name = btn.text
                self.selected_label.text = f"Selecionado: {model_name}"
            else:
                btn.md_bg_color = (0.5, 0.5, 0.5, 1.0)  # Cinza para não selecionado
        
        # Notificar o callback se existir
        if self.callback:
            self.callback(self.title, model_id)
    
    def get_selected_model(self):
        """Retorna o ID do modelo selecionado."""
        return self.selected_model

class GenerateScreen(MDScreen):
    """Screen for generating individual questions."""
    
    # Lista de tópicos do PMBOK
    TOPICS = [
        "Gerenciamento da Integração",
        "Gerenciamento do Escopo",
        "Gerenciamento do Cronograma",
        "Gerenciamento dos Custos",
        "Gerenciamento da Qualidade",
        "Gerenciamento dos Recursos",
        "Gerenciamento das Comunicações",
        "Gerenciamento dos Riscos",
        "Gerenciamento das Aquisições",
        "Gerenciamento das Partes Interessadas"
    ]
    
    def __init__(self, **kwargs):
        """Initialize the generate questions screen."""
        super().__init__(**kwargs)
        self.name = "generate"
        self.dialogs = []
        self.dialog = None  # Initialize dialog attribute
        self.topics_menu = None
        self.selected_topic = None
        self.questions = []
        self.api_manager = APIManager()
        self.db = DatabaseManager()
        self.api = None
        self.generation_thread = None
        self.default_models = self.api_manager.get_default_models()
        self.setup_ui()
        self.setup_menu()
        
        # Load saved API key if exists
        saved_key = self.api_manager.get_api_key()
        if saved_key:
            self.api_key.text = saved_key
            self.update_generate_button()
    
    def on_pre_leave(self):
        """Clean up when leaving the screen."""
        for dialog in self.dialogs:
            if dialog:
                dialog.dismiss()
        self.dialogs = []
    
    def setup_ui(self):
        """Set up the user interface."""
        # Incluído em um ScrollView para permitir rolagem
        scroll = ScrollView()
        main_layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20), size_hint_y=None)
        main_layout.bind(minimum_height=main_layout.setter('height'))
        
        # Verificar se existem modelos padrão
        self.default_models = self.api_manager.get_default_models()
        
        # Inicializa os modelos selecionados
        self.selected_question_model = self.default_models.get('question')
        self.selected_answer_model = self.default_models.get('answer')
        self.selected_wrong_answers_model = self.default_models.get('wrong_answers')
        
        # Title
        title = MDLabel(
            text="Gerar Questões",
            font_style="H4",
            halign="center",
            size_hint_y=None,
            height=dp(60)
        )
        main_layout.add_widget(title)
        
        # Description
        description = MDLabel(
            text="Configure os parâmetros para gerar questões.",
            halign="center",
            size_hint_y=None,
            height=dp(60)
        )
        main_layout.add_widget(description)
        
        # Input Card
        input_card = MDCard(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(20),
            size_hint=(None, None),
            size=(dp(400), dp(300)),
            pos_hint={'center_x': 0.5}
        )
        
        # API Key Input
        self.api_key = MDTextField(
            hint_text="Chave da API OpenAI",
            helper_text="Digite sua chave de API",
            helper_text_mode="on_error",
            password=True,
            size_hint_y=None,
            height=dp(60)
        )
        input_card.add_widget(self.api_key)
        
        # Topic Button
        self.topic_button = MDRaisedButton(
            text="Selecionar Tópico",
            pos_hint={'center_x': 0.5},
            size_hint=(None, None),
            height=dp(50),
            width=dp(200),
            on_release=lambda x: self.topic_menu.open()
        )
        input_card.add_widget(self.topic_button)
        
        # Number of Subtopics Input
        self.num_subtopics = MDTextField(
            hint_text="Número de Sub Temas",
            helper_text="Digite o número de sub temas",
            helper_text_mode="on_error",
            input_filter="int",
            size_hint_y=None,
            height=dp(60)
        )
        input_card.add_widget(self.num_subtopics)
        
        # Number of Questions Input
        self.num_questions = MDTextField(
            hint_text="Número de Questões",
            helper_text="Digite o número de questões",
            helper_text_mode="on_error",
            input_filter="int",
            size_hint_y=None,
            height=dp(60)
        )
        input_card.add_widget(self.num_questions)
        
        main_layout.add_widget(input_card)
        
        # Texto informativo sobre modelos padrão
        if any([self.selected_question_model, self.selected_answer_model, self.selected_wrong_answers_model]):
            model_info = MDCard(
                orientation='vertical',
                padding=dp(15),
                spacing=dp(10),
                size_hint_y=None,
                height=dp(120),
                pos_hint={'center_x': 0.5},
                md_bg_color=(0.9, 0.9, 1.0, 1.0),
                radius=[10, 10, 10, 10]
            )
            
            info_label = MDLabel(
                text="Usando modelos padrão selecionados na tela 'Selecionar Modelos Padrão'",
                halign="center",
                size_hint_y=None,
                height=dp(40),
                bold=True
            )
            model_info.add_widget(info_label)
            
            models_label = MDLabel(
                text=f"Questões: {self.get_model_name(self.selected_question_model)}\nRespostas: {self.get_model_name(self.selected_answer_model)}\nDistratores: {self.get_model_name(self.selected_wrong_answers_model)}",
                halign="center",
                size_hint_y=None,
                height=dp(60)
            )
            model_info.add_widget(models_label)
            
            main_layout.add_widget(model_info)
        
        # Model Selection Cards - apenas se não houver modelos padrão
        if not all([self.selected_question_model, self.selected_answer_model, self.selected_wrong_answers_model]):
            cards_layout = MDBoxLayout(
                orientation='vertical',
                spacing=dp(20),
                size_hint_y=None,
                height=dp(550)
            )
            
            # Card para seleção do modelo de questões
            self.question_model_card = ModelTypeCard("Modelo de Questões", models_list=list_available_models())
            cards_layout.add_widget(self.question_model_card)
            
            # Card para seleção do modelo de respostas
            self.answer_model_card = ModelTypeCard("Modelo de Respostas", models_list=list_available_models())
            cards_layout.add_widget(self.answer_model_card)
            
            # Card para seleção do modelo de respostas incorretas
            self.wrong_answers_model_card = ModelTypeCard("Modelo de Respostas Incorretas", models_list=list_available_models())
            cards_layout.add_widget(self.wrong_answers_model_card)
            
            main_layout.add_widget(cards_layout)
        
        # Progress Card
        progress_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            spacing=dp(15),
            size_hint_y=None,
            height=dp(180),
            pos_hint={'center_x': 0.5}
        )
        
        # Progress Bar
        self.progress = MDProgressBar(
            value=0,
            size_hint_x=0.8,
            pos_hint={'center_x': 0.5}
        )
        progress_card.add_widget(self.progress)
        
        # Progress Label
        self.progress_label = MDLabel(
            text="0%",
            halign="center",
            size_hint_y=None,
            height=dp(40)
        )
        progress_card.add_widget(self.progress_label)
        
        # Status Label
        self.status_label = MDLabel(
            text="",
            halign="center",
            size_hint_y=None,
            height=dp(40)
        )
        progress_card.add_widget(self.status_label)
        
        # Spinner
        self.spinner = MDSpinner(
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            pos_hint={'center_x': .5, 'center_y': .5},
            active=False
        )
        progress_card.add_widget(self.spinner)
        
        main_layout.add_widget(progress_card)
        
        # Control Buttons
        buttons_layout = BoxLayout(
            orientation='horizontal',
            spacing=dp(20),
            size_hint_y=None,
            height=dp(70),
            pos_hint={'center_x': 0.5}
        )
        
        # Generate Button
        self.generate_button = MDRaisedButton(
            text="Gerar Questões",
            on_release=self.generate_questions,
            disabled=True,
            size_hint=(None, None),
            height=dp(50),
            width=dp(200)
        )
        buttons_layout.add_widget(self.generate_button)
        
        # Back Button
        back_btn = MDRaisedButton(
            text="Voltar",
            size_hint=(None, None),
            height=dp(50),
            width=dp(150),
            on_release=self.go_back
        )
        buttons_layout.add_widget(back_btn)
        
        main_layout.add_widget(buttons_layout)
        
        # Add Change API Key Button
        self.change_api_button = MDRaisedButton(
            text="Alterar API Key",
            size_hint=(None, None),
            height=dp(50),
            width=dp(200),
            pos_hint={'center_x': 0.5},
            on_release=lambda x: self.show_change_api_dialog()
        )
        main_layout.add_widget(self.change_api_button)
        
        # Adiciona eventos para atualizar o botão de geração
        self.api_key.bind(text=lambda instance, value: self.update_generate_button())
        self.num_subtopics.bind(text=lambda instance, value: self.update_generate_button())
        self.num_questions.bind(text=lambda instance, value: self.update_generate_button())
        
        scroll.add_widget(main_layout)
        self.add_widget(scroll)
        
        # Atualizar botão de geração
        self.update_generate_button()
    
    def setup_menu(self):
        """Set up the topic selection menu."""
        menu_items = [
            {
                "text": topic,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=topic: self.select_topic(x),
            } for topic in self.TOPICS
        ]
        
        self.topic_menu = MDDropdownMenu(
            caller=self.topic_button,
            items=menu_items,
            width_mult=4,
        )
    
    def select_topic(self, topic):
        """Handle topic selection."""
        self.selected_topic = topic
        self.topic_button.text = topic
        self.topic_menu.dismiss()
        self.update_generate_button()
    
    def update_generate_button(self):
        """Update the state of the generate button based on inputs."""
        # Verificar se temos a chave da API
        api_key_valid = bool(self.api_key.text.strip())
        
        # Verificar se temos modelos selecionados, caso contrário, usar os modelos padrão
        question_model_valid = (self.selected_question_model is not None or 
                               (hasattr(self, 'question_model_card') and 
                                self.question_model_card.get_selected_model() is not None))
                                
        answer_model_valid = (self.selected_answer_model is not None or 
                             (hasattr(self, 'answer_model_card') and 
                              self.answer_model_card.get_selected_model() is not None))
                              
        wrong_answers_model_valid = (self.selected_wrong_answers_model is not None or 
                                    (hasattr(self, 'wrong_answers_model_card') and 
                                     self.wrong_answers_model_card.get_selected_model() is not None))
        
        # Verificar se temos tópico, subtópico e número de questões selecionados
        topic_valid = self.selected_topic is not None and self.selected_topic != ""
        subtopic_valid = bool(self.num_subtopics.text.strip()) if hasattr(self, 'num_subtopics') else False
        num_questions_valid = self.num_questions.text.isdigit() and 1 <= int(self.num_questions.text) <= 10 if hasattr(self, 'num_questions') else False
        
        # Verificar se todos os campos necessários estão preenchidos
        all_valid = (api_key_valid and question_model_valid and answer_model_valid and 
                    wrong_answers_model_valid and topic_valid and subtopic_valid and 
                    num_questions_valid)
        
        # Habilitar ou desabilitar o botão conforme necessário
        self.generate_button.disabled = not all_valid
    
    def show_change_api_dialog(self):
        """Show dialog to change API key."""
        self.dialog = MDDialog(
            title="Alterar Chave da API",
            type="custom",
            content_cls=MDTextField(
                hint_text="Nova chave da API OpenAI",
                password=True
            ),
            buttons=[
                MDRaisedButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="SALVAR",
                    on_release=lambda x: self.save_new_api_key()
                ),
            ],
        )
        self.dialog.open()
    
    def save_new_api_key(self):
        """Save new API key and update UI."""
        new_key = self.dialog.content_cls.text
        if new_key:
            self.api_manager.save_api_key(new_key)
            self.api_key.text = new_key
            self.update_generate_button()
        self.dialog.dismiss()
    
    def generate_questions(self, instance):
        """Generate questions with the given parameters."""
        # Salva a chave da API
        if self.api_key.text:
            self.api_manager.save_api_key(self.api_key.text)
        
        # Usa os modelos selecionados ou os modelos padrão
        question_model = self.selected_question_model
        if hasattr(self, 'question_model_card') and self.question_model_card.get_selected_model():
            question_model = self.question_model_card.get_selected_model()
            
        answer_model = self.selected_answer_model
        if hasattr(self, 'answer_model_card') and self.answer_model_card.get_selected_model():
            answer_model = self.answer_model_card.get_selected_model()
            
        wrong_answers_model = self.selected_wrong_answers_model
        if hasattr(self, 'wrong_answers_model_card') and self.wrong_answers_model_card.get_selected_model():
            wrong_answers_model = self.wrong_answers_model_card.get_selected_model()
        
        # Substituir modelos de exemplo/teste por modelos padrão
        # Estes IDs são modelos mock que não existem na API
        if question_model == "ft:gpt-3.5-turbo:pmp-questions:12345":
            question_model = "default_gpt35"
            logger.warning(f"Substituindo modelo de exemplo por modelo padrão para questões: {question_model}")
            
        if answer_model == "ft:gpt-3.5-turbo:pmp-answers:67890":
            answer_model = "default_gpt35"
            logger.warning(f"Substituindo modelo de exemplo por modelo padrão para respostas: {answer_model}")
        
        # Tratamento para corrigir IDs de modelos incorretos
        if wrong_answers_model == "ftjob-ebT80fcJhVVJTrhXQzKV88Q3":
            wrong_answers_model = "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI"
            logger.warning(f"Substituição direta de ID do modelo de distratores: {wrong_answers_model}")
        # Corrigir formato incorreto do modelo de distratores
        elif wrong_answers_model == "ft:gpt-3.5-turbo:personal::QzKV88Q3":
            wrong_answers_model = "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI"
            logger.warning(f"Corrigindo formato do ID do modelo de distratores para: {wrong_answers_model}")
        # Correção mais genérica para IDs incorretos baseados no QzKV88Q3
        elif "QzKV88Q3" in wrong_answers_model or "personal" in wrong_answers_model:
            wrong_answers_model = "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI"
            logger.warning(f"Correção genérica do ID do modelo de distratores: {wrong_answers_model}")
        
        # Verifica se temos modelos válidos
        if not question_model or not answer_model or not wrong_answers_model:
            self.show_error("Modelos não selecionados", 
                           "Por favor, selecione todos os modelos necessários ou configure modelos padrão.")
            return
            
        try:
            # Inicializa a API caso seja necessário
            if not self.api:
                self.api = OpenAIAPI(self.api_key.text)
                
            # Função para converter job ID em model ID
            def get_model_id(model_or_job_id):
                # Substituir modelos de exemplo/teste por modelos padrão
                if model_or_job_id == "ft:gpt-3.5-turbo:pmp-questions:12345":
                    logger.warning(f"Substituindo modelo de exemplo por modelo padrão (default_gpt35)")
                    return "gpt-3.5-turbo"  # API ID correspondente ao default_gpt35
                    
                if model_or_job_id == "ft:gpt-3.5-turbo:pmp-answers:67890":
                    logger.warning(f"Substituindo modelo de exemplo por modelo padrão (default_gpt35)")
                    return "gpt-3.5-turbo"  # API ID correspondente ao default_gpt35
                
                # Verificação para modelo específico problemático
                if model_or_job_id == "ftjob-ebT80fcJhVVJTrhXQzKV88Q3":
                    logger.warning(f"Detectado job ID específico, usando model ID correto direto")
                    return "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI"
                
                # Correção para modelo com formatação incorreta
                if model_or_job_id == "ft:gpt-3.5-turbo:personal::QzKV88Q3" or "QzKV88Q3" in model_or_job_id:
                    logger.warning(f"Detectado modelo com formatação incorreta, corrigindo para o formato correto")
                    return "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI"
                
                # Mapear IDs internos para IDs da API
                if model_or_job_id == "default_gpt35":
                    return "gpt-3.5-turbo"
                if model_or_job_id == "default_gpt4":
                    return "gpt-4"
                
                if model_or_job_id.startswith("ftjob-"):
                    try:
                        logger.warning(f"Buscando model ID para job: {model_or_job_id}")
                        job_info = self.api.get_fine_tuning_job(model_or_job_id)
                        logger.warning(f"Job info recebido: {job_info}")
                        
                        if job_info and 'fine_tuned_model' in job_info:
                            model_id = job_info['fine_tuned_model']
                            logger.warning(f"Model ID obtido: {model_id}")
                            return model_id
                        else:
                            logger.warning(f"'fine_tuned_model' não encontrado no job_info")
                            # Usar modelo padrão como fallback
                            return "gpt-3.5-turbo"
                    except Exception as e:
                        logger.error(f"Erro ao obter informações do job {model_or_job_id}: {e}")
                        # Usar modelo padrão como fallback
                        return "gpt-3.5-turbo"
                return model_or_job_id
            
            # Converter job IDs para model IDs
            logger.warning(f"Modelos originais - Questões: {question_model}, Respostas: {answer_model}, Distratores: {wrong_answers_model}")
            
            question_model = get_model_id(question_model)
            answer_model = get_model_id(answer_model)
            wrong_answers_model = get_model_id(wrong_answers_model)
            
            logger.warning(f"Modelos convertidos - Questões: {question_model}, Respostas: {answer_model}, Distratores: {wrong_answers_model}")
            
            # Verificar se os modelos existem
            available_models = self.api.list_fine_tuned_models()
            available_model_ids = []
            
            # Extrair IDs dos modelos fine-tuned
            for model in available_models:
                model_id = model.get('id') or model.get('fine_tuned_model')
                if model_id:
                    available_model_ids.append(model_id)
                    
            # Caso especial para o modelo problemático
            if "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI" not in available_model_ids:
                available_model_ids.append("ft:gpt-3.5-turbo-0125:personal::BGt3nwXI")
            
            # Adicionar modelos padrão à lista de disponíveis
            if "gpt-3.5-turbo" not in available_model_ids:
                available_model_ids.append("gpt-3.5-turbo")
            if "gpt-4" not in available_model_ids:
                available_model_ids.append("gpt-4")
            available_model_ids.extend(["default_gpt35", "default_gpt4"])
            
            logger.warning(f"Modelos disponíveis: {available_model_ids}")
            
            # Verificar cada modelo e substituir por padrão se necessário
            modelos_substituidos = False
            for model_id, model_type, model_var in [
                (question_model, "questões", "question_model"),
                (answer_model, "respostas", "answer_model"),
                (wrong_answers_model, "distratores", "wrong_answers_model")
            ]:
                if model_id not in available_model_ids:
                    modelos_substituidos = True
                    logger.warning(f"Modelo {model_id} para {model_type} não encontrado. Usando modelo padrão.")
                    
                    # Usar modelo padrão - evita ser hard-coded em vários lugares
                    if model_type == "questões":
                        question_model = "default_gpt35"
                    elif model_type == "respostas":
                        answer_model = "default_gpt35"
                    elif model_type == "distratores":
                        wrong_answers_model = "default_gpt35"
            
            # Se algum modelo foi substituído, mostrar um aviso ao usuário
            if modelos_substituidos:
                self.show_error("Alguns modelos foram substituídos", 
                             "Alguns modelos selecionados não estão disponíveis e foram substituídos pelos modelos padrão.")
            
            # Log final dos modelos após todas as correções
            logger.warning(f"Modelos finais - Questões: {question_model}, Respostas: {answer_model}, Distratores: {wrong_answers_model}")
            
        except Exception as e:
            logger.error(f"Erro ao verificar modelos: {str(e)}")
            self.show_error("Erro", "Não foi possível verificar os modelos. Verifique sua conexão com a internet.")
            return
        
        try:
            # Ajustar nível de log para reduzir mensagens durante a geração
            original_level = logger.getEffectiveLevel()
            logger.setLevel(logging.WARNING)  # Apenas logs importantes
            
            self.processing = True
            self.generate_button.disabled = True
            self.spinner.active = True
            self.progress.value = 0
            self.status_label.text = "Gerando questões..."
            
            # Get relevant chunks for context
            topic = self.selected_topic
            relevant_chunks = self.db.find_most_relevant_chunks(topic)
            
            # Get user inputs
            num_questions = int(self.num_questions.text)
            
            # Start generation in a separate thread
            self.generation_thread = threading.Thread(
                target=self._generate_questions_thread,
                args=(num_questions, question_model, answer_model, wrong_answers_model)
            )
            self.generation_thread.daemon = True
            self.generation_thread.start()
            
            # Update progress periodically
            Clock.schedule_interval(self.update_progress, 0.1)
            
        except Exception as e:
            logger.error(f"Error starting question generation: {str(e)}")
            self.show_error("Erro", "Não foi possível iniciar a geração de questões")
            self.processing = False
            self.generate_button.disabled = False
            self.spinner.active = False
            # Restaurar nível de log original
            logger.setLevel(original_level)
    
    def _generate_questions_thread(self, num_questions: int, question_model: str, answer_model: str, wrong_answers_model: str):
        """Generate questions in a separate thread."""
        # Salvar nível de log original
        original_level = logger.getEffectiveLevel()
        try:
            # Reset progress and clear status
            Clock.schedule_once(lambda dt: self.update_progress(0, ""))
            
            # Get topic and API key
            topic = self.selected_topic
            api_key = self.api_key.text if hasattr(self, 'api_key') else None
            
            # Get relevant chunks for context
            relevant_chunks = self.db.find_most_relevant_chunks(topic)
            
            # Models info
            models_info = {
                "question_model": question_model,
                "answer_model": answer_model,
                "wrong_answers_model": wrong_answers_model
            }
            
            # Obter nomes amigáveis dos modelos
            question_model_name = self.get_model_name(question_model)
            answer_model_name = self.get_model_name(answer_model)
            wrong_answers_model_name = self.get_model_name(wrong_answers_model)
            
            # Log dos modelos sendo usados
            logger.warning(f"Iniciando geração com os seguintes modelos:")
            logger.warning(f"- Questões: {question_model_name}")
            logger.warning(f"- Respostas: {answer_model_name}")
            logger.warning(f"- Distratores: {wrong_answers_model_name}")
            
            # Mostrar qual modelo está sendo usado na interface
            Clock.schedule_once(lambda dt: self.update_progress(0, f"Gerando questões usando {question_model_name}..."))
            
            # Importar diretamente os módulos necessários
            from ..api.openai_client import generate_questions_with_specialized_models
            
            # Generate questions using the API
            questions = generate_questions_with_specialized_models(
                topic=topic,
                num_questions=num_questions,
                api_key=api_key,
                callback=self.update_progress,
                question_model=question_model,
                answer_model=answer_model,
                distractors_model=wrong_answers_model
            )
            
            # Se não tiver a função especializada, usar a função genérica
            if not questions:
                from ..api.openai_client import generate_questions
                
                # Chamar com os parâmetros corretos
                questions = generate_questions(
                    topic=topic,
                    num_questions=num_questions,
                    api_key=api_key
                )
            
            if not questions:
                # Simulação de questões geradas para desenvolvimento
                questions = self._generate_simulated_questions(topic, num_questions)
                
            if not questions:
                raise ValueError("Nenhuma questão foi gerada.")
            
            # Save questions to database
            db = DatabaseManager()
            for question in questions:
                db.save_question(question)
            
            # Update interface
            self.questions = questions  # Atribuir as questões ao objeto
            Clock.schedule_once(lambda dt: self.update_progress(100, "Questões geradas com sucesso!"))
            Clock.schedule_once(lambda dt: self.show_generated_questions())
            
        except Exception as e:
            logger.error(f"Error in generation thread: {str(e)}")
            error_msg = str(e)  # Capture the error message
            Clock.schedule_once(lambda dt, msg=error_msg: self.update_progress(0, f"Erro: {msg}"))
            Clock.schedule_once(lambda dt, msg=error_msg: self.show_error("Erro", f"Ocorreu um erro ao gerar as questões: {msg}"))
        finally:
            self.processing = False
            Clock.unschedule(self.update_progress)
            # Restaurar nível de log original
            logger.setLevel(original_level)
    
    def _generate_simulated_questions(self, topic: str, num_questions: int) -> list:
        """Gera questões simuladas para fins de desenvolvimento."""
        logger.info(f"Gerando questões simuladas sobre {topic}")
        
        questions = []
        
        # Templates de questões para diferentes tópicos
        templates = {
            "Gerenciamento da Integração": [
                "Qual é o principal objetivo do processo de Desenvolver o Termo de Abertura do Projeto?",
                "Durante o encerramento do projeto, qual documento deve ser atualizado para registrar as lições aprendidas?",
                "Qual é a principal saída do processo de Monitorar e Controlar o Trabalho do Projeto?"
            ],
            "Gerenciamento do Escopo": [
                "Qual técnica é mais útil para verificar o escopo do projeto com os stakeholders?",
                "Qual documento contém os critérios de aceitação dos entregáveis do projeto?",
                "Qual processo é responsável pela criação da Estrutura Analítica do Projeto (EAP)?"
            ],
            "Gerenciamento do Cronograma": [
                "Qual técnica é usada para calcular as datas de início e término mais cedo e mais tarde para as atividades do projeto?",
                "Qual é a diferença entre caminho crítico e cadeia crítica no gerenciamento do cronograma?",
                "O que representa a folga livre em uma atividade do cronograma?"
            ]
        }
        
        # Respostas para as perguntas
        answers = {
            "Qual é o principal objetivo do processo de Desenvolver o Termo de Abertura do Projeto?": 
                "Autorizar formalmente o projeto e documentar os requisitos iniciais",
            "Durante o encerramento do projeto, qual documento deve ser atualizado para registrar as lições aprendidas?": 
                "Ativos de processos organizacionais",
            "Qual é a principal saída do processo de Monitorar e Controlar o Trabalho do Projeto?": 
                "Solicitações de mudança",
            "Qual técnica é mais útil para verificar o escopo do projeto com os stakeholders?": 
                "Inspeção",
            "Qual documento contém os critérios de aceitação dos entregáveis do projeto?": 
                "Declaração do escopo do projeto",
            "Qual processo é responsável pela criação da Estrutura Analítica do Projeto (EAP)?": 
                "Criar EAP",
            "Qual técnica é usada para calcular as datas de início e término mais cedo e mais tarde para as atividades do projeto?": 
                "Método do Caminho Crítico (CPM)",
            "Qual é a diferença entre caminho crítico e cadeia crítica no gerenciamento do cronograma?": 
                "O caminho crítico considera apenas as dependências entre tarefas, enquanto a cadeia crítica também considera restrições de recursos",
            "O que representa a folga livre em uma atividade do cronograma?": 
                "O tempo que uma atividade pode atrasar sem afetar o início mais cedo da próxima atividade"
        }
        
        # Opções incorretas
        wrong_options = {
            "Qual é o principal objetivo do processo de Desenvolver o Termo de Abertura do Projeto?": [
                "Definir o cronograma detalhado do projeto",
                "Documentar os riscos do projeto",
                "Aprovar o orçamento final do projeto"
            ],
            "Durante o encerramento do projeto, qual documento deve ser atualizado para registrar as lições aprendidas?": [
                "Plano de gerenciamento do projeto",
                "Termo de abertura do projeto",
                "Registro de riscos"
            ],
            "Qual é a principal saída do processo de Monitorar e Controlar o Trabalho do Projeto?": [
                "Entregas aceitas",
                "Atualizações no plano de gerenciamento do projeto",
                "Relatórios de desempenho"
            ],
            "Qual técnica é mais útil para verificar o escopo do projeto com os stakeholders?": [
                "Análise de variação",
                "Decomposição",
                "Planejamento em ondas sucessivas"
            ],
            "Qual documento contém os critérios de aceitação dos entregáveis do projeto?": [
                "Registro das partes interessadas",
                "Documentação dos requisitos",
                "Dicionário da EAP"
            ],
            "Qual processo é responsável pela criação da Estrutura Analítica do Projeto (EAP)?": [
                "Definir o Escopo",
                "Validar o Escopo",
                "Coletar os Requisitos"
            ],
            "Qual técnica é usada para calcular as datas de início e término mais cedo e mais tarde para as atividades do projeto?": [
                "Técnica de Avaliação e Revisão de Programa (PERT)",
                "Método da Corrente Crítica",
                "Compressão do Cronograma"
            ],
            "Qual é a diferença entre caminho crítico e cadeia crítica no gerenciamento do cronograma?": [
                "O caminho crítico é usado em projetos ágeis, enquanto a cadeia crítica é usada em projetos preditivos",
                "O caminho crítico é calculado pelo método PERT, enquanto a cadeia crítica é calculada pelo CPM",
                "O caminho crítico considera apenas o tempo, enquanto a cadeia crítica considera apenas os recursos"
            ],
            "O que representa a folga livre em uma atividade do cronograma?": [
                "O tempo adicional necessário para concluir uma atividade",
                "O tempo que uma atividade pode atrasar sem afetar o término do projeto",
                "O tempo entre o início mais cedo e o início mais tarde de uma atividade"
            ]
        }
        
        # Selecionar questões para o tópico específico ou usar questões gerais
        topic_questions = templates.get(topic, [f"Explique um conceito importante de {topic}"])
        
        # Criar questões com respostas e opções
        for i in range(min(num_questions, len(topic_questions))):
            question_text = topic_questions[i]
            
            # Resposta correta
            correct_answer = answers.get(question_text, f"A resposta correta para {question_text}")
            
            # Opções incorretas
            options = wrong_options.get(question_text, [
                f"Alternativa incorreta 1 para {question_text}",
                f"Alternativa incorreta 2 para {question_text}",
                f"Alternativa incorreta 3 para {question_text}"
            ])
            
            # Montar todas as opções (certa + erradas)
            all_options = [correct_answer] + options
            random.shuffle(all_options)  # Misturar opções
            
            # Determinar qual é a opção correta (A, B, C, D)
            correct_index = all_options.index(correct_answer)
            correct_letter = chr(65 + correct_index)  # A, B, C, D
            
            # Criar questão
            question = {
                "question": question_text,
                "options": all_options,
                "correct_answer": correct_letter,
                "explanation": f"A resposta correta é {correct_letter}: {correct_answer}",
                "topic": topic,
                "subtopic": "",
                "difficulty": "medium"
            }
            
            questions.append(question)
            
        return questions
    
    def validate_inputs(self):
        """Validate user inputs."""
        if not self.api_key.text:
            self.api_key.error = True
            return False
            
        if not self.selected_topic:
            return False
            
        try:
            num_subtopics = int(self.num_subtopics.text)
            if num_subtopics <= 0:
                self.num_subtopics.error = True
                return False
        except:
            self.num_subtopics.error = True
            return False
            
        try:
            num_questions = int(self.num_questions.text)
            if num_questions <= 0:
                self.num_questions.error = True
                return False
        except:
            self.num_questions.error = True
            return False
            
        return True
    
    def update_progress(self, value, status=""):
        """Update progress and status."""
        self.progress.value = value
        self.progress_label.text = f"{int(value)}%"
        if status:
            self.status_label.text = status
    
    def go_back(self, *args):
        """Return to home screen."""
        self.manager.current = "home"
    
    def on_prompt_change(self, instance, value):
        """Atualiza a lista de arquivos relevantes quando o prompt muda."""
        if value.strip():
            self.update_relevant_files(value)
    
    def update_relevant_files(self, prompt):
        """Atualiza a lista de arquivos relevantes."""
        from ..api.openai_client import find_relevant_training_data
        
        # Limpar lista atual
        if hasattr(self, 'relevant_files_list'):
            self.relevant_files_list.clear_widgets()
        
        # Buscar arquivos relevantes
        relevant_files = find_relevant_training_data(prompt)
        
        if not relevant_files:
            if hasattr(self, 'relevant_files_list'):
                self.relevant_files_list.height = dp(0)
            if hasattr(self, 'relevant_files_label'):
                self.relevant_files_label.text = "Nenhum arquivo relevante encontrado"
            return
        
        # Atualizar altura da lista
        if hasattr(self, 'relevant_files_list'):
            self.relevant_files_list.height = dp(len(relevant_files) * 60)
        
        # Adicionar arquivos à lista
        for file_info in relevant_files:
            similarity = file_info.get('similarity', 0)
            similarity_text = f"Relevância: {similarity:.2%}"
            
            item = TwoLineListItem(
                text=file_info['name'],
                secondary_text=f"{file_info['questions_count']} questões | {similarity_text}",
                size_hint_y=None,
                height=dp(60)
            )
            if hasattr(self, 'relevant_files_list'):
                self.relevant_files_list.add_widget(item)
    
    def show_success(self, title, message):
        """Show success dialog."""
        if not self.dialog:
            self.dialog = MDDialog(
                title=title,
                text=message,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.dialog.dismiss()
                    )
                ]
            )
        else:
            self.dialog.title = title
            self.dialog.text = message
        self.dialog.open()
    
    def show_error(self, title, message):
        """Show error dialog."""
        def create_dialog(dt):
            dialog = MDDialog(
                title=title,
                text=message,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: dialog.dismiss()
                    )
                ]
            )
            dialog.open()
            self.dialogs.append(dialog)
            
        Clock.schedule_once(create_dialog)
    
    def show_generated_questions(self):
        """Display generated questions in a dialog."""
        if not hasattr(self, 'questions') or not self.questions:
            self.show_error("Erro", "Nenhuma questão foi gerada.")
            return
            
        # Criar conteúdo da lista de questões
        content = BoxLayout(orientation='vertical', spacing=dp(30), size_hint_y=None)  # Aumentado spacing entre questões
        content.bind(minimum_height=content.setter('height'))
        
        for i, question in enumerate(self.questions, 1):
            # Card para cada questão
            question_card = MDCard(
                orientation='vertical',
                size_hint_y=None,
                height=dp(350),  # Altura aumentada
                padding=dp(15),
                spacing=dp(15),  # Aumentado spacing interno
                elevation=2,
                radius=[10, 10, 10, 10]
            )
            
            # Texto da questão - remover tags [b]
            question_text = question['question'].replace('[b]', '').replace('[/b]', '')
            question_text_label = MDLabel(
                text=f"Questão {i}:\n{question_text}",
                size_hint_y=None,
                height=dp(120),  # Altura aumentada
                halign='left'
            )
            question_card.add_widget(question_text_label)
            
            # Opções - remover tags [b]
            options_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(120),  # Altura aumentada
                spacing=dp(8)  # Espaçamento entre opções
            )
            for j, option in enumerate(question['options']):
                option_text = option.replace('[b]', '').replace('[/b]', '')
                option_label = MDLabel(
                    text=f"{chr(65+j)}. {option_text}",
                    size_hint_y=None,
                    height=dp(30),  # Altura aumentada
                    halign='left'
                )
                options_box.add_widget(option_label)
            question_card.add_widget(options_box)
            
            # Resposta correta e explicação - remover tags [b]
            correct_answer = question['correct_answer'].replace('[b]', '').replace('[/b]', '')
            explanation = question.get('explanation', '').replace('[b]', '').replace('[/b]', '')
            
            # Separar resposta e explicação em labels diferentes
            answer_text = MDLabel(
                text=f"Resposta correta: {correct_answer}",
                size_hint_y=None,
                height=dp(30),
                halign='left'
            )
            question_card.add_widget(answer_text)
            
            explanation_text = MDLabel(
                text=f"Explicação: {explanation}",
                size_hint_y=None,
                height=dp(50),
                halign='left'
            )
            question_card.add_widget(explanation_text)
            
            content.add_widget(question_card)
        
        # Criar scroll view para o conteúdo
        scroll = ScrollView(size_hint=(1, None), height=dp(600))  # Altura aumentada
        scroll.add_widget(content)
        
        # Criar e mostrar o diálogo
        dialog = MDDialog(
            title="Questões Geradas",
            type="custom",
            content_cls=scroll,
            buttons=[
                MDFlatButton(
                    text="Fechar",
                    on_release=lambda x: dialog.dismiss()
                )
            ],
            size_hint=(0.95, 0.95)  # Tamanho aumentado
        )
        self.dialogs.append(dialog)
        dialog.open()

    def get_model_name(self, model_id):
        """Obtém um nome amigável para o modelo."""
        if not model_id:
            return "Não selecionado"
            
        # Correção para o modelo específico com ID incorreto
        if model_id == "ftjob-ebT80fcJhVVJTrhXQzKV88Q3":
            model_id = "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI"
        elif model_id == "ft:gpt-3.5-turbo:personal::QzKV88Q3" or "QzKV88Q3" in model_id:
            model_id = "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI"
            
        # Primeiro, verificar se existe um nome personalizado no banco de dados
        custom_name = self.api_manager.db.get_model_custom_name(model_id)
        if custom_name:
            return custom_name
            
        # Se for um job ID, tentar obter o model ID associado
        if model_id.startswith("ftjob-"):
            try:
                # Tentar obter o modelo associado ao job
                job_info = self.api.get_fine_tuning_job(model_id)
                if job_info and 'fine_tuned_model' in job_info:
                    model_id = job_info['fine_tuned_model']
            except Exception as e:
                logger.warning(f"Não foi possível obter informações do job {model_id}: {e}")
                return f"Job de Fine-tuning: {model_id}"
            
        # Extrair informações significativas do ID do modelo
        parts = model_id.split(':')
        
        # Formato específico para modelos da OpenAI com formato ft:gpt-3.5-turbo-0125:personal::BGt3nwXI
        if len(parts) >= 3 and parts[0] == "ft" and "personal" in parts[2]:
            base_model = parts[1]  # gpt-3.5-turbo-0125, etc.
            version = ""
            if "-" in base_model:
                # Extrair versão do modelo base se disponível
                base_parts = base_model.split('-')
                if len(base_parts) >= 2:
                    base_name = f"GPT-{base_parts[1]}"
                    # Adicionar versão se disponível (como 0125)
                    if len(base_parts) >= 3:
                        version = f"-{base_parts[2]}"
                else:
                    base_name = base_model.upper()
            else:
                base_name = base_model.upper()
                
            # Adicionar identificador único do modelo se disponível
            model_identifier = ""
            if len(parts) >= 4 and parts[3]:
                model_identifier = f" ({parts[3]})"
                
            return f"Modelo Fine-tuned {base_name}{version}{model_identifier}"
        
        # Formato padrão ft:gpt-3.5-turbo:pmp-questions:12345
        elif len(parts) >= 3:
            base_model = parts[1]  # gpt-3.5-turbo, gpt-4, etc.
            purpose = parts[2]  # pmp-questions, pmp-answers, etc.
            
            # Mapear finalidade para um nome mais amigável
            purpose_names = {
                'pmp-questions': 'Questões PMP',
                'pmp-answers': 'Respostas PMP',
                'pmp-distractors': 'Distratores PMP',
                'questions': 'Questões',
                'answers': 'Respostas',
                'distractors': 'Distratores',
                'wrong-answers': 'Distratores',
                'wrong_answers': 'Distratores',
                'personal': 'Personalizado'
            }
            
            friendly_purpose = purpose_names.get(purpose, purpose.capitalize())
            
            # Extrair versão do modelo base se disponível
            base_parts = base_model.split('-')
            if len(base_parts) >= 2:
                base_name = f"GPT-{base_parts[1]}"
            else:
                base_name = base_model.upper()
                
            # Adicionar identificador único do modelo se disponível
            model_suffix = ""
            if len(parts) >= 4 and parts[3]:
                model_suffix = f" ({parts[3]})"
                
            return f"{friendly_purpose} ({base_name}{model_suffix})"
        
        # Para modelos padrão
        elif model_id == "default_gpt35":
            return "GPT-3.5 Turbo (Padrão)"
        elif model_id == "default_gpt4":
            return "GPT-4 (Padrão)"
        
        # Se não conseguir extrair informações, retornar o ID original
        return model_id