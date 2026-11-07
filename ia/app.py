import time
from database import init_db, salvar_analise
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="EcoCity Guardian - AI Module",
    description="API de triagem inteligente de ocorrências e análise de risco urbano.",
    version="1.0.0"
)


# Inicializa a base de dados ao subir a API
init_db()

# Modelo de entrada de dados do Frontend / IoT
class OcorrenciaRequest(BaseModel):
    cidadao_id: str
    descricao: str
    nivel_sensor_agua_cm: Optional[float] = 0.0
    imagem_base64: Optional[str] = None


# Modelo de resposta da IA
class AnáliseIAResponse(BaseModel):
    categoria: str
    nivel_risco: int  # 1 (Baixo) a 5 (Crítico)
    prioridade_atendimento: str
    tempo_processamento_ms: float
    timestamp: str


@app.get("/")
def read_root():
    return {"status": "online", "modulo": "IA & Analytics EcoCity"}


@app.post("/api/v1/analisar-ocorrencia", response_model=AnáliseIAResponse)
def analisar_ocorrencia(payload: OcorrenciaRequest):
    inicio = time.time()

    # 1. Simulação / Lógica da IA (Regra Cognitiva + Classificação)
    # Na fase final conectamos com o prompt do LLM / Visão Computacional
    descricao_lower = payload.descricao.lower()
    nivel_agua = payload.nivel_sensor_agua_cm

    if nivel_agua > 50 or "alagamento" in descricao_lower or "enchente" in descricao_lower:
        categoria = "Risco de Enchente / Alagamento"
        risco = 5
        prioridade = "ALTA - Emergência"
    elif "lixo" in descricao_lower or "bueiro" in descricao_lower:
        categoria = "Zeladoria / Bueiro Obstruído"
        risco = 3
        prioridade = "MÉDIA"
    else:
        categoria = "Zeladoria Geral"
        risco = 1
        prioridade = "BAIXA"

    tempo_execucao = round((time.time() - inicio) * 1000, 2)

    # Grava no Big Data (analytics/ecocity.db)
    salvar_analise(
        payload.cidadao_id,
        categoria,
        risco,
        prioridade,
        tempo_execucao,
        datetime.now().isoformat()
    )

    return AnáliseIAResponse(
        categoria=categoria,
        nivel_risco=risco,
        prioridade_atendimento=prioridade,
        tempo_processamento_ms=tempo_execucao,
        timestamp=datetime.now().isoformat()
    )