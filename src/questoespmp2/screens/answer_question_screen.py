#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Answer Question Screen for PMP Questions Generator
"""

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.lang import Builder
from ..database.db_manager import DatabaseManager
import json
import logging

logger = logging.getLogger(__name__)

# Definir o estilo do botão de opção personalizado
Builder.load_string('''
<OptionButton>:
    size_hint_x: 1
    size_hint_y: None
    height: label.height + dp(20)
    padding: dp(15)
    ripple_behavior: True
    md_bg_color: app.theme_cls.primary_light
    radius: dp(10)
    on_release: if self.callback: self.callback(self.index)

    MDLabel:
        id: label
        text: root.option_text
        size_hint_y: None
        height: self.texture_size[1]
        halign: 'left'
        valign: 'middle'
        text_size: self.width - dp(30), None
''')

class OptionButton(MDCard):
    """Custom button for question options with text wrapping."""
    
    option_text = StringProperty("")
    callback = ObjectProperty(None)
    index = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        self.option_text = kwargs.pop('text', '')
        self.callback = kwargs.pop('on_release', None)
        self.index = kwargs.pop('index', None)
        super().__init__(**kwargs)

class AnswerQuestionScreen(MDScreen):
    """Screen for answering PMP questions."""
    
    current_question_id = StringProperty("")
    has_answered = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        """Initialize the answer question screen."""
        super(AnswerQuestionScreen, self).__init__(**kwargs)
        self.db_manager = DatabaseManager()
        self.dialogs = []
        self.selected_answer = None
        self.option_buttons = []
        self.current_question = None
        self.content_layout = None
        self.question_label = None
        self.question_card = None
        self.next_btn = None
        self.other_feedback = None
        self.build_ui()
    
    def build_ui(self):
        """Build the user interface."""
        # Main container
        main_layout = MDBoxLayout(orientation="vertical", spacing=0)
        
        # Scrollable content
        scroll = MDScrollView(
            do_scroll_x=False,
            size_hint=(1, 1)
        )
        
        # Layout principal sem spacing e com tamanho adaptativo
        content_layout = MDBoxLayout(
            orientation="vertical",
            padding=[dp(10), dp(10), dp(10), dp(10)],  # Padding uniforme
            spacing=dp(5),  # Reintroduzir um espaçamento geral entre elementos
            size_hint_y=None,
            size_hint_x=1
        )
        content_layout.bind(minimum_height=content_layout.setter('height'))
        
        # Title mais compacto
        title = MDLabel(
            text="Responder Questões",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=dp(40)  # Aumentado para dar mais respiro
        )
        content_layout.add_widget(title)
        
        # Question Card simples e direto
        self.question_card = MDCard(
            orientation="vertical",
            padding=dp(10),  # Aumentado para melhor respiro interno
            spacing=dp(5),   # Algum espaçamento interno
            size_hint=(1, None),
            height=dp(80),   # Aumentado para mais conforto visual
            elevation=1      # Reintroduzir elevação leve
        )
        
        # Question Label
        self.question_label = MDLabel(
            text="",
            size_hint_y=None,
            height=dp(60),  # Aumentado para comportar mais texto
            halign="left",
            valign="middle"
        )
        self.question_card.add_widget(self.question_label)
        content_layout.add_widget(self.question_card)
        
        # Espaço entre a pergunta e as opções - apenas um pouquinho
        spacer = MDBoxLayout(
            size_hint_y=None,
            height=dp(5)  # Espaço pequeno mas perceptível
        )
        content_layout.add_widget(spacer)
        
        # MUDANÇA RADICAL: Não usamos mais um BoxLayout separado para opções
        # Guardaremos apenas uma referência para os botões
        self.option_buttons = []
        
        # O resto do layout (botões de opções) é adicionado diretamente em load_question
        
        # Add scrollable content
        scroll.add_widget(content_layout)
        main_layout.add_widget(scroll)
        
        # Navigation Buttons
        nav_layout = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(50),
            padding=[dp(20), dp(10), dp(20), dp(10)]
        )
        
        back_btn = MDRaisedButton(
            text="Voltar",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.go_back
        )
        nav_layout.add_widget(back_btn)
        
        # Botão de Reportar Problema
        report_btn = MDRaisedButton(
            text="Reportar Problema",
            size_hint=(0.8, None),
            height=dp(50),
            md_bg_color=(0.8, 0.1, 0.1, 1),
            on_release=self.show_report_problem_dialog
        )
        nav_layout.add_widget(report_btn)
        
        self.next_btn = MDRaisedButton(
            text="Próxima Questão",
            on_release=lambda x: self.next_question()
        )
        nav_layout.add_widget(self.next_btn)
        
        main_layout.add_widget(nav_layout)
        self.add_widget(main_layout)
        
        # Salvar referência ao content_layout para adicionar opções depois
        self.content_layout = content_layout
    
    def on_pre_enter(self):
        """Load a question when entering the screen."""
        self.load_question()
    
    def load_question(self):
        """Load a random question from the database."""
        try:
            question = self.db_manager.get_random_question()
            if not question:
                logger.error("Nenhuma questão disponível no banco de dados")
                self.show_no_questions_dialog()
                return
            
            logger.info(f"Questão carregada: {question}")
            
            self.current_question = question
            # Remover tags [b] e [/b] da questão
            question_text = question['question'].replace('[b]', '').replace('[/b]', '')
            self.question_label.text = question_text
            self.has_answered = False
            self.selected_answer = None
            
            # Limpar todas as opções anteriores
            for button in self.option_buttons:
                self.content_layout.remove_widget(button)
            self.option_buttons = []
            
            # Processar opções
            options = question['options']
            if isinstance(options, str):
                try:
                    options = json.loads(options)
                    logger.info(f"Opções convertidas de JSON: {options}")
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar JSON das opções: {e}")
                    options = []
            
            if not isinstance(options, list):
                logger.error(f"Opções não são uma lista: {type(options)}")
                options = []
            
            # Garantir que temos exatamente 4 opções
            while len(options) < 4:
                options.append("Opção não disponível")
            
            logger.info(f"Opções processadas: {options}")
            
            # Processar todas as opções primeiro
            processed_options = []
            for i, option_text in enumerate(options[:4]):
                option_text = option_text.strip()
                # Remover tags [b] e [/b]
                option_text = option_text.replace('[b]', '').replace('[/b]', '')
                
                # Se o texto da opção for igual à pergunta ou começar com ela, tente limpar
                if option_text == question_text or option_text.startswith(question_text):
                    cleaned_text = option_text[len(question_text):].strip() if option_text.startswith(question_text) else ""
                    if cleaned_text:  # Se ainda houver texto após a limpeza
                        option_text = cleaned_text
                    else:
                        option_text = options[i]  # Mantenha o texto original se a limpeza resultar em texto vazio
                
                processed_options.append(option_text)
            
            logger.info(f"Opções processadas finais: {processed_options}")
            
            # Adicionar as opções ao layout
            for i, option_text in enumerate(processed_options):
                button = OptionButton(
                    text=f"{chr(65+i)}. {option_text}",
                    on_release=lambda idx=i: self.check_answer(idx),
                    index=i
                )
                self.option_buttons.append(button)
                self.content_layout.add_widget(button)
                
                # Adicionar um pequeno espaço entre os botões de opção (exceto o último)
                if i < len(processed_options) - 1:
                    option_spacer = MDBoxLayout(
                        size_hint_y=None,
                        height=dp(8)  # Espaço entre opções
                    )
                    self.content_layout.add_widget(option_spacer)
                    # Guardar referência para remover depois
                    self.option_buttons.append(option_spacer)
            
            logger.info(f"Questão carregada com sucesso - ID: {question['id']}")
            
        except Exception as e:
            logger.error(f"Erro ao carregar questão: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            self.show_error_dialog("Erro ao carregar questão", str(e))
    
    def check_answer(self, index):
        """Handle answer selection."""
        if self.has_answered:
            return
            
        self.has_answered = True
        self.selected_answer = index
        
        # Log para debug
        logger.info(f"Verificando resposta - Questão ID: {self.current_question['id']}")
        logger.info(f"Resposta selecionada: {index}")
        logger.info(f"Resposta correta do banco: {self.current_question['correct_answer']}")
        
        # Usar diretamente o índice numérico da resposta correta
        correct_index = self.current_question['correct_answer']
        
        # Log adicional para debug
        logger.info(f"Índice correto convertido: {correct_index}")
        
        # Atualizar cores dos botões
        for i, btn in enumerate(self.option_buttons):
            if isinstance(btn, OptionButton):  # Verificar se é um botão de opção
                if i == correct_index:
                    btn.md_bg_color = (0, 0.7, 0, 1)  # Verde para correto
                elif i == index and i != correct_index:
                    btn.md_bg_color = (0.7, 0, 0, 1)  # Vermelho para errado
                else:
                    # Manter a cor original para as outras opções
                    btn.md_bg_color = MDApp.get_running_app().theme_cls.primary_light
        
        # Log para debug da explicação
        logger.info(f"Explicação disponível: {bool(self.current_question.get('explanation'))}")
        
        # Converter índice para letra (0=A, 1=B, 2=C, 3=D)
        correct_letter = chr(65 + correct_index)
        selected_letter = chr(65 + index)
        
        # Verificar se a resposta está correta
        is_correct = index == correct_index
        logger.info(f"Resposta está correta: {is_correct}")
        
        # Mostrar explicação
        self.show_explanation_dialog(
            correct=is_correct,
            explanation=f"Resposta correta: {correct_letter}\n\n{self.current_question.get('explanation', 'Explicação não disponível')}"
        )
        
        # Atualizar estatísticas
        try:
            self.db_manager.update_question_stats(
                self.current_question['id'],
                is_correct
            )
            logger.info(f"Estatísticas atualizadas para questão {self.current_question['id']}")
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
    
    def show_explanation_dialog(self, correct: bool, explanation: str):
        """Show dialog with question explanation."""
        # Obter a letra da resposta selecionada
        selected_letter = chr(65 + self.selected_answer) if self.selected_answer is not None else "N/A"
        
        # Construir mensagem mais detalhada
        if correct:
            result = "🎉 Parabéns! Você acertou!"
            message = f"""
Sua resposta ({selected_letter}) está correta!

{explanation}
"""
        else:
            result = "❌ Resposta incorreta"
            message = f"""
Sua resposta ({selected_letter}) está incorreta.

{explanation}
"""
        
        dialog = MDDialog(
            title=result,
            text=message,
            buttons=[
                MDFlatButton(
                    text="Próxima",
                    on_release=lambda x: (dialog.dismiss(), self.next_question())
                ),
                MDFlatButton(
                    text="Reportar Problema",
                    theme_text_color="Custom",
                    text_color=(0.8, 0.1, 0.1, 1),
                    on_release=lambda x: (dialog.dismiss(), self.show_report_problem_dialog(None))
                )
            ]
        )
        dialog.open()
        self.dialogs.append(dialog)
    
    def next_question(self):
        """Load the next question."""
        self.load_question()
    
    def show_no_questions_dialog(self):
        """Show dialog when no questions are available."""
        dialog = MDDialog(
            title="Sem Questões",
            text="Não há questões disponíveis no banco de dados.",
            buttons=[
                MDFlatButton(
                    text="Voltar",
                    on_release=lambda x: (dialog.dismiss(), self.go_back())
                )
            ]
        )
        dialog.open()
        self.dialogs.append(dialog)
    
    def show_error_dialog(self, title: str, message: str):
        """Mostra um diálogo de erro ao usuário."""
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
    
    def go_back(self, *args):
        """Return to home screen."""
        self.manager.current = "home"
    
    def show_report_problem_dialog(self, *args):
        """Mostrar diálogo para reportar problema com a questão."""
        if not self.current_question:
            return
            
        items = [
            {"text": "Questão muito fácil", "value": "muito_facil"},
            {"text": "Opções óbvias", "value": "opcoes_obvias"},
            {"text": "Questão confusa", "value": "questao_confusa"},
            {"text": "Problema na explicação", "value": "problema_explicacao"},
            {"text": "Outro", "value": "outro"}
        ]
        
        dialog_content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(300)
        )
        
        # Label de instrução
        instruction = MDLabel(
            text="Selecione o tipo de problema nesta questão:",
            size_hint_y=None,
            height=dp(30)
        )
        dialog_content.add_widget(instruction)
        
        # Scroll para os botões de opção
        scroll = MDScrollView(size_hint=(1, None), height=dp(200))
        options_layout = MDBoxLayout(
            orientation="vertical",
            spacing=dp(5),
            size_hint_y=None
        )
        options_layout.bind(minimum_height=options_layout.setter('height'))
        
        for item in items:
            btn = MDRaisedButton(
                text=item["text"],
                size_hint=(1, None),
                height=dp(40),
                on_release=lambda x, val=item["value"]: self.select_problem_type(val, dialog)
            )
            options_layout.add_widget(btn)
        
        # Campo de texto para "Outro"
        self.other_feedback = MDTextField(
            hint_text="Descreva o problema (opcional)",
            size_hint_y=None,
            height=dp(60),
            multiline=True,
            helper_text="Descreva mais detalhes sobre o problema",
            helper_text_mode="on_focus"
        )
        dialog_content.add_widget(self.other_feedback)
        
        scroll.add_widget(options_layout)
        dialog_content.add_widget(scroll)
        
        dialog = MDDialog(
            title="Reportar Problema",
            type="custom",
            content_cls=dialog_content,
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="ENVIAR",
                    on_release=lambda x: self.report_problem("outro", self.other_feedback.text, dialog)
                )
            ]
        )
        dialog.open()
        self.dialogs.append(dialog)
    
    def select_problem_type(self, problem_type, dialog):
        """Seleciona o tipo de problema e reporta."""
        details = self.other_feedback.text if problem_type == "outro" else ""
        self.report_problem(problem_type, details, dialog)
    
    def report_problem(self, problem_type, details, dialog):
        """Reporta o problema da questão e carrega uma nova."""
        try:
            # Fechar o diálogo
            dialog.dismiss()
            
            # Reportar o problema no banco de dados
            if self.db_manager.report_question_problem(self.current_question['id'], problem_type, details):
                # Mostrar confirmação
                confirm_dialog = MDDialog(
                    title="Obrigado pelo feedback!",
                    text="O problema foi reportado com sucesso e esta questão foi removida do banco de dados.",
                    buttons=[
                        MDFlatButton(
                            text="OK",
                            on_release=lambda x: (confirm_dialog.dismiss(), self.next_question())
                        )
                    ]
                )
                confirm_dialog.open()
                self.dialogs.append(confirm_dialog)
            else:
                # Mostrar erro
                error_dialog = MDDialog(
                    title="Erro",
                    text="Não foi possível reportar o problema. Tente novamente mais tarde.",
                    buttons=[
                        MDFlatButton(
                            text="OK",
                            on_release=lambda x: error_dialog.dismiss()
                        )
                    ]
                )
                error_dialog.open()
                self.dialogs.append(error_dialog)
                
        except Exception as e:
            logger.error(f"Erro ao reportar problema: {e}")
            # Mostrar erro genérico
            error_dialog = MDDialog(
                title="Erro",
                text=f"Ocorreu um erro: {str(e)}",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: error_dialog.dismiss()
                    )
                ]
            )
            error_dialog.open()
            self.dialogs.append(error_dialog)
    
    def _adjust_card_height(self, instance, value):
        """Ajusta a altura do card da pergunta com base no conteúdo."""
        if instance.texture_size[1] > dp(60):  # Se o texto for maior que 60dp
            instance.height = instance.texture_size[1] + dp(20)  # Adiciona 20dp de padding
            self.question_card.height = instance.height + dp(20)  # Ajusta o card também
        else:
            instance.height = dp(60)  # Altura mínima
            self.question_card.height = dp(80)  # Altura mínima do card 