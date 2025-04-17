#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cliente API para o OpenAI.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class OpenAIAPI:
    """Cliente para a API da OpenAI."""
    
    def __init__(self, api_key: str):
        """Inicializa o cliente com a chave da API."""
        self.api_key = api_key
        logger.info("Cliente OpenAI API inicializado")
        
    def list_fine_tuned_models(self) -> List[Dict[str, Any]]:
        """
        Lista os modelos fine-tuned disponíveis.
        
        Nota: Esta é uma implementação de simulação para desenvolvimento.
        Em produção, deve usar a API real da OpenAI.
        """
        logger.info("Listando modelos fine-tuned")
        
        # Simulação de modelos para desenvolvimento
        models = [
            {
                "id": "ft:gpt-3.5-turbo-0125:personal::BGt3nwXI",
                "object": "model",
                "created": 1720152360,
                "owned_by": "user-abc123"
            },
            {
                "id": "ft:gpt-3.5-turbo:pmp-questions:7FbShAzl",
                "object": "model",
                "created": 1719958360,
                "owned_by": "user-abc123"
            },
            {
                "id": "ft:gpt-3.5-turbo:pmp-answers:9Db4hGsp",
                "object": "model",
                "created": 1719858360,
                "owned_by": "user-abc123"
            },
            {
                "id": "ft:gpt-3.5-turbo:pmp-distractors:3KcRj7pQ",
                "object": "model",
                "created": 1719758360,
                "owned_by": "user-abc123"
            }
        ]
        
        # Verificar IDs de jobs nos logs
        job_ids = [
            "ftjob-VaG7uCUOkiSPdN1j7w9u5OTu",
            "ftjob-H3so8ec6ocGImouoAlSpLGFk"
        ]
        
        for job_id in job_ids:
            job_details = self.get_fine_tuning_job(job_id)
            if job_details and job_details.get("fine_tuned_model"):
                model_id = job_details.get("fine_tuned_model")
                models.append({
                    "id": model_id,
                    "object": "model",
                    "created": int(datetime.datetime.now().timestamp()),
                    "owned_by": "user-abc123"
                })
        
        logger.info(f"Encontrados {len(models)} modelos fine-tuned")
        return models
    
    def get_fine_tuning_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes de um job de fine-tuning.
        
        Nota: Esta é uma implementação de simulação para desenvolvimento.
        Em produção, deve usar a API real da OpenAI.
        """
        logger.info(f"Buscando detalhes do job: {job_id}")
        
        # Verificar se o job_id contém o prefixo ftjob-
        if not job_id.startswith("ftjob-") and job_id != "12345" and job_id != "67890" and job_id != "54321":
            logger.warning(f"ID de job inválido: {job_id}")
            return None
            
        # Simular diferentes estados de job para diferentes IDs
        if job_id == "12345" or job_id == "ftjob-VaG7uCUOkiSPdN1j7w9u5OTu":
            job_details = {
                "id": job_id,
                "object": "fine_tuning.job",
                "created_at": int(datetime.datetime.now().timestamp()) - 86400,  # 1 dia atrás
                "finished_at": int(datetime.datetime.now().timestamp()) - 3600,  # 1 hora atrás
                "status": "succeeded",
                "fine_tuned_model": "ft:gpt-3.5-turbo:pmp-questions:12345",
                "organization_id": "org-abc123",
                "result_files": ["file-abc123"],
                "trained_tokens": 123456,
                "hyperparameters": {
                    "n_epochs": 3
                }
            }
        elif job_id == "67890" or job_id == "ftjob-H3so8ec6ocGImouoAlSpLGFk":
            job_details = {
                "id": job_id,
                "object": "fine_tuning.job",
                "created_at": int(datetime.datetime.now().timestamp()) - 43200,  # 12 horas atrás
                "finished_at": int(datetime.datetime.now().timestamp()) - 1800,  # 30 minutos atrás
                "status": "succeeded",
                "fine_tuned_model": "ft:gpt-3.5-turbo:pmp-answers:67890",
                "organization_id": "org-abc123",
                "result_files": ["file-def456"],
                "trained_tokens": 87654,
                "hyperparameters": {
                    "n_epochs": 4
                }
            }
        elif job_id == "54321":
            job_details = {
                "id": job_id,
                "object": "fine_tuning.job",
                "created_at": int(datetime.datetime.now().timestamp()) - 21600,  # 6 horas atrás
                "finished_at": None,
                "status": "running",
                "fine_tuned_model": None,
                "organization_id": "org-abc123",
                "result_files": [],
                "trained_tokens": 0,
                "hyperparameters": {
                    "n_epochs": 3
                }
            }
        else:
            # Job ID desconhecido
            job_details = {
                "id": job_id,
                "object": "fine_tuning.job",
                "created_at": int(datetime.datetime.now().timestamp()) - 3600,  # 1 hora atrás
                "finished_at": int(datetime.datetime.now().timestamp()) - 1800,  # 30 minutos atrás
                "status": "succeeded",
                "fine_tuned_model": f"ft:gpt-3.5-turbo:personal::{job_id[-8:]}",
                "organization_id": "org-abc123",
                "result_files": ["file-xyz789"],
                "trained_tokens": 50000,
                "hyperparameters": {
                    "n_epochs": 3
                }
            }
        
        logger.info(f"Detalhes do job: {job_details}")
        return job_details
    
    def get_model_details(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes de um modelo.
        
        Nota: Esta é uma implementação de simulação para desenvolvimento.
        Em produção, deve usar a API real da OpenAI.
        """
        logger.info(f"Buscando detalhes do modelo: {model_id}")
        
        # Verificar se o model_id contém o prefixo ft:
        if not model_id.startswith("ft:") and not model_id.startswith("default_"):
            logger.warning(f"ID de modelo inválido: {model_id}")
            return None
            
        # Simular diferentes tipos de modelos
        if "questions" in model_id.lower():
            model_details = {
                "id": model_id,
                "object": "model",
                "created": int(datetime.datetime.now().timestamp()) - 86400,  # 1 dia atrás
                "owned_by": "user-abc123",
                "permission": [],
                "root": "gpt-3.5-turbo-0125",
                "parent": None
            }
        elif "answers" in model_id.lower():
            model_details = {
                "id": model_id,
                "object": "model",
                "created": int(datetime.datetime.now().timestamp()) - 43200,  # 12 horas atrás
                "owned_by": "user-abc123",
                "permission": [],
                "root": "gpt-3.5-turbo-0125",
                "parent": None
            }
        elif "distractors" in model_id.lower() or "wrong" in model_id.lower():
            model_details = {
                "id": model_id,
                "object": "model",
                "created": int(datetime.datetime.now().timestamp()) - 21600,  # 6 horas atrás
                "owned_by": "user-abc123",
                "permission": [],
                "root": "gpt-3.5-turbo-0125",
                "parent": None
            }
        else:
            # Modelo genérico
            model_details = {
                "id": model_id,
                "object": "model",
                "created": int(datetime.datetime.now().timestamp()) - 3600,  # 1 hora atrás
                "owned_by": "user-abc123",
                "permission": [],
                "root": "gpt-3.5-turbo-0125",
                "parent": None
            }
        
        logger.info(f"Detalhes do modelo: {model_details}")
        return model_details
    
    def create_completion(self, model: str, prompt: str, max_tokens: int = 500) -> Dict[str, Any]:
        """
        Cria uma completion usando o modelo especificado.
        
        Nota: Esta é uma implementação de simulação para desenvolvimento.
        Em produção, deve usar a API real da OpenAI.
        """
        logger.info(f"Criando completion com o modelo: {model}")
        
        # Simulação de resposta
        completion = {
            "id": f"cmpl-{os.urandom(4).hex()}",
            "object": "text_completion",
            "created": int(datetime.datetime.now().timestamp()),
            "model": model,
            "choices": [
                {
                    "text": f"Resposta simulada para: {prompt[:30]}...",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 20,
                "total_tokens": len(prompt.split()) + 20
            }
        }
        
        return completion
    
    def create_chat_completion(self, model: str, messages: List[Dict[str, str]], max_tokens: int = 500) -> Dict[str, Any]:
        """
        Cria uma chat completion usando o modelo especificado.
        
        Nota: Esta é uma implementação de simulação para desenvolvimento.
        Em produção, deve usar a API real da OpenAI.
        """
        logger.info(f"Criando chat completion com o modelo: {model}")
        
        # Extrair a última mensagem para usar como base para a resposta simulada
        last_message = messages[-1]["content"] if messages else "Sem mensagem"
        
        # Simulação de resposta
        completion = {
            "id": f"chatcmpl-{os.urandom(4).hex()}",
            "object": "chat.completion",
            "created": int(datetime.datetime.now().timestamp()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Resposta simulada para: {last_message[:30]}..."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(msg["content"].split()) for msg in messages),
                "completion_tokens": 20,
                "total_tokens": sum(len(msg["content"].split()) for msg in messages) + 20
            }
        }
        
        return completion
    
    def create_fine_tuning_job(self, training_file: str, validation_file: str = None, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """
        Cria um job de fine-tuning.
        
        Nota: Esta é uma implementação de simulação para desenvolvimento.
        Em produção, deve usar a API real da OpenAI.
        """
        logger.info(f"Criando job de fine-tuning para o arquivo: {training_file}")
        
        # Simular criação de job
        job_id = f"ftjob-{os.urandom(4).hex()}"
        
        job = {
            "id": job_id,
            "object": "fine_tuning.job",
            "created_at": int(datetime.datetime.now().timestamp()),
            "finished_at": None,
            "status": "validating_files",
            "fine_tuned_model": None,
            "organization_id": "org-abc123",
            "result_files": [],
            "trained_tokens": 0,
            "hyperparameters": {
                "n_epochs": 3
            }
        }
        
        logger.info(f"Job de fine-tuning criado: {job_id}")
        return job 