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

# Configuração do Ollama Local
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")  # Pode ser llama3.2, qwen2.5, phi3, etc.


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
Você é o motor cognitivo de IA do sistema EcoCity Guardian (CitizenTech).
Sua missão é analisar o relato de um cidadão e os dados de sensores urbanos para classificar a gravidade da ocorrência.

Relato do Cidadão: "{descricao}"
Nível do Sensor de Água: {nivel_agua} cm

Responda APENAS um objeto JSON válido exatamente com esta estrutura:
{{
  "categoria": "Risco de Enchente / Alagamento" | "Zeladoria / Bueiro Obstruído" | "Deslizamento / Encosta" | "Iluminação Pública" | "Zeladoria Geral",
  "nivel_risco": 1 a 5 (inteiro),
  "prioridade_atendimento": "BAIXA" | "MÉDIA" | "ALTA" | "ALTA - Emergência",
  "justificativa_ia": "Explicação técnica sucinta da decisão"
}}
"""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=6)
        if response.status_code == 200:
            data = response.json()
            return json.loads(data.get("response", "{}"))
    except Exception:
        return None
    return None


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
        # Timeout de 30 segundos para dar tempo de inferência do modelo local
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            raw_response = data.get("response", "{}")
            return json.loads(raw_response)
        else:
            print(f"⚠️ [Ollama Error Status] Code: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ [Ollama Exception] {type(e).__name__}: {e}")
        return None
    return None


@app.post("/api/v1/analisar-ocorrencia", response_model=AnáliseIAResponse)
def analisar_ocorrencia(payload: OcorrenciaRequest):
    inicio = time.time()

    # 1. Tenta processar via LLM Local (Ollama)
    resultado_ia = processar_com_llm_local(payload.descricao, payload.nivel_sensor_agua_cm)
    modelo_usado = f"LLM Local ({OLLAMA_MODEL})"

    # 2. Se o Ollama estiver offline na máquina do avaliador, entra o fallback
    if not resultado_ia or "categoria" not in resultado_ia:
        resultado_ia = processar_algoritmo_heuristico(payload.descricao, payload.nivel_sensor_agua_cm)
        modelo_usado = "Motor Heurístico (Fallback)"

    tempo_execucao = round((time.time() - inicio) * 1000, 2)

    # 3. Persistência no Big Data
    salvar_analise(
        payload.cidadao_id,
        resultado_ia["categoria"],
        resultado_ia["nivel_risco"],
        resultado_ia["prioridade_atendimento"],
        tempo_execucao,
        datetime.now().isoformat()
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