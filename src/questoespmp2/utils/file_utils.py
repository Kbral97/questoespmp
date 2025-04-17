#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilidades para processamento de arquivos de diferentes formatos.
"""

import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_document(
    file_path: str,
    is_pdf: bool = False,
    is_word: bool = False,
    is_text: bool = False
) -> Optional[str]:
    """
    Processa um documento e extrai seu texto.
    
    Args:
        file_path: Caminho para o arquivo
        is_pdf: Se o arquivo é um PDF
        is_word: Se o arquivo é um documento Word
        is_text: Se o arquivo é um arquivo de texto
        
    Returns:
        O texto extraído do documento ou None se ocorrer um erro
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Arquivo não encontrado: {file_path}")
            return None
            
        # Detecta o tipo de arquivo se não foi especificado
        if not any([is_pdf, is_word, is_text]):
            ext = os.path.splitext(file_path)[1].lower()
            is_pdf = ext == '.pdf'
            is_word = ext in ['.doc', '.docx']
            is_text = ext in ['.txt', '.md']
            
        # Processa o arquivo de acordo com seu tipo
        if is_pdf:
            return extract_text_from_pdf(file_path)
        elif is_word:
            return extract_text_from_word(file_path)
        elif is_text:
            return extract_text_from_text(file_path)
        else:
            logger.error(f"Tipo de arquivo não suportado: {file_path}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao processar arquivo {file_path}: {str(e)}")
        return None
        
def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """
    Extrai texto de um arquivo PDF.
    
    Args:
        file_path: Caminho para o arquivo PDF
        
    Returns:
        O texto extraído do PDF ou None se ocorrer um erro
    """
    try:
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            logger.warning("PyPDF2 não está instalado. Tentando pdfplumber...")
            
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                logger.error("Nenhuma biblioteca para processamento de PDF está instalada.")
                logger.error("Instale PyPDF2 ou pdfplumber para processar arquivos PDF.")
                return None
                
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF {file_path}: {str(e)}")
        return None
        
def extract_text_from_word(file_path: str) -> Optional[str]:
    """
    Extrai texto de um documento Word.
    
    Args:
        file_path: Caminho para o arquivo Word
        
    Returns:
        O texto extraído do documento Word ou None se ocorrer um erro
    """
    try:
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except ImportError:
            logger.error("python-docx não está instalado.")
            logger.error("Instale python-docx para processar arquivos Word (.docx).")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao extrair texto do Word {file_path}: {str(e)}")
        return None
        
def extract_text_from_text(file_path: str) -> Optional[str]:
    """
    Extrai texto de um arquivo de texto.
    
    Args:
        file_path: Caminho para o arquivo de texto
        
    Returns:
        O texto extraído do arquivo ou None se ocorrer um erro
    """
    try:
        # Tenta diferentes codificações
        encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
                
        logger.error(f"Não foi possível ler o arquivo de texto {file_path} com nenhuma codificação.")
        return None
        
    except Exception as e:
        logger.error(f"Erro ao extrair texto do arquivo {file_path}: {str(e)}")
        return None

def clean_text(text):
    """
    Clean and normalize extracted text.
    
    Args:
        text (str): Text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple newlines with a single one
    import re
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Replace multiple spaces with a single one
    text = re.sub(r' +', ' ', text)
    
    # Fix common OCR/extraction issues
    text = text.replace('•', '\n• ')  # Make bullet points more obvious
    text = text.replace('…', '...')  # Replace ellipsis
    
    return text.strip()

def save_document_to_temp(file_content, file_name):
    """
    Save a document to a temporary file.
    
    Args:
        file_content (bytes): Content of the file
        file_name (str): Name to give to the temporary file
        
    Returns:
        str: Path to the temporary file
    """
    # Create a temporary directory if it doesn't exist
    temp_dir = os.path.join(tempfile.gettempdir(), 'questoespmp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create a file path with a unique name
    file_path = os.path.join(temp_dir, file_name)
    
    # Write the content to the file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    logger.info(f"Documento salvo em arquivo temporário: {file_path}")
    return file_path

def delete_temp_file(file_path):
    """
    Delete a temporary file.
    
    Args:
        file_path (str): Path to the temporary file
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Arquivo temporário removido: {file_path}")
    except Exception as e:
        logger.warning(f"Erro ao remover arquivo temporário {file_path}: {str(e)}")
