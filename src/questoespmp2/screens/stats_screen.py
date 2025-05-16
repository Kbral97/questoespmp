from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.snackbar import Snackbar

import logging
from ..database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class StatsScreen(MDScreen):
    """Screen for displaying statistics."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "stats"
        self.db_manager = DatabaseManager()
        self.setup_ui()
        self.confirm_dialog = None
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main ScrollView
        main_scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            size_hint=(1, 1)
        )
        
        # Main content layout
        layout = BoxLayout(
            orientation='vertical', 
            spacing=dp(10), 
            padding=dp(10),
            size_hint_y=None
        )
        # Bind height para permitir rolagem
        layout.bind(minimum_height=layout.setter('height'))
        
        # Title
        title = MDLabel(
            text="Estatísticas",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        layout.add_widget(title)
        
        # Overall Stats Card
        overall_card = MDCard(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(10),
            size_hint=(None, None),
            size=(dp(300), dp(230)),  # Aumentado para acomodar nova label
            pos_hint={'center_x': 0.5}
        )
        
        # Overall Stats Title
        overall_title = MDLabel(
            text="Estatísticas Gerais",
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        overall_card.add_widget(overall_title)
        
        # Total Questions Answered
        self.total_questions_answered = MDLabel(
            text="Total de Questões Respondidas: 0",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        overall_card.add_widget(self.total_questions_answered)
        
        # Total Questions in Database
        self.total_questions_db = MDLabel(
            text="Total de Questões no Banco: 0",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        overall_card.add_widget(self.total_questions_db)
        
        # Correct Answers
        self.correct_answers = MDLabel(
            text="Respostas Corretas: 0",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        overall_card.add_widget(self.correct_answers)
        
        # Accuracy
        self.accuracy = MDLabel(
            text="Precisão: 0%",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        overall_card.add_widget(self.accuracy)
        
        layout.add_widget(overall_card)
        
        # Theme Stats Card
        theme_card = MDCard(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(300),  # Altura fixa para o card
            size_hint_x=1
        )
        
        # Theme Stats Title
        theme_title = MDLabel(
            text="Estatísticas por Tema",
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        theme_card.add_widget(theme_title)
        
        # Scrollable list for themes
        scroll = ScrollView(size_hint=(1, 1))
        self.themes_list = MDList()
        scroll.add_widget(self.themes_list)
        theme_card.add_widget(scroll)
        
        layout.add_widget(theme_card)
        
        # Bottom buttons layout
        buttons_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            size_hint_y=None,
            height=dp(120)
        )
        
        # Back Button
        back_btn = MDRaisedButton(
            text="Voltar",
            size_hint=(1, None),
            height=dp(50),
            on_release=self.go_back
        )
        buttons_layout.add_widget(back_btn)
        
        # Delete All Questions Button
        delete_btn = MDRaisedButton(
            text="Deletar Todas as Questões",
            size_hint=(1, None),
            height=dp(50),
            md_bg_color=(0.8, 0.1, 0.1, 1),  # Vermelho
            on_release=self.show_delete_confirmation
        )
        buttons_layout.add_widget(delete_btn)
        
        layout.add_widget(buttons_layout)
        
        # Adicionar o layout ao ScrollView
        main_scroll.add_widget(layout)
        
        # Adicionar o ScrollView à tela
        self.add_widget(main_scroll)
    
    def show_delete_confirmation(self, *args):
        """Mostra diálogo de confirmação antes de deletar todas as questões."""
        if not self.confirm_dialog:
            self.confirm_dialog = MDDialog(
                title="Atenção!",
                text="Esta ação irá deletar TODAS as questões do banco de dados e resetar todas as estatísticas. Esta ação é irreversível. Deseja continuar?",
                buttons=[
                    MDFlatButton(
                        text="CANCELAR",
                        theme_text_color="Custom",
                        text_color=(0.3, 0.3, 0.3, 1),
                        on_release=lambda x: self.confirm_dialog.dismiss()
                    ),
                    MDFlatButton(
                        text="CONFIRMAR",
                        theme_text_color="Custom",
                        text_color=(0.8, 0.1, 0.1, 1),
                        on_release=self.delete_all_questions
                    ),
                ],
            )
        self.confirm_dialog.open()
    
    def delete_all_questions(self, *args):
        """Deleta todas as questões e resetar estatísticas."""
        try:
            # Fechar o diálogo
            self.confirm_dialog.dismiss()
            
            # Deletar todas as questões
            result = self.db_manager.clear_all_questions()
            
            if result:
                Snackbar(
                    text="Todas as questões e estatísticas foram removidas com sucesso!",
                    duration=3
                ).open()
                
                # Atualizar a tela
                self.update_statistics()
            else:
                Snackbar(
                    text="Erro ao remover questões. Verifique o log para mais detalhes.",
                    duration=3
                ).open()
        except Exception as e:
            logger.error(f"Erro ao deletar questões: {e}")
            Snackbar(
                text=f"Erro: {str(e)}",
                duration=3
            ).open()
    
    def on_pre_enter(self):
        """Update statistics when entering the screen."""
        self.update_statistics()
        
    def update_statistics(self):
        """Update statistics from the database."""
        try:
            # Get general statistics
            stats = self.db_manager.get_statistics()
            
            # Update total questions answered and accuracy
            total_questions_answered = stats.get('total_questions', 0)
            total_correct = stats.get('total_correct', 0)
            accuracy = stats.get('accuracy', 0) * 100
            
            self.total_questions_answered.text = f"Total de Questões Respondidas: {total_questions_answered}"
            self.correct_answers.text = f"Respostas Corretas: {total_correct}"
            self.accuracy.text = f"Precisão: {accuracy:.1f}%"
            
            # Update total questions in database
            total_questions_db = self.db_manager.get_total_questions_in_database()
            self.total_questions_db.text = f"Total de Questões no Banco: {total_questions_db}"
            
            # Update topics list
            self.themes_list.clear_widgets()
            topics = self.db_manager.get_all_topics()
            
            if not topics:
                self.themes_list.add_widget(
                    OneLineListItem(
                        text="Nenhum tema encontrado"
                    )
                )
            else:
                for topic in topics:
                    self.themes_list.add_widget(
                        TwoLineListItem(
                            text=f"{topic['topic']}",
                            secondary_text=f"Respondidas: {topic['questions_answered']} | Corretas: {topic['correct_answers']} | Precisão: {topic['accuracy']}%"
                        )
                    )
                    
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
            self.total_questions_answered.text = "Total de Questões Respondidas: 0"
            self.total_questions_db.text = "Total de Questões no Banco: 0"
            self.correct_answers.text = "Respostas Corretas: 0"
            self.accuracy.text = "Precisão: 0.0%"
    
    def go_back(self, *args):
        """Return to home screen."""
        self.manager.current = "home" 