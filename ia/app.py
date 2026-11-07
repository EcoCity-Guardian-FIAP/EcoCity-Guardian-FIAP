import time
import os
import json
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from database import init_db, salvar_analise

app = FastAPI(
    title="EcoCity Guardian - Local LLM Engine",
    description="Motor Cognitivo de Triagem com LLM Local (Ollama) e Fallback Heurístico.",
    version="2.0.0"
)

init_db()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


class OcorrenciaRequest(BaseModel):
    cidadao_id: str
    descricao: str
    nivel_sensor_agua_cm: Optional[float] = 0.0
    imagem_base64: Optional[str] = None


class AnáliseIAResponse(BaseModel):
    categoria: str
    nivel_risco: int
    prioridade_atendimento: str
    justificativa_ia: str
    modelo_utilizado: str
    tempo_processamento_ms: float
    timestamp: str


def processar_com_llm_local(descricao: str, nivel_agua: float) -> Optional[dict]:
    """Processa o relato chamando o LLM local via Ollama com saída JSON estrita."""
    prompt = f"""
Você é o motor cognitivo do sistema EcoCity Guardian.
Analise o relato do cidadão e a telemetria do sensor para classificar a ocorrência.

Relato: "{descricao}"
Nível do Sensor de Água: {nivel_agua} cm

Responda APENAS um objeto JSON com as chaves:
- "categoria": Escolha uma entre ("Risco de Enchente / Alagamento", "Zeladoria / Bueiro Obstruído", "Deslizamento / Encosta", "Iluminação Pública", "Zeladoria Geral")
- "nivel_risco": Número inteiro de 1 a 5
- "prioridade_atendimento": "BAIXA", "MÉDIA", "ALTA" ou "ALTA - Emergência"
- "justificativa_ia": Explicação sucinta do motivo da classificação
"""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return json.loads(data.get("response", "{}"))
    except Exception as e:
        print(f"⚠️ [Ollama Fallback Ativado] motivo: {e}")
        return None
    return None


def processar_algoritmo_heuristico(descricao: str, nivel_agua: float) -> dict:
    """Motor Heurístico de Contingência (Fallback quando o Ollama estiver offline)."""
    desc_lower = descricao.lower()
    pesos_criticos = ["alagamento", "enchente", "transbordou", "enxurrada", "socorro", "ilhado", "deslizamento"]
    pesos_medios = ["bueiro", "lixo", "entupido", "arvore caiu", "cratera", "buraco"]

    score_critico = sum(2 for p in pesos_criticos if p in desc_lower)
    score_medio = sum(1 for p in pesos_medios if p in desc_lower)

    if nivel_agua > 50 or score_critico >= 2:
        return {
            "categoria": "Risco de Enchente / Alagamento",
            "nivel_risco": 5,
            "prioridade_atendimento": "ALTA - Emergência",
            "justificativa_ia": f"Sensor superou limite crítico ({nivel_agua}cm) e/ou padrão de texto indica emergência severa."
        }
    elif score_critico == 1 or score_medio >= 2:
        return {
            "categoria": "Risco de Alagamento Moderado",
            "nivel_risco": 4,
            "prioridade_atendimento": "ALTA",
            "justificativa_ia": "Detecção de padrões de risco moderado no relato do cidadão."
        }
    elif score_medio == 1:
        return {
            "categoria": "Zeladoria / Bueiro Obstruído",
            "nivel_risco": 3,
            "prioridade_atendimento": "MÉDIA",
            "justificativa_ia": "Necessidade de manutenção preventiva em infraestrutura urbana."
        }
    else:
        return {
            "categoria": "Zeladoria Geral",
            "nivel_risco": 1,
            "prioridade_atendimento": "BAIXA",
            "justificativa_ia": "Ocorrência padrão sem risco iminente detectado."
        }


@app.post("/api/v1/analisar-ocorrencia", response_model=AnáliseIAResponse)
def analisar_ocorrencia(payload: OcorrenciaRequest):
    inicio = time.time()

    resultado_ia = processar_com_llm_local(payload.descricao, payload.nivel_sensor_agua_cm)
    modelo_usado = f"LLM Local ({OLLAMA_MODEL})"

    if not resultado_ia or "categoria" not in resultado_ia:
        resultado_ia = processar_algoritmo_heuristico(payload.descricao, payload.nivel_sensor_agua_cm)
        modelo_usado = "Motor Heurístico (Fallback)"

    tempo_execucao = round((time.time() - inicio) * 1000, 2)

    salvar_analise(
        payload.cidadao_id,
        resultado_ia["categoria"],
        resultado_ia["nivel_risco"],
        resultado_ia["prioridade_atendimento"],
        tempo_execucao,
        datetime.now().isoformat()gi
    )

    return AnáliseIAResponse(
        categoria=resultado_ia["categoria"],
        nivel_risco=resultado_ia["nivel_risco"],
        prioridade_atendimento=resultado_ia["prioridade_atendimento"],
        justificativa_ia=resultado_ia["justificativa_ia"],
        modelo_utilizado=modelo_usado,
        tempo_processamento_ms=tempo_execucao,
        timestamp=datetime.now().isoformat()
    )