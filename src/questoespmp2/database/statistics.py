import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class StatisticsManager:
    def __init__(self):
        self.data_dir = Path("data")
        self.stats_file = self.data_dir / "statistics.json"
        self.initialize_statistics()
        
    def initialize_statistics(self):
        """Inicializa o arquivo de estatísticas se não existir"""
        try:
            if not self.stats_file.exists():
                self.data_dir.mkdir(exist_ok=True)
                self.stats_file.write_text("{}")
                logger.info("Arquivo de estatísticas inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar estatísticas: {e}")
            
    def clear_statistics(self):
        """Limpa todas as estatísticas"""
        try:
            self.stats_file.write_text("{}")
            logger.info("Estatísticas limpas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao limpar estatísticas: {e}")
            
    def get_statistics(self):
        """Retorna as estatísticas atuais"""
        try:
            if self.stats_file.exists():
                return json.loads(self.stats_file.read_text())
            return {}
        except Exception as e:
            logger.error(f"Erro ao ler estatísticas: {e}")
            return {}
            
    def update_statistics(self, new_stats):
        """Atualiza as estatísticas"""
        try:
            current_stats = self.get_statistics()
            current_stats.update(new_stats)
            self.stats_file.write_text(json.dumps(current_stats, indent=2))
            logger.info("Estatísticas atualizadas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
            
    def increment_counter(self, counter_name):
        """Incrementa um contador específico"""
        try:
            stats = self.get_statistics()
            stats[counter_name] = stats.get(counter_name, 0) + 1
            self.stats_file.write_text(json.dumps(stats, indent=2))
            logger.info(f"Contador {counter_name} incrementado")
        except Exception as e:
            logger.error(f"Erro ao incrementar contador {counter_name}: {e}") 