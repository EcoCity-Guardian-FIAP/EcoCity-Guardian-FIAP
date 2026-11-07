import sqlite3
import os

# Define a pasta analytics para guardar o ficheiro do banco de dados
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'analytics', 'ecocity.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias_analisadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cidadao_id TEXT,
            categoria TEXT,
            nivel_risco INTEGER,
            prioridade_atendimento TEXT,
            tempo_processamento_ms REAL,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_analise(cidadao_id, categoria, nivel_risco, prioridade, tempo_ms, timestamp):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ocorrencias_analisadas 
        (cidadao_id, categoria, nivel_risco, prioridade_atendimento, tempo_processamento_ms, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (cidadao_id, categoria, nivel_risco, prioridade, tempo_ms, timestamp))
    conn.commit()
    conn.close()