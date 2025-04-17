#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Filter Questions Screen for PMP Questions Generator
"""

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList, TwoLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.scrollview import ScrollView
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.tooltip import MDTooltip
from kivymd.uix.chip import MDChip
from kivymd.uix.menu import MDDropdownMenu

from ..database.db_manager import get_filtered_questions, get_question_topics, get_question_count

class FilterScreen(MDScreen):
    """Screen for filtering and displaying questions."""
    
    def __init__(self, **kwargs):
        """Initialize the filter questions screen."""
        super().__init__(**kwargs)
        self.dialogs = []
        self.topics_menu = None
        self.difficulty_menu = None
        self.topics = [
            "Integração", "Escopo", "Tempo", "Custo", "Qualidade", 
            "Recursos Humanos", "Comunicação", "Riscos", "Aquisições", 
            "Partes Interessadas", "Metodologias Ágeis", "Geral"
        ]
        self.difficulties = ["Todos", "Fácil", "Média", "Difícil"]
        self.selected_topic = "Todos"
        self.selected_difficulty = "Todos"
        self.current_page = 1
        self.questions_per_page = 10
        self.total_questions = 0
        self.total_pages = 0
        self.filtered_questions = []
        self.active_filters = []
        self.build_ui()
    
    def on_pre_leave(self):
        """Clean up when leaving the screen."""
        for dialog in self.dialogs:
            if dialog:
                dialog.dismiss()
        self.dialogs = []
    
    def on_pre_enter(self):
        """Load data when entering the screen."""
        self.load_topics()
        self.update_question_count()
    
    def build_ui(self):
        """Build the user interface."""
        # Main layout
        main_layout = MDBoxLayout(orientation="vertical", padding=20, spacing=10)
        
        # Title
        title = MDLabel(
            text="Filtrar Questões",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(title)
        
        # Filter controls
        filter_layout = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None, height=220)
        
        # Search by keyword
        search_layout = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        self.search_field = MDTextField(
            hint_text="Buscar por palavra-chave",
            helper_text="Digite uma palavra-chave para buscar nas questões",
            helper_text_mode="on_focus",
            size_hint_x=0.8
        )
        search_btn = MDRaisedButton(
            text="Buscar",
            size_hint_x=0.2,
            height=50,
            on_release=self.apply_filters
        )
        search_layout.add_widget(self.search_field)
        search_layout.add_widget(search_btn)
        filter_layout.add_widget(search_layout)
        
        # Topic and difficulty selection
        selection_layout = MDGridLayout(cols=2, spacing=10, size_hint_y=None, height=100)
        
        # Topic dropdown
        topic_layout = MDBoxLayout(orientation="vertical", spacing=5)
        topic_label = MDLabel(
            text="Tópico:",
            size_hint_y=None,
            height=20
        )
        self.topic_button = MDRaisedButton(
            text=self.selected_topic,
            size_hint=(1, None),
            height=50,
            on_release=self.show_topics_menu
        )
        topic_layout.add_widget(topic_label)
        topic_layout.add_widget(self.topic_button)
        selection_layout.add_widget(topic_layout)
        
        # Difficulty dropdown
        difficulty_layout = MDBoxLayout(orientation="vertical", spacing=5)
        difficulty_label = MDLabel(
            text="Dificuldade:",
            size_hint_y=None,
            height=20
        )
        self.difficulty_button = MDRaisedButton(
            text=self.selected_difficulty,
            size_hint=(1, None),
            height=50,
            on_release=self.show_difficulty_menu
        )
        difficulty_layout.add_widget(difficulty_label)
        difficulty_layout.add_widget(self.difficulty_button)
        selection_layout.add_widget(difficulty_layout)
        
        filter_layout.add_widget(selection_layout)
        
        # Additional filters
        additional_layout = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        
        # Only show questions with explanations
        explanation_layout = MDBoxLayout(orientation="horizontal", spacing=5)
        explanation_label = MDLabel(
            text="Apenas com explicações",
            size_hint_x=0.7
        )
        self.explanation_checkbox = MDCheckbox(size_hint_x=0.3)
        explanation_layout.add_widget(explanation_label)
        explanation_layout.add_widget(self.explanation_checkbox)
        additional_layout.add_widget(explanation_layout)
        
        # Only show unanswered questions
        unanswered_layout = MDBoxLayout(orientation="horizontal", spacing=5)
        unanswered_label = MDLabel(
            text="Apenas não respondidas",
            size_hint_x=0.7
        )
        self.unanswered_checkbox = MDCheckbox(size_hint_x=0.3)
        unanswered_layout.add_widget(unanswered_label)
        unanswered_layout.add_widget(self.unanswered_checkbox)
        additional_layout.add_widget(unanswered_layout)
        
        filter_layout.add_widget(additional_layout)
        
        main_layout.add_widget(filter_layout)
        
        # Active filters display
        self.filters_box = MDBoxLayout(
            orientation="horizontal",
            spacing=5,
            size_hint_y=None,
            height=50,
            padding=(10, 0, 10, 0)
        )
        self.update_active_filters()
        scroll_filters = ScrollView(size_hint=(1, None), height=50)
        scroll_filters.add_widget(self.filters_box)
        main_layout.add_widget(scroll_filters)
        
        # Results count
        self.results_label = MDLabel(
            text="0 questões encontradas",
            font_style="Caption",
            halign="center",
            size_hint_y=None,
            height=30
        )
        main_layout.add_widget(self.results_label)
        
        # Results list
        results_scroll = ScrollView(size_hint=(1, 1))
        self.results_list = MDList()
        results_scroll.add_widget(self.results_list)
        main_layout.add_widget(results_scroll)
        
        # Pagination
        pagination_layout = MDBoxLayout(
            orientation="horizontal",
            spacing=10,
            size_hint_y=None,
            height=50,
            padding=(10, 0, 10, 0)
        )
        
        self.prev_btn = MDRaisedButton(
            text="Anterior",
            on_release=self.prev_page,
            disabled=True
        )
        pagination_layout.add_widget(self.prev_btn)
        
        self.page_label = MDLabel(
            text="Página 0 de 0",
            halign="center",
            size_hint_x=1
        )
        pagination_layout.add_widget(self.page_label)
        
        self.next_btn = MDRaisedButton(
            text="Próximo",
            on_release=self.next_page,
            disabled=True
        )
        pagination_layout.add_widget(self.next_btn)
        
        main_layout.add_widget(pagination_layout)
        
        # Back button
        back_btn = MDFlatButton(
            text="Voltar",
            size_hint=(1, None),
            height=50,
            on_release=lambda x: self.go_back()
        )
        main_layout.add_widget(back_btn)
        
        self.add_widget(main_layout)
    
    def load_topics(self):
        """Load question topics from the database."""
        # In a real application, load topics from database
        # For now, we'll just use the predefined list
        
        # Example of how this would be done with a real database
        """
        try:
            self.topics = ["Todos"] + get_question_topics()
        except Exception as e:
            print(f"Erro ao carregar tópicos: {e}")
        """
        
        # Add "Todos" as first option if not already there
        if "Todos" not in self.topics:
            self.topics = ["Todos"] + self.topics
    
    def update_question_count(self):
        """Update the total question count."""
        # In a real application, get count from database
        # For now, just use a mock count
        
        # Example of how this would be done with a real database
        """
        try:
            self.total_questions = get_question_count()
            self.results_label.text = f"{self.total_questions} questões no banco de dados"
        except Exception as e:
            print(f"Erro ao obter contagem de questões: {e}")
            self.total_questions = 0
            self.results_label.text = "Erro ao contar questões"
        """
        
        # Mock count
        self.total_questions = 150
        self.results_label.text = f"{self.total_questions} questões no banco de dados"
    
    def show_topics_menu(self, button):
        """Show the topics dropdown menu."""
        items = [
            {
                "text": topic,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=topic: self.set_topic(x),
            } for topic in self.topics
        ]
        
        self.topics_menu = MDDropdownMenu(
            caller=button,
            items=items,
            width_mult=4,
        )
        self.topics_menu.open()
    
    def set_topic(self, topic):
        """Set the selected topic."""
        self.selected_topic = topic
        self.topic_button.text = topic
        if self.topics_menu:
            self.topics_menu.dismiss()
        
        # Automatically apply filters when topic changes
        self.apply_filters()
    
    def show_difficulty_menu(self, button):
        """Show the difficulty dropdown menu."""
        items = [
            {
                "text": difficulty,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=difficulty: self.set_difficulty(x),
            } for difficulty in self.difficulties
        ]
        
        self.difficulty_menu = MDDropdownMenu(
            caller=button,
            items=items,
            width_mult=4,
        )
        self.difficulty_menu.open()
    
    def set_difficulty(self, difficulty):
        """Set the selected difficulty."""
        self.selected_difficulty = difficulty
        self.difficulty_button.text = difficulty
        if self.difficulty_menu:
            self.difficulty_menu.dismiss()
        
        # Automatically apply filters when difficulty changes
        self.apply_filters()
    
    def apply_filters(self, *args):
        """Apply filters and search for questions."""
        # Reset to first page
        self.current_page = 1
        
        # Update active filters display
        self.update_active_filters()
        
        # Get search parameters
        keyword = self.search_field.text.strip()
        topic = None if self.selected_topic == "Todos" else self.selected_topic
        difficulty = None if self.selected_difficulty == "Todos" else self.selected_difficulty
        with_explanation = self.explanation_checkbox.active
        unanswered_only = self.unanswered_checkbox.active
        
        # Show loading dialog
        loading_dialog = MDDialog(
            title="Buscando",
            text="Buscando questões...",
            size_hint=(0.8, None)
        )
        self.dialogs.append(loading_dialog)
        loading_dialog.open()
        
        # In a real application, query the database
        # For now, just show mock results
        
        # Example of how this would be done with a real database
        """
        try:
            # Get filtered questions
            self.filtered_questions = get_filtered_questions(
                keyword=keyword,
                topic=topic,
                difficulty=difficulty,
                with_explanation=with_explanation,
                unanswered_only=unanswered_only,
                page=self.current_page,
                per_page=self.questions_per_page
            )
            
            # Get total count for pagination
            total_results = len(self.filtered_questions)
            self.total_pages = (total_results + self.questions_per_page - 1) // self.questions_per_page
            
            loading_dialog.dismiss()
            self.dialogs.remove(loading_dialog)
            
            # Update results count
            self.results_label.text = f"{total_results} questões encontradas"
            
            # Display results
            self.display_results()
            
        except Exception as e:
            loading_dialog.dismiss()
            self.dialogs.remove(loading_dialog)
            self.show_error_dialog(f"Erro ao buscar questões: {e}")
        """
        
        # Mock filtering
        import time
        import random
        time.sleep(1)
        
        loading_dialog.dismiss()
        self.dialogs.remove(loading_dialog)
        
        # Create mock filtered questions based on filters
        base_questions = [
            {
                "id": 1,
                "question": "Qual é a principal finalidade do Termo de Abertura do Projeto?",
                "topic": "Integração",
                "difficulty": "Fácil",
                "has_explanation": True,
                "answered": True
            },
            {
                "id": 2,
                "question": "Como calcular a variação de custo (CV) no gerenciamento do valor agregado?",
                "topic": "Custo",
                "difficulty": "Média",
                "has_explanation": True,
                "answered": False
            },
            {
                "id": 3,
                "question": "Qual método é mais adequado para estimar a duração de atividades com alta incerteza?",
                "topic": "Tempo",
                "difficulty": "Difícil",
                "has_explanation": False,
                "answered": True
            },
            {
                "id": 4,
                "question": "O que é o Método do Caminho Crítico (CPM) e qual sua principal finalidade?",
                "topic": "Tempo",
                "difficulty": "Média",
                "has_explanation": True,
                "answered": False
            },
            {
                "id": 5,
                "question": "Quais são os componentes principais da matriz RACI?",
                "topic": "Recursos Humanos",
                "difficulty": "Média",
                "has_explanation": True,
                "answered": False
            }
        ]
        
        # Apply mock filtering
        filtered = base_questions.copy()
        
        if topic:
            filtered = [q for q in filtered if q["topic"] == topic]
        
        if difficulty and difficulty != "Todos":
            filtered = [q for q in filtered if q["difficulty"] == difficulty]
        
        if keyword:
            filtered = [q for q in filtered if keyword.lower() in q["question"].lower()]
        
        if with_explanation:
            filtered = [q for q in filtered if q["has_explanation"]]
        
        if unanswered_only:
            filtered = [q for q in filtered if not q["answered"]]
        
        # Generate additional mock results if we have too few
        if len(filtered) < 20 and not keyword:
            topics_to_use = [topic] if topic else self.topics[1:]  # Skip "Todos"
            difficulties_to_use = [difficulty] if difficulty and difficulty != "Todos" else self.difficulties[1:]  # Skip "Todos"
            
            for i in range(20 - len(filtered)):
                q_topic = random.choice(topics_to_use)
                q_difficulty = random.choice(difficulties_to_use)
                q_has_explanation = True if with_explanation else random.choice([True, False])
                q_answered = False if unanswered_only else random.choice([True, False])
                
                filtered.append({
                    "id": len(filtered) + 6 + i,
                    "question": f"Pergunta de exemplo sobre {q_topic} com dificuldade {q_difficulty}?",
                    "topic": q_topic,
                    "difficulty": q_difficulty,
                    "has_explanation": q_has_explanation,
                    "answered": q_answered
                })
        
        self.filtered_questions = filtered
        total_results = len(filtered)
        self.total_pages = max(1, (total_results + self.questions_per_page - 1) // self.questions_per_page)
        
        # Update results count
        self.results_label.text = f"{total_results} questões encontradas"
        
        # Display results
        self.display_results()
    
    def update_active_filters(self):
        """Update the active filters display."""
        # Clear current filters
        self.filters_box.clear_widgets()
        self.active_filters = []
        
        # Add filter chips
        if self.selected_topic != "Todos":
            self.add_filter_chip(f"Tópico: {self.selected_topic}", "topic")
        
        if self.selected_difficulty != "Todos":
            self.add_filter_chip(f"Dificuldade: {self.selected_difficulty}", "difficulty")
        
        if self.search_field.text.strip():
            self.add_filter_chip(f"Busca: {self.search_field.text.strip()}", "keyword")
        
        if self.explanation_checkbox.active:
            self.add_filter_chip("Com explicação", "explanation")
        
        if self.unanswered_checkbox.active:
            self.add_filter_chip("Não respondidas", "unanswered")
        
        # Add clear all button if we have any filters
        if self.active_filters:
            clear_btn = MDFlatButton(
                text="Limpar Filtros",
                on_release=self.clear_all_filters,
                size_hint=(None, None),
                height=30
            )
            self.filters_box.add_widget(clear_btn)
    
    def add_filter_chip(self, text, filter_type):
        """Add a filter chip to the active filters display."""
        chip = MDChip(
            text=text,
            icon="close-circle",
            on_release=lambda x, ft=filter_type: self.remove_filter(ft)
        )
        self.filters_box.add_widget(chip)
        self.active_filters.append(filter_type)
    
    def remove_filter(self, filter_type):
        """Remove a specific filter."""
        if filter_type == "topic":
            self.selected_topic = "Todos"
            self.topic_button.text = "Todos"
        elif filter_type == "difficulty":
            self.selected_difficulty = "Todos"
            self.difficulty_button.text = "Todos"
        elif filter_type == "keyword":
            self.search_field.text = ""
        elif filter_type == "explanation":
            self.explanation_checkbox.active = False
        elif filter_type == "unanswered":
            self.unanswered_checkbox.active = False
        
        # Apply filters again
        self.apply_filters()
    
    def clear_all_filters(self, *args):
        """Clear all active filters."""
        self.selected_topic = "Todos"
        self.topic_button.text = "Todos"
        self.selected_difficulty = "Todos"
        self.difficulty_button.text = "Todos"
        self.search_field.text = ""
        self.explanation_checkbox.active = False
        self.unanswered_checkbox.active = False
        
        # Apply filters again
        self.apply_filters()
    
    def display_results(self):
        """Display the filtered results."""
        # Clear current results
        self.results_list.clear_widgets()
        
        # Calculate page range
        start_idx = (self.current_page - 1) * self.questions_per_page
        end_idx = min(start_idx + self.questions_per_page, len(self.filtered_questions))
        
        # Display page items
        page_items = self.filtered_questions[start_idx:end_idx]
        
        if not page_items:
            # No results
            no_results = MDLabel(
                text="Nenhuma questão encontrada com os filtros selecionados.",
                halign="center"
            )
            self.results_list.add_widget(no_results)
        else:
            # Add each question to the list
            for i, question in enumerate(page_items):
                # Create list item
                item = TwoLineAvatarIconListItem(
                    text=question["question"],
                    secondary_text=f"{question['topic']} • {question['difficulty']}",
                    on_release=lambda x, q=question: self.view_question(q)
                )
                
                # Add icon based on difficulty
                if question["difficulty"] == "Fácil":
                    icon = IconLeftWidget(icon="circle-slice-1", theme_text_color="Custom", text_color=(0, 0.7, 0, 1))
                elif question["difficulty"] == "Média":
                    icon = IconLeftWidget(icon="circle-slice-4", theme_text_color="Custom", text_color=(0.9, 0.9, 0, 1))
                else:  # Difícil
                    icon = IconLeftWidget(icon="circle-slice-8", theme_text_color="Custom", text_color=(0.7, 0, 0, 1))
                
                item.add_widget(icon)
                self.results_list.add_widget(item)
        
        # Update pagination
        self.update_pagination()
    
    def update_pagination(self):
        """Update pagination controls."""
        self.page_label.text = f"Página {self.current_page} de {self.total_pages}"
        
        # Update button states
        self.prev_btn.disabled = (self.current_page <= 1)
        self.next_btn.disabled = (self.current_page >= self.total_pages)
    
    def prev_page(self, *args):
        """Go to the previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.display_results()
    
    def next_page(self, *args):
        """Go to the next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_results()
    
    def view_question(self, question):
        """View a question's details."""
        # Get full question details from database
        full_question = self.db.get_question_by_text(question['question'])
        if not full_question:
            return
            
        # Create content for dialog
        content = MDBoxLayout(orientation="vertical", spacing=10, padding=10, size_hint_y=None, height=400)
        
        # Question text - remove [b] tags
        question_text = full_question["question"].replace('[b]', '').replace('[/b]', '')
        question_label = MDLabel(
            text=question_text,
            font_style="Body1",
            halign="left",
            size_hint_y=None,
            height=80
        )
        content.add_widget(question_label)
        
        # Options
        options_scroll = ScrollView(size_hint=(1, None), height=200)
        options_list = MDList()
        
        for i, option_text in enumerate(full_question["options"]):
            # Remove [b] tags from options
            option_text = option_text.replace('[b]', '').replace('[/b]', '')
            option_text = f"{chr(65 + i)}. {option_text}"
            
            # Mark correct option
            if i == full_question["correct_answer"]:
                option_item = TwoLineAvatarIconListItem(
                    text=option_text,
                    secondary_text="✓ Resposta correta"
                )
                icon = IconLeftWidget(icon="check-circle", theme_text_color="Custom", text_color=(0, 0.7, 0, 1))
            else:
                option_item = TwoLineAvatarIconListItem(text=option_text)
                icon = IconLeftWidget(icon="checkbox-blank-circle-outline")
            
            option_item.add_widget(icon)
            options_list.add_widget(option_item)
        
        options_scroll.add_widget(options_list)
        content.add_widget(options_scroll)
        
        # Explanation - remove [b] tags
        if full_question.get("explanation"):
            explanation_text = full_question["explanation"].replace('[b]', '').replace('[/b]', '')
            explanation_label = MDLabel(
                text=f"Explicação: {explanation_text}",
                font_style="Body2",
                halign="left",
                size_hint_y=None,
                height=100
            )
            content.add_widget(explanation_label)
        
        # Create dialog
        question_dialog = MDDialog(
            title=f"Questão #{full_question.get('id', '')}",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Fechar",
                    on_release=lambda x: question_dialog.dismiss()
                )
            ],
            size_hint=(0.9, None)
        )
        self.dialogs.append(question_dialog)
        question_dialog.open()
    
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