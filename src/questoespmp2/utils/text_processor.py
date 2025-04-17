#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Processador de texto para documentos e resumos.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from ..database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TextProcessor:
    """Processa arquivos de texto e gerencia trechos de texto."""
    
    def __init__(self):
        """Inicializa o processador de texto com configuração."""
        self.db = DatabaseManager()
        self.logger = logging.getLogger(__name__)
        
        # Configurações de chunking
        self.chunk_size = 1200  # Tamanho reduzido para melhor foco em conceitos específicos
        self.chunk_overlap = 120  # Overlap de 10% para manter continuidade
        
        # Padrões de limpeza
        self.cleanup_patterns = [
            (r'\s+', ' '),  # Remove espaços extras
            (r'[\r\n]+', '\n'),  # Normaliza quebras de linha
            (r'[^\S\r\n]+', ' '),  # Remove espaços em branco exceto quebras de linha
        ]
        
        self.logger.info("TextProcessor inicializado com chunk_size=%d, chunk_overlap=%d", 
                       self.chunk_size, self.chunk_overlap)
        
    def clean_text(self, text: str) -> str:
        """Limpa e normaliza o conteúdo do texto."""
        try:
            # Aplica padrões de limpeza
            for pattern, replacement in self.cleanup_patterns:
                text = re.sub(pattern, replacement, text)
            
            # Remove caracteres especiais mantendo pontuação básica
            text = re.sub(r'[^\w\s.,!?;:()\-\'\"]+', '', text)
            
            # Remove espaços no início e fim
            text = text.strip()
            
            return text
        except Exception as e:
            self.logger.error(f"Erro ao limpar texto: {str(e)}")
            return text
            
    def split_into_chunks(self, text: str) -> List[str]:
        """Divide o texto em trechos sobrepostos."""
        try:
            chunks = []
            start = 0
            text_length = len(text)
            
            while start < text_length:
                # Define o fim do chunk atual
                end = start + self.chunk_size
                
                # Se não é o último chunk, tenta quebrar em uma palavra
                if end < text_length:
                    # Procura o último espaço antes do fim do chunk
                    last_space = text.rfind(' ', start, end)
                    if last_space != -1:
                        end = last_space
                
                # Extrai o chunk
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                
                # Move o início para o próximo chunk, considerando o overlap
                start = end - self.chunk_overlap
            
            return chunks
        except Exception as e:
            self.logger.error(f"Erro ao dividir texto em chunks: {str(e)}")
            return []
            
    def process_file(self, file_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> int:
        """
        Processa um único arquivo e armazena os chunks no banco de dados.
        
        Args:
            file_path: Caminho para o arquivo
            progress_callback: Função opcional para reportar progresso
            
        Returns:
            int: Número de chunks processados
        """
        try:
            self.logger.info(f"Processando arquivo: {file_path}")
            
            # Verifica se o arquivo existe
            if not os.path.exists(file_path):
                self.logger.error(f"Arquivo não encontrado: {file_path}")
                return 0
            
            # Determina o tipo do arquivo
            file_ext = os.path.splitext(file_path)[1].lower()
            is_pdf = file_ext == '.pdf'
            is_word = file_ext in ['.doc', '.docx']
            is_text = file_ext in ['.txt', '.md']
            
            # Atualiza o progresso
            if progress_callback:
                progress_callback(10)
                
            # Processa o arquivo de acordo com seu tipo
            from .file_utils import process_document
            content = None
            try:
                content = process_document(file_path, is_pdf=is_pdf, is_word=is_word, is_text=is_text)
                if progress_callback:
                    progress_callback(30)
            except Exception as e:
                self.logger.error(f"Erro ao processar arquivo {file_path}: {str(e)}")
                raise
            
            if not content:
                self.logger.error(f"Nenhum conteúdo extraído do arquivo: {file_path}")
                return 0
            
            # Limpa o texto
            cleaned_text = self.clean_text(content)
            if progress_callback:
                progress_callback(40)
            
            # Divide em chunks
            chunks = self.split_into_chunks(cleaned_text)
            if progress_callback:
                progress_callback(50)
            
            if not chunks:
                self.logger.warning(f"Nenhum chunk gerado para o arquivo: {file_path}")
                return 0
            
            # Obtém o nome do arquivo
            file_name = os.path.basename(file_path)
            
            # Remove chunks antigos do mesmo arquivo
            self.db.remove_chunks_by_file(file_name)
            if progress_callback:
                progress_callback(60)
            
            # Insere os novos chunks
            for i, chunk_text in enumerate(chunks, 1):
                chunk_data = {
                    'raw_text': chunk_text,
                    'file_name': file_name,
                    'chunk_number': i,
                    'embedding': None  # Pode ser adicionado posteriormente se necessário
                }
                self.db.insert_text_chunk(chunk_data)
                
                # Atualiza o progresso se houver callback
                if progress_callback:
                    progress = 60 + int((i / len(chunks)) * 30)
                    progress_callback(min(progress, 90))
            
            # Garante que o progresso chegue a 100%
            if progress_callback:
                progress_callback(100)
            
            self.logger.info(f"Processados com sucesso {len(chunks)} chunks de {file_name}")
            return len(chunks)
            
        except Exception as e:
            self.logger.error(f"Erro ao processar arquivo {file_path}: {str(e)}")
            raise
            
    def process_directory(self, directory_path: str) -> Dict[str, Any]:
        """Processa todos os arquivos de texto em um diretório."""
        try:
            self.logger.info(f"Processando diretório: {directory_path}")
            
            # Verifica se o diretório existe
            if not os.path.exists(directory_path):
                self.logger.error(f"Diretório não encontrado: {directory_path}")
                return {'success': False, 'message': 'Diretório não encontrado'}
            
            # Lista todos os arquivos de texto no diretório
            text_files = [f for f in os.listdir(directory_path) 
                         if f.endswith(('.txt', '.md', '.pdf', '.doc', '.docx'))]
            
            if not text_files:
                self.logger.warning(f"Nenhum arquivo de texto encontrado no diretório: {directory_path}")
                return {'success': False, 'message': 'Nenhum arquivo de texto encontrado'}
            
            # Processa cada arquivo
            results = {
                'total_files': len(text_files),
                'processed_files': 0,
                'failed_files': 0,
                'total_chunks': 0
            }
            
            for file_name in text_files:
                file_path = os.path.join(directory_path, file_name)
                try:
                    chunks = self.process_file(file_path)
                    if chunks:
                        results['processed_files'] += 1
                        results['total_chunks'] += chunks
                    else:
                        results['failed_files'] += 1
                except Exception:
                    results['failed_files'] += 1
            
            # Obtém o total de chunks no banco
            results['total_chunks'] = self.db.get_total_chunks()
            
            self.logger.info(f"Processamento do diretório concluído: {results}")
            return {'success': True, 'results': results}
            
        except Exception as e:
            self.logger.error(f"Erro ao processar diretório {directory_path}: {str(e)}")
            return {'success': False, 'message': str(e)} 