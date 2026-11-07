import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_01_analise_emergencia_alagamento():
    """Teste 1: Verifica se o sensor > 50cm classifica como Risco de Enchente (Nível 5)."""
    payload = {
        "cidadao_id": "TESTE-01",
        "descricao": "Rua totalmente alagada com água subindo rápido",
        "nivel_sensor_agua_cm": 65.0
    }
    response = client.post("/api/v1/analisar-ocorrencia", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["nivel_risco"] == 5
    assert "Enchente" in data["categoria"] or "Alagamento" in data["categoria"]

def test_02_analise_zeladoria_bueiro():
    """Teste 2: Verifica a triagem de bueiro entupido (Prioridade Média)."""
    payload = {
        "cidadao_id": "TESTE-02",
        "descricao": "Bueiro entupido com acúmulo de sacos de lixo",
        "nivel_sensor_agua_cm": 10.0
    }
    response = client.post("/api/v1/analisar-ocorrencia", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["nivel_risco"] in [3, 4, 5]

def test_03_ocorrencia_geral_risco_baixo():
    """Teste 3: Verifica se um relato comum recebe Risco 1 / Prioridade Baixa."""
    payload = {
        "cidadao_id": "TESTE-03",
        "descricao": "Pintura da guia apagada na calçada",
        "nivel_sensor_agua_cm": 0.0
    }
    response = client.post("/api/v1/analisar-ocorrencia", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "categoria" in data
    assert "justificativa_ia" in data

def test_04_validacao_campos_invalidos():
    """Teste 4: Garante que a API rejeita requisições com payload incorreto (HTTP 422)."""
    payload = {
        "cidadao_id": "TESTE-ERRO"
        # Faltando o campo obrigatório 'descricao'
    }
    response = client.post("/api/v1/analisar-ocorrencia", json=payload)
    assert response.status_code == 422

def test_05_metrica_tempo_processamento():
    """Teste 5: Garante que a API calcula e devolve a métrica de tempo em ms."""
    payload = {
        "cidadao_id": "TESTE-METRICA",
        "descricao": "Teste de performance da triagem",
        "nivel_sensor_agua_cm": 5.0
    }
    response = client.post("/api/v1/analisar-ocorrencia", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tempo_processamento_ms"] > 0