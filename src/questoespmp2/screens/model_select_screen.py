#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tela para seleção de modelos padrão para geração de questões.
"""

import os
import json
import logging
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty
from kivy.uix.scrollview import ScrollView

from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox

from ..api.openai_api import OpenAIAPI
from ..utils.api_manager import APIManager

logger = logging.getLogger(__name__)

class ModelSelectScreen(MDScreen):
    """
    Tela para seleção de modelos padrão de IA.
    """
    
    def __init__(self, **kwargs):
        """Inicializa a tela."""
        super().__init__(**kwargs)
        self.name = "model_select"
        self.api_manager = APIManager()
        self.api = None
        self.dialog = None
        self.models_changed = False
        
        # Dicionário para armazenar os modelos selecionados para cada tipo
        self.selected_models = {
            'question': None,
            'answer': None,
            'wrong_answers': None
        }
        
        # Lista de modelos disponíveis
        self.available_models = {
            'question': [],
            'answer': [],
            'wrong_answers': []
        }
        
        self.setup_ui()
        self.load_available_models()
    
    def setup_ui(self):
        """Configura a interface da tela."""
        main_layout = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(20)
        )
        
        # Título
        title = MDLabel(
            text="Selecionar Modelos Padrão",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        main_layout.add_widget(title)
        
        # Descrição
        description = MDLabel(
            text="Selecione os modelos padrão para geração de questões, respostas e distratores.",
            size_hint_y=None,
            height=dp(40)
        )
        main_layout.add_widget(description)
        
        # Scroll View para os cards de modelos
        scroll = ScrollView()
        self.cards_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(20),
            size_hint_y=None
        )
        self.cards_layout.bind(minimum_height=self.cards_layout.setter('height'))
        
        # Adiciona os cards de seleção de modelo
        self.question_card = self.create_model_card("Modelo para Questões", "question")
        self.answer_card = self.create_model_card("Modelo para Respostas", "answer")
        self.wrong_answers_card = self.create_model_card("Modelo para Distratores", "wrong_answers")
        
        self.cards_layout.add_widget(self.question_card)
        self.cards_layout.add_widget(self.answer_card)
        self.cards_layout.add_widget(self.wrong_answers_card)
        
        scroll.add_widget(self.cards_layout)
        main_layout.add_widget(scroll)
        
        # Botões
        buttons_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        # Botão de importação de modelos
        import_btn = MDRaisedButton(
            text="Importar Modelo",
            on_release=self.show_import_dialog,
            size_hint_x=0.25
        )
        buttons_layout.add_widget(import_btn)
        
        # Botão de reload dos modelos
        reload_btn = MDRaisedButton(
            text="Recarregar Modelos",
            on_release=self.reload_models,
            size_hint_x=0.25
        )
        buttons_layout.add_widget(reload_btn)
        
        # Botão para limpar todos os modelos
        reset_btn = MDRaisedButton(
            text="Limpar Modelos",
            on_release=self.reset_models,
            size_hint_x=0.25,
            md_bg_color=(0.8, 0.2, 0.2, 1)  # Vermelho
        )
        buttons_layout.add_widget(reset_btn)
        
        # Botão de salvar
        save_btn = MDRaisedButton(
            text="Salvar Configurações",
            on_release=self.save_models,
            size_hint_x=0.25,
            md_bg_color=(0.2, 0.7, 0.3, 1)  # Verde
        )
        buttons_layout.add_widget(save_btn)
        
        main_layout.add_widget(buttons_layout)
        
        # Botão de voltar
        back_btn = MDRaisedButton(
            text="Voltar",
            on_release=self.go_back,
            size_hint=(1, None),
            height=dp(50)
        )
        main_layout.add_widget(back_btn)
        
        self.add_widget(main_layout)
    
    def create_model_card(self, title, model_type):
        """Cria um card para seleção de modelo."""
        card = MDCard(
            orientation='vertical',
            size_hint_y=None,
            height=dp(200),
            padding=dp(10),
            spacing=dp(10)
        )
        
        # Título do card
        card_title = MDLabel(
            text=title,
            font_style="H6",
            size_hint_y=None,
            height=dp(30)
        )
        card.add_widget(card_title)
        
        # ScrollView para a lista de modelos
        scroll = ScrollView()
        model_list = BoxLayout(
            orientation='vertical',
            spacing=dp(5),
            size_hint_y=None
        )
        model_list.bind(minimum_height=model_list.setter('height'))
        
        # Será preenchido com modelos disponíveis
        setattr(card, 'model_list', model_list)
        setattr(card, 'model_type', model_type)
        
        scroll.add_widget(model_list)
        card.add_widget(scroll)
        
        # Label para o modelo selecionado
        selected_label = MDLabel(
            text="Nenhum modelo selecionado",
            size_hint_y=None,
            height=dp(30)
        )
        setattr(card, 'selected_label', selected_label)
        card.add_widget(selected_label)
        
        return card
    
    def load_available_models(self):
        """Carrega a lista de modelos disponíveis."""
        # Carregar os modelos padrão salvos
        self.default_models = self.api_manager.get_default_models()
        
        # Modelos padrão do sistema
        default_system_models = [
            {"id": "default_gpt35", "name": "GPT-3.5 Turbo (Padrão)"},
            {"id": "default_gpt4", "name": "GPT-4 (Padrão)"}
        ]
        
        # Inicializar a API, se necessário
        if not self.api:
            api_key = self.api_manager.get_api_key()
            if api_key:
                self.api = OpenAIAPI(api_key)
        
        # Buscar modelos fine-tuned, se a API estiver disponível
        fine_tuned_models = []
        if self.api:
            try:
                models = self.api.list_fine_tuned_models()
                for model in models:
                    model_id = model.get('id') or model.get('fine_tuned_model')
                    if model_id:
                        model_name = self.get_model_name_from_id(model_id)
                        model_type = self._guess_model_type(model_id)
                        fine_tuned_models.append({
                            "id": model_id,
                            "name": model_name,
                            "type": model_type
                        })
            except Exception as e:
                logger.error(f"Erro ao listar modelos fine-tuned: {e}")
        
        # Atualizar cards com os modelos
        for model_type in ['question', 'answer', 'wrong_answers']:
            card = getattr(self, f"{model_type}_card")
            model_list = getattr(card, 'model_list')
            model_list.clear_widgets()
            
            # Adicionar modelos padrão
            for model in default_system_models:
                self.add_model_to_list(model_list, model["id"], model["name"], model_type)
            
            # Adicionar modelos fine-tuned do tipo correspondente
            for model in fine_tuned_models:
                if model["type"] == model_type:
                    self.add_model_to_list(model_list, model["id"], model["name"], model_type)
            
            # Definir modelo selecionado, se houver
            selected_model = self.default_models.get(model_type)
            if selected_model:
                self.select_model(model_type, selected_model)
    
    def add_model_to_list(self, model_list, model_id, model_name, model_type):
        """Adiciona um modelo à lista do card correspondente."""
        # Verificar se existe um nome personalizado
        custom_name = self.api_manager.db.get_model_custom_name(model_id)
        # Se houver um nome personalizado, usá-lo como nome de exibição, caso contrário usar o nome gerado
        display_name = custom_name if custom_name else model_name
        
        # Se o nome personalizado existir, mostrar também o ID do modelo para referência
        if custom_name:
            display_name = f"{custom_name} ({model_id[-10:]})"
        
        # Criar um layout horizontal para o botão e um possível botão de ação
        item_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=dp(5)
        )
        
        model_btn = MDFlatButton(
            text=display_name,
            size_hint_x=0.8,
            on_release=lambda x, mid=model_id, mtype=model_type: self.select_model(mtype, mid)
        )
        
        # Adicionar o ID do modelo como atributo para facilitar a busca
        setattr(model_btn, 'model_id', model_id)
        
        # Adicionar botão de renomear
        rename_btn = MDRaisedButton(
            text="Renomear",
            size_hint_x=0.2,
            on_release=lambda x, mid=model_id: self.rename_model(mid)
        )
        
        item_layout.add_widget(model_btn)
        item_layout.add_widget(rename_btn)
        model_list.add_widget(item_layout)
    
    def select_model(self, model_type, model_id):
        """Seleciona um modelo para o tipo especificado."""
        self.selected_models[model_type] = model_id
        card = getattr(self, f"{model_type}_card")
        selected_label = getattr(card, 'selected_label')
        model_name = self.get_model_name_from_id(model_id)
        selected_label.text = f"Selecionado: {model_name}"
        self.models_changed = True
    
    def get_model_name_from_id(self, model_id):
        """Extrai um nome amigável a partir do ID do modelo."""
        # Primeiro, verificar se existe um nome personalizado no banco de dados
        custom_name = self.api_manager.db.get_model_custom_name(model_id)
        if custom_name:
            return custom_name
            
        # Extrair informações significativas do ID do modelo
        parts = model_id.split(':')
        
        # Formato específico para modelos da OpenAI com formato ft:gpt-3.5-turbo-0125:personal::BGt3nwXI
        if len(parts) >= 3 and parts[0] == "ft" and "personal" in parts[2]:
            base_model = parts[1]  # gpt-3.5-turbo-0125, etc.
            
            # Extrair identificador único
            model_identifier = parts[-1] if len(parts) > 3 else "custom"
            
            # Criar um nome amigável
            return f"Modelo Personalizado ({base_model})"
        
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
            return f"{friendly_purpose} ({base_model.upper()})"
        
        # Para job IDs
        elif model_id.startswith("ftjob-"):
            return f"Job de Fine-tuning: {model_id}"
        
        # Para modelos padrão
        elif model_id == "default_gpt35":
            return "GPT-3.5 Turbo (Padrão)"
        elif model_id == "default_gpt4":
            return "GPT-4 (Padrão)"
        
        # Se não conseguir extrair informações, retornar parte do ID
        if len(model_id) > 20:
            return f"Modelo: ...{model_id[-20:]}"
        else:
            return f"Modelo: {model_id}"
    
    def _guess_model_type(self, model_id):
        """Tenta adivinhar o tipo de modelo com base no ID."""
        model_id = model_id.lower()
        
        if 'question' in model_id:
            return 'question'
        elif 'answer' in model_id:
            return 'answer'
        elif 'distractor' in model_id or 'wrong' in model_id:
            return 'wrong_answers'
        else:
            # Padrão para questões se não conseguir identificar
            return 'question'
    
    def save_models(self, instance):
        """Salva os modelos selecionados como padrão."""
        self.api_manager.save_default_models(self.selected_models)
        Snackbar(text="Modelos padrão salvos com sucesso!").open()
        self.models_changed = False
    
    def show_import_dialog(self, instance):
        """Mostra o diálogo de importação de modelo."""
        content = ImportModelContent(callback=self.import_model)
        self.dialog = MDDialog(
            title="Importar Modelo",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="IMPORTAR",
                    on_release=lambda x: self.process_import(content)
                ),
            ],
            size_hint=(0.8, None),
            height=dp(500)  # Aumentado para acomodar o conteúdo
        )
        self.dialog.open()
    
    def process_import(self, content):
        """Processa a importação do modelo."""
        if content.fetch_all_selected:
            self.fetch_all_fine_tuned_models()
            self.dialog.dismiss()
        else:
            id_value = content.id_input.text.strip()
            if not id_value:
                Snackbar(text="Por favor, insira um ID válido.").open()
                return
            
            id_type = content.id_type
            model_type = content.model_type
            custom_name = content.custom_name_input.text.strip()
            
            self.import_model(id_value, id_type, model_type, custom_name)
            self.dialog.dismiss()
    
    def import_model(self, id_value, id_type, model_type, custom_name=None):
        """Importa um modelo treinado da OpenAI."""
        logger.info(f"Tentando importar modelo - ID: {id_value}, Tipo de ID: {id_type}, Tipo de modelo: {model_type}, Nome: {custom_name}")
        
        if not self.api:
            api_key = self.api_manager.get_api_key()
            if not api_key:
                logger.error("Chave da API não encontrada")
                Snackbar(text="Chave da API não encontrada. Configure primeiro.").open()
                return
            self.api = OpenAIAPI(api_key)
        
        # Mostrar mensagem de carregamento
        Snackbar(text="Buscando informações do modelo...").open()
        
        # Em uma implementação real, usaríamos threading para não bloquear a UI
        try:
            if id_type == 'job':
                # Buscar detalhes do job de fine-tuning
                logger.info(f"Buscando detalhes do job: {id_value}")
                job_details = self.api.get_fine_tuning_job(id_value)
                
                if not job_details:
                    logger.error(f"Job não encontrado: {id_value}")
                    Snackbar(text="Job não encontrado ou erro ao buscar informações.").open()
                    return
                
                logger.info(f"Detalhes do job encontrados: {job_details}")
                
                if job_details.get('status') != 'succeeded':
                    logger.warning(f"Job não concluído, status: {job_details.get('status', 'desconhecido')}")
                    Snackbar(text=f"Job não concluído. Status: {job_details.get('status', 'desconhecido')}").open()
                    return
                
                model_id = job_details.get('fine_tuned_model')
                if not model_id:
                    logger.error("Modelo não encontrado no job")
                    Snackbar(text="Modelo não encontrado no job de fine-tuning.").open()
                    return
                
                logger.info(f"ID do modelo extraído do job: {model_id}")
                
                # Adicionar o modelo à lista correspondente
                self.add_imported_model(model_id, model_type, job_details, custom_name)
                
            elif id_type == 'model':
                # Buscar detalhes do modelo
                logger.info(f"Buscando detalhes do modelo: {id_value}")
                model_details = self.api.get_model_details(id_value)
                
                if not model_details:
                    logger.error(f"Modelo não encontrado: {id_value}")
                    Snackbar(text="Modelo não encontrado ou erro ao buscar informações.").open()
                    return
                
                logger.info(f"Detalhes do modelo encontrados: {model_details}")
                
                # Adicionar o modelo à lista correspondente
                self.add_imported_model(id_value, model_type, model_details, custom_name)
                
            else:
                logger.error(f"Tipo de ID não suportado: {id_type}")
                Snackbar(text="Tipo de ID não suportado.").open()
                
        except Exception as e:
            logger.error(f"Erro ao importar modelo: {str(e)}")
            Snackbar(text=f"Erro ao importar modelo: {str(e)}").open()
    
    def add_imported_model(self, model_id, model_type, model_details, custom_name=None):
        """Adiciona um modelo importado à lista de modelos."""
        # Verificar se o modelo já existe na lista
        card = getattr(self, f"{model_type}_card")
        model_list = getattr(card, 'model_list')
        
        # Verificar cada botão para ver se o modelo já existe
        for child in model_list.children:
            if hasattr(child, 'model_id') and child.model_id == model_id:
                Snackbar(text=f"Modelo já importado: {model_id}").open()
                return
        
        # Criar nome amigável para o modelo
        model_name = self.get_model_name_from_id(model_id)
        
        # Adicionar à lista
        self.add_model_to_list(model_list, model_id, model_name, model_type)
        
        # Definir nome personalizado se fornecido
        if custom_name:
            self.api_manager.db.set_model_custom_name(model_id, custom_name)
        
        # Selecionar automaticamente
        self.select_model(model_type, model_id)
        
        Snackbar(text=f"Modelo importado com sucesso!").open()
        self.models_changed = True
    
    def go_back(self, instance):
        """Volta para a tela inicial."""
        if self.models_changed:
            # Perguntar se deseja salvar as alterações
            self.show_save_dialog()
        else:
            self.manager.current = 'home'
    
    def show_save_dialog(self):
        """Mostra o diálogo para salvar as alterações."""
        self.dialog = MDDialog(
            title="Salvar Alterações",
            text="Deseja salvar as alterações nos modelos padrão?",
            buttons=[
                MDFlatButton(
                    text="NÃO",
                    on_release=lambda x: self.dismiss_and_go_back()
                ),
                MDRaisedButton(
                    text="SIM",
                    on_release=lambda x: self.save_and_go_back()
                ),
            ]
        )
        self.dialog.open()
    
    def dismiss_and_go_back(self):
        """Descarta as alterações e volta para a tela inicial."""
        self.dialog.dismiss()
        self.manager.current = 'home'
    
    def save_and_go_back(self):
        """Salva as alterações e volta para a tela inicial."""
        self.api_manager.save_default_models(self.selected_models)
        self.dialog.dismiss()
        self.manager.current = 'home'
        self.models_changed = False
    
    def reload_models(self, instance=None):
        """Recarrega a lista de modelos disponíveis."""
        # Inicializar a API, se necessário
        api_key = self.api_manager.get_api_key()
        if not api_key:
            Snackbar(text="Chave da API não encontrada. Configure primeiro.").open()
            return
            
        self.api = OpenAIAPI(api_key)
        
        # Mostrar mensagem de carregamento
        Snackbar(text="Recarregando modelos...").open()
        
        # Reload dos modelos
        self.load_available_models()
        
        # Mensagem de conclusão
        Snackbar(text="Modelos recarregados com sucesso!").open()
    
    def fetch_all_fine_tuned_models(self):
        """Busca todos os modelos fine-tuned da conta e os adiciona."""
        # Inicializar a API, se necessário
        if not self.api:
            api_key = self.api_manager.get_api_key()
            if not api_key:
                Snackbar(text="Chave da API não encontrada. Configure primeiro.").open()
                return
            self.api = OpenAIAPI(api_key)
        
        # Mostrar mensagem de carregamento
        Snackbar(text="Buscando modelos fine-tuned...").open()
        
        try:
            # Buscar modelos fine-tuned
            models = self.api.list_fine_tuned_models()
            
            # Verificar se encontrou modelos
            if not models:
                Snackbar(text="Nenhum modelo fine-tuned encontrado.").open()
                return
            
            # Contar modelos adicionados
            added_count = 0
            
            # Adicionar cada modelo
            for model in models:
                model_id = model.get('id') or model.get('fine_tuned_model')
                if model_id:
                    # Tentar adivinhar o tipo do modelo
                    model_type = self._guess_model_type(model_id)
                    
                    # Buscar detalhes do modelo para confirmar tipo
                    model_details = self.api.get_model_details(model_id)
                    
                    # Adicionar à lista correspondente
                    self.add_imported_model(model_id, model_type, model_details)
                    added_count += 1
            
            # Mensagem de conclusão
            Snackbar(text=f"{added_count} modelos importados com sucesso!").open()
            
        except Exception as e:
            logger.error(f"Erro ao buscar modelos: {str(e)}")
            Snackbar(text=f"Erro ao buscar modelos: {str(e)}").open()

    def rename_model(self, model_name):
        """Abre um diálogo para renomear o modelo."""
        # Buscar o nome personalizado atual, se existir
        current_custom_name = self.api_manager.db.get_model_custom_name(model_name)
        
        # Criar o diálogo
        content = BoxLayout(
            orientation='vertical', 
            spacing=dp(10),
            size_hint_y=None,
            height=dp(100)
        )
        
        # Campo de texto para o novo nome
        text_field = MDTextField(
            hint_text="Nome Personalizado",
            helper_text="Digite um nome para identificar este modelo",
            helper_text_mode="on_focus",
            size_hint_y=None,
            height=dp(70)
        )
        
        # Preencher com o nome atual, se existir
        if current_custom_name:
            text_field.text = current_custom_name
        
        content.add_widget(text_field)
        
        # Criar e exibir o diálogo
        self.dialog = MDDialog(
            title="Renomear Modelo",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="SALVAR",
                    on_release=lambda x, field=text_field, mid=model_name: self._save_model_name(field, mid)
                ),
            ],
        )
        self.dialog.open()
    
    def _save_model_name(self, text_field, model_name):
        """Salva o novo nome do modelo no banco de dados."""
        new_name = text_field.text.strip()
        
        # Validar nome
        if not new_name:
            Snackbar(text="Nome não pode ser vazio").open()
            return
            
        try:
            # Salvar no banco de dados
            if self.api_manager.db.set_model_custom_name(model_name, new_name):
                # Atualizar a interface
                Snackbar(text=f"Modelo renomeado para '{new_name}'").open()
                
                # Atualizar a lista de modelos
                self.models_changed = True
                self.load_available_models()
                
                # Fechar diálogo
                self.dialog.dismiss()
            else:
                Snackbar(text="Erro ao renomear modelo").open()
        except Exception as e:
            logger.error(f"Erro ao renomear modelo: {e}")
            Snackbar(text=f"Erro ao renomear modelo: {e}").open()

    def update_models_list(self):
        """Atualiza a lista de modelos disponíveis."""
        try:
            # Limpa a lista atual
            self.ids.models_container.clear_widgets()
            
            # Obtém os modelos do banco de dados
            models = self.api_manager.db.get_fine_tuned_models()
            
            if not models:
                self.ids.models_container.add_widget(
                    MDLabel(
                        text="Nenhum modelo encontrado",
                        halign="center",
                        theme_text_color="Secondary"
                    )
                )
                return
            
            # Adiciona cada modelo à lista
            for model in models:
                # Obtém o nome personalizado se existir
                custom_name = self.api_manager.db.get_model_custom_name(model['model_name'])
                display_name = custom_name if custom_name else model['model_name']
                
                # Cria o card do modelo
                card = MDCard(
                    orientation="vertical",
                    padding="8dp",
                    size_hint_y=None,
                    height="120dp",
                    elevation=3
                )
                
                # Layout principal
                main_layout = BoxLayout(orientation="horizontal")
                
                # Layout do texto
                text_layout = BoxLayout(orientation="vertical")
                text_layout.add_widget(
                    MDLabel(
                        text=display_name,
                        theme_text_color="Primary",
                        font_style="H6"
                    )
                )
                text_layout.add_widget(
                    MDLabel(
                        text=f"Base: {model['base_model']}",
                        theme_text_color="Secondary"
                    )
                )
                text_layout.add_widget(
                    MDLabel(
                        text=f"Status: {model['status']}",
                        theme_text_color="Secondary"
                    )
                )
                
                # Layout dos botões
                button_layout = BoxLayout(
                    orientation="vertical",
                    size_hint_x=None,
                    width="100dp",
                    spacing="8dp"
                )
                
                # Botão de renomear
                rename_btn = MDRaisedButton(
                    text="Renomear",
                    size_hint_y=None,
                    height="40dp",
                    on_release=lambda x, m=model['model_name']: self.rename_model(m)
                )
                
                # Botão de selecionar
                select_btn = MDRaisedButton(
                    text="Selecionar",
                    size_hint_y=None,
                    height="40dp",
                    on_release=lambda x, m=model['model_name']: self.select_model(m)
                )
                
                button_layout.add_widget(rename_btn)
                button_layout.add_widget(select_btn)
                
                main_layout.add_widget(text_layout)
                main_layout.add_widget(button_layout)
                
                card.add_widget(main_layout)
                self.ids.models_container.add_widget(card)
                
        except Exception as e:
            logger.error(f"Erro ao atualizar lista de modelos: {str(e)}")
            Snackbar(text=f"Erro ao buscar modelos: {str(e)}").open()

    def reset_models(self, instance=None):
        """Reseta a lista de modelos no banco de dados."""
        # Mostrar diálogo de confirmação
        self.dialog = MDDialog(
            title="Limpar Modelos",
            text="Tem certeza que deseja limpar todos os modelos? Esta ação não pode ser desfeita.",
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="LIMPAR",
                    on_release=lambda x: self._confirm_reset_models()
                ),
            ],
        )
        self.dialog.open()
    
    def _confirm_reset_models(self):
        """Confirma e executa a limpeza dos modelos."""
        try:
            # Fechar o diálogo
            self.dialog.dismiss()
            
            # Resetar modelos no banco de dados
            if self.api_manager.db.reset_fine_tuned_models():
                Snackbar(text="Lista de modelos resetada com sucesso!").open()
                
                # Limpar as listas de modelos na interface
                for card_name in ['question_card', 'answer_card', 'wrong_answers_card']:
                    card = getattr(self, card_name, None)
                    if card:
                        model_list = getattr(card, 'model_list', None)
                        if model_list:
                            model_list.clear_widgets()
                
                # Limpar modelos selecionados
                self.selected_models = {
                    'question': None,
                    'answer': None,
                    'wrong_answers': None
                }
                
                # Atualizar labels
                for card_name in ['question_card', 'answer_card', 'wrong_answers_card']:
                    card = getattr(self, card_name, None)
                    if card:
                        selected_label = getattr(card, 'selected_label', None)
                        if selected_label:
                            selected_label.text = "Nenhum modelo selecionado"
                
                self.models_changed = True
            else:
                Snackbar(text="Erro ao resetar lista de modelos!").open()
        except Exception as e:
            logger.error(f"Erro ao resetar modelos: {e}")
            Snackbar(text=f"Erro ao resetar modelos: {str(e)}").open()

class ImportModelContent(BoxLayout):
    """Conteúdo do diálogo de importação de modelo."""
    
    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(10)
        self.padding = dp(10)
        self.size_hint_y = None
        self.height = dp(420)  # Aumentado para acomodar o novo campo
        self.callback = callback
        self.id_type = 'job'  # Padrão para job ID
        self.model_type = 'question'  # Padrão para modelo de perguntas
        self.fetch_all_selected = False
        
        # Título e mensagem explicativa
        explanation = MDLabel(
            text="Importe modelos fine-tuned da sua conta OpenAI",
            size_hint_y=None,
            height=dp(30)
        )
        self.add_widget(explanation)
        
        # Botão para buscar automaticamente todos os modelos
        fetch_btn = MDRaisedButton(
            text="Buscar Todos os Modelos da Minha Conta",
            on_release=self.select_fetch_all,
            size_hint=(1, None),
            height=dp(50)
        )
        self.add_widget(fetch_btn)
        
        # Separador
        separator = MDLabel(
            text="OU",
            halign="center",
            size_hint_y=None,
            height=dp(30),
            bold=True
        )
        self.add_widget(separator)
        
        # Input para ID
        self.id_input = MDTextField(
            hint_text="ID do Job ou Modelo Fine-Tuned",
            helper_text="Ex: ftjob-123456 ou ft:gpt-3.5-turbo:model-id",
            helper_text_mode="on_focus",
            size_hint_y=None,
            height=dp(70)
        )
        self.add_widget(self.id_input)
        
        # Input para nome personalizado
        self.custom_name_input = MDTextField(
            hint_text="Nome Personalizado (opcional)",
            helper_text="Um nome para ajudar a identificar este modelo",
            helper_text_mode="on_focus",
            size_hint_y=None,
            height=dp(70)
        )
        self.add_widget(self.custom_name_input)
        
        # Opções de tipo de ID
        id_type_title = MDLabel(
            text="Tipo de ID:",
            size_hint_y=None,
            height=dp(30)
        )
        self.add_widget(id_type_title)
        
        id_type_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40)
        )
        
        # Job ID option
        job_id_layout = BoxLayout(orientation='horizontal', size_hint_x=0.5)
        self.job_checkbox = MDCheckbox(
            group='id_type',
            active=True,
            size_hint=(None, None),
            size=(dp(48), dp(48))
        )
        self.job_checkbox.bind(active=lambda x, y: self.set_id_type('job') if y else None)
        job_id_layout.add_widget(self.job_checkbox)
        job_id_layout.add_widget(MDLabel(text="Job ID", size_hint_x=None, width=dp(80)))
        id_type_layout.add_widget(job_id_layout)
        
        # Model ID option
        model_id_layout = BoxLayout(orientation='horizontal', size_hint_x=0.5)
        self.model_checkbox = MDCheckbox(
            group='id_type',
            active=False,
            size_hint=(None, None),
            size=(dp(48), dp(48))
        )
        self.model_checkbox.bind(active=lambda x, y: self.set_id_type('model') if y else None)
        model_id_layout.add_widget(self.model_checkbox)
        model_id_layout.add_widget(MDLabel(text="Model ID", size_hint_x=None, width=dp(80)))
        id_type_layout.add_widget(model_id_layout)
        
        self.add_widget(id_type_layout)
        
        # Opções de tipo de modelo
        model_type_title = MDLabel(
            text="Tipo de Modelo:",
            size_hint_y=None,
            height=dp(30)
        )
        self.add_widget(model_type_title)
        
        model_type_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40)
        )
        
        # Questions model option
        question_layout = BoxLayout(orientation='horizontal', size_hint_x=0.33)
        self.question_checkbox = MDCheckbox(
            group='model_type',
            active=True,
            size_hint=(None, None),
            size=(dp(48), dp(48))
        )
        self.question_checkbox.bind(active=lambda x, y: self.set_model_type('question') if y else None)
        question_layout.add_widget(self.question_checkbox)
        question_layout.add_widget(MDLabel(text="Questões", size_hint_x=None, width=dp(80)))
        model_type_layout.add_widget(question_layout)
        
        # Answers model option
        answer_layout = BoxLayout(orientation='horizontal', size_hint_x=0.33)
        self.answer_checkbox = MDCheckbox(
            group='model_type',
            active=False,
            size_hint=(None, None),
            size=(dp(48), dp(48))
        )
        self.answer_checkbox.bind(active=lambda x, y: self.set_model_type('answer') if y else None)
        answer_layout.add_widget(self.answer_checkbox)
        answer_layout.add_widget(MDLabel(text="Respostas", size_hint_x=None, width=dp(80)))
        model_type_layout.add_widget(answer_layout)
        
        # Distractors model option
        distractor_layout = BoxLayout(orientation='horizontal', size_hint_x=0.33)
        self.distractor_checkbox = MDCheckbox(
            group='model_type',
            active=False,
            size_hint=(None, None),
            size=(dp(48), dp(48))
        )
        self.distractor_checkbox.bind(active=lambda x, y: self.set_model_type('wrong_answers') if y else None)
        distractor_layout.add_widget(self.distractor_checkbox)
        distractor_layout.add_widget(MDLabel(text="Distratores", size_hint_x=None, width=dp(80)))
        model_type_layout.add_widget(distractor_layout)
        
        self.add_widget(model_type_layout)
    
    def set_id_type(self, id_type):
        """Define o tipo de ID."""
        self.id_type = id_type
    
    def set_model_type(self, model_type):
        """Define o tipo de modelo."""
        self.model_type = model_type
    
    def select_fetch_all(self, instance):
        """Seleciona a opção de buscar todos os modelos."""
        self.fetch_all_selected = True
        if self.callback:
            self.callback(None, None, None) 