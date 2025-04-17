#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Conversor de CSV para formato de fine-tuning da OpenAI.
"""

import os
import csv
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def convert_csv_to_fine_tuning(csv_path: str, output_path: Optional[str] = None) -> str:
    """
    Converte um arquivo CSV para o formato JSONL usado para fine-tuning da OpenAI.
    
    Args:
        csv_path: Caminho para o arquivo CSV
        output_path: Caminho para salvar o arquivo JSONL (opcional)
        
    Returns:
        Caminho do arquivo JSONL gerado
    """
    logger.info(f"Convertendo {csv_path} para formato de fine-tuning")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_path}")
    
    # Se output_path não for fornecido, usa o mesmo diretório com extensão .jsonl
    if not output_path:
        base_path = os.path.splitext(csv_path)[0]
        output_path = f"{base_path}.jsonl"
    
    samples = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                # Verificar se tem os campos essenciais
                if 'prompt' not in row or 'completion' not in row:
                    logger.warning("Linha sem prompt ou completion ignorada")
                    continue
                
                # Criar o sample no formato da OpenAI
                sample = {
                    "messages": [
                        {"role": "system", "content": "Você é um assistente especializado em PMP."},
                        {"role": "user", "content": row['prompt']},
                        {"role": "assistant", "content": row['completion']}
                    ]
                }
                
                samples.append(sample)
    
        # Salvar no formato JSONL
        with open(output_path, 'w', encoding='utf-8') as jsonl_file:
            for sample in samples:
                jsonl_file.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"Convertidos {len(samples)} exemplos para {output_path}")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Erro ao converter CSV para fine-tuning: {e}")
        raise 