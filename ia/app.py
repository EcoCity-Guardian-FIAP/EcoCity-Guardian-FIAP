"""API do EcoCity Guardian: autenticação demonstrativa, relatos e triagem por IA."""
from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import (
    create_report,
    create_session,
    delete_report,
    delete_session,
    get_report,
    get_user_by_email,
    get_user_by_token,
    init_db,
    list_reports,
    salvar_analise,
    update_report,
    verify_password,
)

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="EcoCity Guardian API",
    description="API demonstrativa para autenticação, relatos colaborativos e triagem de ocorrências.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500", "http://localhost:5500",
        "http://127.0.0.1:5501", "http://localhost:5501",
        "http://127.0.0.1:8000", "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
security = HTTPBearer(auto_error=False)
init_db()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SENSOR_API_KEY = os.getenv("SENSOR_API_KEY", "ecocity-iot-demo-key")
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class LoginRequest(BaseModel):
    email: str
    password: str


class RelatoUpdate(BaseModel):
    localizacao: Optional[str] = Field(default=None, max_length=255)
    descricao: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = None


class TelemetryRequest(BaseModel):
    sensor_id: str = Field(min_length=2, max_length=100)
    localizacao: str = Field(default="Local do sensor", min_length=3, max_length=255)
    descricao: str = Field(default="Alerta automático: nível de água elevado detectado pelo sensor IoT.", max_length=2000)
    nivel_sensor_agua_cm: float = Field(ge=0, le=500)


def public_user(user: dict) -> dict:
    return {"id": user["id"], "nome": user["nome"], "email": user["email"], "role": user["role"]}


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre novamente.")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Esta área é exclusiva para administradores.")
    return user


def processar_com_llm_local(descricao: str, nivel_agua: float) -> dict | None:
    prompt = f"""Você é o motor cognitivo do sistema EcoCity Guardian. Classifique o relato e a telemetria.
Relato: {descricao!r}
Nível do sensor de água: {nivel_agua} cm
Responda somente JSON com: categoria (Risco de Enchente / Alagamento, Zeladoria / Bueiro Obstruído, Deslizamento / Encosta, Iluminação Pública ou Zeladoria Geral), nivel_risco (inteiro 1 a 5), prioridade_atendimento (BAIXA, MÉDIA, ALTA ou ALTA - Emergência), justificativa_ia (frase curta)."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False},
            timeout=4,
        )
        response.raise_for_status()
        result = json.loads(response.json().get("response", "{}"))
        if all(key in result for key in ("categoria", "nivel_risco", "prioridade_atendimento", "justificativa_ia")):
            result["nivel_risco"] = max(1, min(5, int(result["nivel_risco"])))
            return result
    except Exception as exc:
        print(f"[EcoCity] Ollama indisponível; usando triagem heurística: {exc}")
    return None


def processar_algoritmo_heuristico(descricao: str, nivel_agua: float) -> dict:
    texto = descricao.casefold()
    criticos = ["alagamento", "enchente", "transbordou", "enxurrada", "socorro", "ilhado", "deslizamento", "água invad"]
    medios = ["bueiro", "lixo", "entupido", "árvore caiu", "arvore caiu", "cratera", "buraco", "drenagem"]
    score_critico = sum(2 for termo in criticos if termo in texto)
    score_medio = sum(1 for termo in medios if termo in texto)
    if nivel_agua >= 50 or score_critico >= 2:
        return {"categoria": "Risco de Enchente / Alagamento", "nivel_risco": 5,
                "prioridade_atendimento": "ALTA - Emergência",
                "justificativa_ia": "Foram identificados sinais de possível emergência ou nível de água crítico. Encaminhe para vistoria prioritária."}
    if score_critico or score_medio >= 2:
        return {"categoria": "Risco de Enchente / Alagamento", "nivel_risco": 4,
                "prioridade_atendimento": "ALTA",
                "justificativa_ia": "O relato contém indícios relevantes de risco urbano ou de drenagem e requer avaliação rápida."}
    if score_medio:
        return {"categoria": "Zeladoria / Bueiro Obstruído", "nivel_risco": 3,
                "prioridade_atendimento": "MÉDIA",
                "justificativa_ia": "O relato sugere manutenção preventiva em infraestrutura urbana."}
    return {"categoria": "Zeladoria Geral", "nivel_risco": 1,
            "prioridade_atendimento": "BAIXA",
            "justificativa_ia": "Não foram encontrados termos indicativos de risco iminente; a ocorrência foi classificada para acompanhamento."}


def serialize_report(report: dict) -> dict:
    report["imagem_url"] = f"/uploads/{Path(report['imagem_path']).name}" if report.get("imagem_path") else None
    report["usuario"] = {"id": report.pop("cidadao_id"), "nome": report.pop("nome"), "email": report.pop("email")}
    return report


@app.get("/health")
def health():
    return {"status": "ok", "servico": "EcoCity Guardian API"}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest):
    user = get_user_by_email(payload.email.strip())
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    token = secrets.token_urlsafe(36)
    create_session(token, user["id"])
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


@app.get("/api/v1/auth/me")
def who_am_i(user: dict = Depends(current_user)):
    return public_user(user)


@app.post("/api/v1/auth/logout")
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(security), user: dict = Depends(current_user)):
    delete_session(credentials.credentials)
    return {"message": "Sessão encerrada."}


@app.post("/api/v1/analisar-ocorrencia")
async def analisar_ocorrencia(
    localizacao: str = Form(..., min_length=3, max_length=255),
    descricao: str = Form(..., min_length=10, max_length=2000),
    nivel_sensor_agua_cm: float = Form(0),
    imagem: UploadFile | None = File(default=None),
    user: dict = Depends(current_user),
):
    inicio = time.perf_counter()
    imagem_path = None
    if imagem and imagem.filename:
        extension = ALLOWED_IMAGE_TYPES.get(imagem.content_type or "")
        if not extension:
            raise HTTPException(status_code=400, detail="Envie uma imagem JPG, PNG ou WEBP.")
        content = await imagem.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="A imagem deve ter no máximo 5 MB.")
        filename = f"{uuid.uuid4().hex}{extension}"
        (UPLOAD_DIR / filename).write_bytes(content)
        imagem_path = filename

    triagem = processar_com_llm_local(descricao, nivel_sensor_agua_cm)
    modelo = f"LLM local ({OLLAMA_MODEL})" if triagem else "Motor heurístico (fallback)"
    if not triagem:
        triagem = processar_algoritmo_heuristico(descricao, nivel_sensor_agua_cm)
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    timestamp = datetime.now(timezone.utc).isoformat()

    report = create_report({
        "cidadao_id": user["id"], "nome": user["nome"], "email": user["email"],
        "localizacao": localizacao.strip(), "descricao": descricao.strip(), "imagem_path": imagem_path,
        "categoria": triagem["categoria"], "nivel_risco": triagem["nivel_risco"],
        "prioridade_atendimento": triagem["prioridade_atendimento"],
        "justificativa_ia": triagem["justificativa_ia"], "modelo_utilizado": modelo,
        "tempo_processamento_ms": tempo_ms,
    })
    salvar_analise(user["id"], triagem["categoria"], triagem["nivel_risco"], triagem["prioridade_atendimento"], tempo_ms, timestamp)
    return {
        "message": "Relato enviado e classificado com sucesso.",
        "relato": serialize_report(report),
        "triagem": {
            **triagem,
            "modelo_utilizado": modelo,
            "tempo_processamento_ms": tempo_ms,
            "timestamp": timestamp,
        },
    }


@app.post("/api/v1/telemetria")
def receber_telemetria(payload: TelemetryRequest, x_sensor_token: str = Header(default="")):
    """Entrada simples e autenticada para sensores ESP32; cria relato visível no Painel do Gestor."""
    if not secrets.compare_digest(x_sensor_token, SENSOR_API_KEY):
        raise HTTPException(status_code=401, detail="Chave do sensor inválida.")
    system_user = get_user_by_email("admin@ecocity.local")
    if not system_user:
        raise HTTPException(status_code=500, detail="Conta interna do sistema não foi inicializada.")

    inicio = time.perf_counter()
    triagem = processar_com_llm_local(payload.descricao, payload.nivel_sensor_agua_cm)
    if triagem:
        modelo = f"LLM local ({OLLAMA_MODEL})"
    else:
        triagem = processar_algoritmo_heuristico(payload.descricao, payload.nivel_sensor_agua_cm)
        modelo = "Motor heurístico (fallback)"
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    timestamp = datetime.now(timezone.utc).isoformat()
    report = create_report({
        "cidadao_id": system_user["id"],
        "nome": f"Sensor IoT · {payload.sensor_id}",
        "email": f"iot+{payload.sensor_id}@ecocity.local",
        "localizacao": payload.localizacao,
        "descricao": payload.descricao,
        "imagem_path": None,
        "categoria": triagem["categoria"],
        "nivel_risco": triagem["nivel_risco"],
        "prioridade_atendimento": triagem["prioridade_atendimento"],
        "justificativa_ia": triagem["justificativa_ia"],
        "modelo_utilizado": modelo,
        "tempo_processamento_ms": tempo_ms,
    })
    salvar_analise(payload.sensor_id, triagem["categoria"], triagem["nivel_risco"], triagem["prioridade_atendimento"], tempo_ms, timestamp)
    return {
        "message": "Telemetria recebida e convertida em ocorrência.",
        "relato": serialize_report(report),
        "triagem": {**triagem, "modelo_utilizado": modelo, "tempo_processamento_ms": tempo_ms, "timestamp": timestamp},
    }


@app.get("/api/v1/relatos")
def get_all_reports(user: dict = Depends(admin_user)):
    return [serialize_report(item) for item in list_reports()]


@app.get("/api/v1/relatos/meus")
def get_my_reports(user: dict = Depends(current_user)):
    return [serialize_report(item) for item in list_reports(user["id"])]


@app.patch("/api/v1/relatos/{report_id}")
def edit_report(report_id: int, payload: RelatoUpdate, user: dict = Depends(admin_user)):
    fields = payload.model_dump(exclude_unset=True)
    if "status" in fields and fields["status"] not in {"Recebido", "Em análise", "Em atendimento", "Resolvido", "Arquivado"}:
        raise HTTPException(status_code=400, detail="Status inválido.")
    if "descricao" in fields:
        inicio = time.perf_counter()
        triagem = processar_com_llm_local(fields["descricao"], 0)
        if triagem:
            modelo = f"LLM local ({OLLAMA_MODEL})"
        else:
            triagem = processar_algoritmo_heuristico(fields["descricao"], 0)
            modelo = "Motor heurístico (fallback)"
        fields.update(triagem)
        fields["modelo_utilizado"] = modelo
        fields["tempo_processamento_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
    report = update_report(report_id, fields)
    if not report:
        raise HTTPException(status_code=404, detail="Relato não encontrado.")
    return serialize_report(report)


@app.delete("/api/v1/relatos/{report_id}")
def remove_report(report_id: int, user: dict = Depends(admin_user)):
    report = get_report(report_id)
    if not report or not delete_report(report_id):
        raise HTTPException(status_code=404, detail="Relato não encontrado.")
    if report.get("imagem_path"):
        image_file = UPLOAD_DIR / Path(report["imagem_path"]).name
        try:
            image_file.unlink(missing_ok=True)
        except OSError:
            pass
    return {"message": "Relato excluído."}


@app.get("/api/v1/alertas")
def get_alerts():
    return {
        "origem": "Dados simulados para demonstração",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "status_cidade": "Monitoramento demonstrativo",
        "alertas": [
            {"id": "A-001", "titulo": "Atenção: acúmulo de água", "local": "Av. Ibirapuera, Moema", "lat": -23.6015, "lng": -46.6652, "nivel": "alto", "agua_cm": 42, "descricao": "Ponto de atenção simulado após chuva intensa."},
            {"id": "A-002", "titulo": "Drenagem em observação", "local": "Alameda dos Anapurus, Moema", "lat": -23.6090, "lng": -46.6658, "nivel": "medio", "agua_cm": 24, "descricao": "Possível obstrução de bueiro; vistoria preventiva simulada."},
            {"id": "A-003", "titulo": "Condição estável", "local": "Praça Nossa Senhora Aparecida, Moema", "lat": -23.6035, "lng": -46.6623, "nivel": "baixo", "agua_cm": 6, "descricao": "Sem indício de alagamento no cenário demonstrativo."},
            {"id": "A-004", "titulo": "Atenção: via com histórico de enxurrada", "local": "Av. dos Bandeirantes, São Paulo", "lat": -23.6184, "lng": -46.6650, "nivel": "alto", "agua_cm": 48, "descricao": "Alerta de exemplo; a localização e o nível não vêm de sensor real."},
            {"id": "A-005", "titulo": "Drenagem em observação", "local": "Av. Juriti, Moema", "lat": -23.6020, "lng": -46.6725, "nivel": "medio", "agua_cm": 19, "descricao": "Indicador fictício para ilustrar o mapa de alertas."},
        ],
    }


@app.exception_handler(Exception)
async def unexpected_error_handler(request, exc):
    print(f"[EcoCity API] Erro inesperado: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Erro interno na API. Consulte o terminal do backend."})
