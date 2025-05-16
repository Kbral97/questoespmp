import json
import traceback
import os
import logging
import PyPDF2
import pdfplumber
import openai

logger = logging.getLogger(__name__)

def generate_topic_summary(topic, text):
    """
    Gera um resumo estruturado para um tópico específico usando a API do OpenAI.
    """
    logger.info("[GENERATE-SUMMARY] Iniciando geração de resumo")
    logger.info(f"[GENERATE-SUMMARY] Tópico: {topic}")
    logger.info(f"[GENERATE-SUMMARY] Tamanho do texto: {len(text)} caracteres")
    
    try:
        # Preparar o prompt para a API
        prompt = f"""
        Analise o seguinte tópico e texto relacionado ao PMBOK e gere um resumo estruturado.
        
        Tópico: {topic}
        
        Texto: {text}
        
        Gere um resumo que inclua:
        1. Um resumo conciso e informativo
        2. Pontos-chave principais
        3. Exemplos práticos
        4. Referências ao PMBOK
        5. Domínios do PMP relacionados
        
        Retorne a resposta em formato JSON com a seguinte estrutura:
        {{
            "summary": "Resumo conciso do tópico",
            "key_points": ["Ponto 1", "Ponto 2", ...],
            "practical_examples": ["Exemplo 1", "Exemplo 2", ...],
            "pmbok_references": ["Referência 1", "Referência 2", ...],
            "domains": ["Domínio 1", "Domínio 2", ...]
        }}
        """
        
        logger.info("[GENERATE-SUMMARY] Enviando requisição para a API do OpenAI")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos e PMBOK."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        logger.info("[GENERATE-SUMMARY] Resposta recebida da API")
        
        # Extrair e validar a resposta
        try:
            summary_data = json.loads(response.choices[0].message.content)
            
            # Validar campos obrigatórios
            required_fields = ['summary', 'key_points', 'practical_examples', 'pmbok_references', 'domains']
            missing_fields = [field for field in required_fields if field not in summary_data]
            
            if missing_fields:
                logger.error(f"[GENERATE-SUMMARY] Campos obrigatórios ausentes: {missing_fields}")
                raise ValueError(f"Campos obrigatórios ausentes: {missing_fields}")
                
            logger.info("[GENERATE-SUMMARY] Resumo gerado com sucesso")
            return summary_data
            
        except json.JSONDecodeError as e:
            logger.error(f"[GENERATE-SUMMARY] Erro ao decodificar JSON: {str(e)}")
            logger.error(f"[GENERATE-SUMMARY] Resposta bruta: {response.choices[0].message.content}")
            raise ValueError(f"Erro ao decodificar resposta da API: {str(e)}")
            
    except Exception as e:
        logger.error(f"[GENERATE-SUMMARY] Erro ao gerar resumo: {str(e)}")
        logger.error(f"[GENERATE-SUMMARY] Tipo do erro: {type(e)}")
        logger.error(f"[GENERATE-SUMMARY] Stack trace: {traceback.format_exc()}")
        raise ValueError(f"Falha ao gerar resumo: {str(e)}")

def extract_text_from_pdf(pdf_path):
    """
    Extrai texto de um arquivo PDF usando PyPDF2 ou pdfplumber como fallback.
    """
    logger.info(f"[EXTRACT-TEXT] Iniciando extração de texto do PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"[EXTRACT-TEXT] Arquivo não encontrado: {pdf_path}")
        raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
        
    if not pdf_path.lower().endswith('.pdf'):
        logger.error(f"[EXTRACT-TEXT] Arquivo não é um PDF: {pdf_path}")
        raise ValueError(f"Arquivo não é um PDF: {pdf_path}")
        
    # Primeira tentativa: PyPDF2
    try:
        logger.info("[EXTRACT-TEXT] Tentando extrair texto com PyPDF2")
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
        if not text.strip():
            logger.warning("[EXTRACT-TEXT] PyPDF2 não conseguiu extrair texto")
            raise ValueError("PyPDF2 não conseguiu extrair texto")
            
        logger.info(f"[EXTRACT-TEXT] PyPDF2 extraiu {len(text)} caracteres")
        return text
        
    except Exception as e:
        logger.error(f"[EXTRACT-TEXT] Erro ao extrair texto com PyPDF2: {str(e)}")
        logger.error(f"[EXTRACT-TEXT] Tipo do erro: {type(e)}")
        logger.error(f"[EXTRACT-TEXT] Stack trace: {traceback.format_exc()}")
        
        # Segunda tentativa: pdfplumber
        try:
            logger.info("[EXTRACT-TEXT] Tentando extrair texto com pdfplumber")
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        
            if not text.strip():
                logger.error("[EXTRACT-TEXT] pdfplumber não conseguiu extrair texto")
                raise ValueError("pdfplumber não conseguiu extrair texto")
                
            logger.info(f"[EXTRACT-TEXT] pdfplumber extraiu {len(text)} caracteres")
            return text
            
        except Exception as e:
            logger.error(f"[EXTRACT-TEXT] Erro ao extrair texto com pdfplumber: {str(e)}")
            logger.error(f"[EXTRACT-TEXT] Tipo do erro: {type(e)}")
            logger.error(f"[EXTRACT-TEXT] Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Falha ao extrair texto do PDF: {str(e)}") 