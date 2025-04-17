import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from pathlib import Path
from questoespmp2.database.statistics import StatisticsManager

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Questões PMP")
        self.root.geometry("800x600")
        
        # Inicializar gerenciador de estatísticas
        self.stats_manager = StatisticsManager()
        
        # Configurar estilo
        self.style = ttk.Style()
        self.style.configure("Danger.TButton", foreground="red")
        
        # Frame principal
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Botão de limpeza
        self.clear_button = ttk.Button(
            self.main_frame,
            text="Limpar Banco de Dados",
            command=self.confirm_clear_database,
            style="Danger.TButton"
        )
        self.clear_button.grid(row=0, column=0, pady=10)
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        
    def confirm_clear_database(self):
        """Primeira camada de confirmação"""
        response = messagebox.askyesno(
            "Confirmar Limpeza",
            "Você está prestes a apagar todo o banco de questões e zerar as estatísticas.\n"
            "Esta ação não pode ser desfeita.\n\n"
            "Deseja continuar?"
        )
        
        if response:
            self.confirm_clear_database_final()
            
    def confirm_clear_database_final(self):
        """Segunda camada de confirmação"""
        response = messagebox.askyesno(
            "Confirmação Final",
            "ATENÇÃO: Esta é a confirmação final!\n\n"
            "Você tem certeza que deseja:\n"
            "1. Apagar todas as questões do banco de dados\n"
            "2. Zerar todas as estatísticas\n"
            "3. Remover todos os dados de treinamento\n\n"
            "Esta ação é irreversível!"
        )
        
        if response:
            self.clear_database()
            
    def clear_database(self):
        """Executa a limpeza do banco de dados"""
        try:
            # Caminhos dos arquivos
            data_dir = Path("data")
            questions_file = data_dir / "questions.json"
            training_file = data_dir / "training_data.json"
            
            # Remover arquivos
            if questions_file.exists():
                questions_file.unlink()
            if training_file.exists():
                training_file.unlink()
                
            # Criar arquivos vazios
            questions_file.write_text("[]")
            training_file.write_text("[]")
            
            # Limpar estatísticas
            self.stats_manager.clear_statistics()
            
            messagebox.showinfo(
                "Sucesso",
                "Banco de dados e estatísticas foram limpos com sucesso!"
            )
            
        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao limpar o banco de dados:\n{str(e)}"
            )

def main():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main() 