"""Persistência simples do EcoCity Guardian (SQLite por padrão ou MariaDB/XAMPP)."""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DB_PATH = PROJECT_DIR / "analytics" / "ecocity.db"
load_dotenv(BASE_DIR / ".env")
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").strip().lower()


def _connect():
    if DB_ENGINE == "mysql":
        try:
            import pymysql
            from pymysql.cursors import DictCursor
        except ImportError as exc:  # pragma: no cover - depends on chosen engine
            raise RuntimeError("Instale PyMySQL com: pip install pymysql") from exc
        return pymysql.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "ecocity_guardian"),
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
        )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _sql(statement: str) -> str:
    return statement.replace("?", "%s") if DB_ENGINE == "mysql" else statement


def _dict(row):
    return dict(row) if row is not None else None


def fetch_one(statement: str, params: tuple = ()) -> dict | None:
    conn = _connect()
    try:
        cursor = conn.cursor()
        cursor.execute(_sql(statement), params)
        return _dict(cursor.fetchone())
    finally:
        conn.close()


def fetch_all(statement: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    try:
        cursor = conn.cursor()
        cursor.execute(_sql(statement), params)
        return [_dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def execute(statement: str, params: tuple = ()) -> int:
    conn = _connect()
    try:
        cursor = conn.cursor()
        cursor.execute(_sql(statement), params)
        last_id = getattr(cursor, "lastrowid", 0) or 0
        conn.commit()
        return int(last_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 240_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = _password_hash(password, salt).split("$", 2)[2]
        return secrets.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False


def _create_user(nome: str, email: str, password: str, role: str) -> None:
    existing = fetch_one("SELECT id FROM users WHERE email = ?", (email.lower(),))
    if existing:
        return
    execute(
        "INSERT INTO users (nome, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (nome, email.lower(), _password_hash(password), role, datetime.now(timezone.utc).isoformat()),
    )


def init_db() -> None:
    if DB_ENGINE == "mysql":
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(120) NOT NULL,
                email VARCHAR(190) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                created_at VARCHAR(40) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS auth_tokens (
                token_hash CHAR(64) PRIMARY KEY,
                user_id INT NOT NULL,
                expires_at VARCHAR(40) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS relatos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cidadao_id INT NOT NULL,
                nome VARCHAR(120) NOT NULL,
                email VARCHAR(190) NOT NULL,
                localizacao VARCHAR(255) NOT NULL,
                descricao TEXT NOT NULL,
                imagem_path VARCHAR(500),
                categoria VARCHAR(120) NOT NULL,
                nivel_risco INT NOT NULL,
                prioridade_atendimento VARCHAR(40) NOT NULL,
                justificativa_ia TEXT NOT NULL,
                modelo_utilizado VARCHAR(120) NOT NULL,
                tempo_processamento_ms DOUBLE NOT NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'Recebido',
                timestamp VARCHAR(40) NOT NULL,
                updated_at VARCHAR(40) NOT NULL,
                FOREIGN KEY (cidadao_id) REFERENCES users(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS ocorrencias_analisadas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cidadao_id VARCHAR(120),
                categoria VARCHAR(120),
                nivel_risco INT,
                prioridade_atendimento VARCHAR(40),
                tempo_processamento_ms DOUBLE,
                timestamp VARCHAR(40)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        ]
    else:
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS auth_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS relatos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cidadao_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                email TEXT NOT NULL,
                localizacao TEXT NOT NULL,
                descricao TEXT NOT NULL,
                imagem_path TEXT,
                categoria TEXT NOT NULL,
                nivel_risco INTEGER NOT NULL,
                prioridade_atendimento TEXT NOT NULL,
                justificativa_ia TEXT NOT NULL,
                modelo_utilizado TEXT NOT NULL,
                tempo_processamento_ms REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Recebido',
                timestamp TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (cidadao_id) REFERENCES users(id)
            )""",
            """CREATE TABLE IF NOT EXISTS ocorrencias_analisadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cidadao_id TEXT,
                categoria TEXT,
                nivel_risco INTEGER,
                prioridade_atendimento TEXT,
                tempo_processamento_ms REAL,
                timestamp TEXT
            )""",
        ]

    conn = _connect()
    try:
        cursor = conn.cursor()
        for statement in statements:
            cursor.execute(statement)
        conn.commit()
    finally:
        conn.close()

    _create_user("Administrador EcoCity", "admin@ecocity.local", "Admin123!", "admin")
    _create_user("Cidadão Demonstração", "cidadao@ecocity.local", "Cidadao123!", "user")
    _seed_demo_reports()


def _seed_demo_reports() -> None:
    existing = fetch_one("SELECT COUNT(*) AS total FROM relatos")
    if existing and int(existing["total"]) > 0:
        return
    citizen = fetch_one("SELECT id, nome, email FROM users WHERE email = ?", ("cidadao@ecocity.local",))
    admin = fetch_one("SELECT id, nome, email FROM users WHERE email = ?", ("admin@ecocity.local",))
    if not citizen or not admin:
        return
    now = datetime.now(timezone.utc)
    samples = [
        (citizen, "Av. Ibirapuera, Moema", "Água acumulada na esquina após a chuva; a passagem de pedestres está parcialmente bloqueada.", "Risco de Enchente / Alagamento", 4, "ALTA", "Relato menciona acúmulo de água em via urbana; recomenda-se vistoria preventiva.", "Demonstração (dados fictícios)"),
        (citizen, "Alameda dos Anapurus, Moema", "Bueiro parece estar entupido por folhas e resíduos.", "Zeladoria / Bueiro Obstruído", 3, "MÉDIA", "Indício de obstrução de drenagem que pode agravar alagamentos.", "Demonstração (dados fictícios)"),
        (admin, "Av. dos Bandeirantes, São Paulo", "Ponto baixo da pista com enxurrada durante chuva forte.", "Risco de Enchente / Alagamento", 5, "ALTA - Emergência", "Menção a enxurrada em via de tráfego; exige avaliação prioritária.", "Demonstração (dados fictícios)"),
    ]
    for owner, location, description, category, risk, priority, reason, model in samples:
        timestamp = (now - timedelta(hours=len(samples))).isoformat()
        execute(
            """INSERT INTO relatos
            (cidadao_id, nome, email, localizacao, descricao, imagem_path, categoria, nivel_risco,
             prioridade_atendimento, justificativa_ia, modelo_utilizado, tempo_processamento_ms,
             status, timestamp, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (owner["id"], owner["nome"], owner["email"], location, description, None, category, risk,
             priority, reason, model, 0.0, "Em análise", timestamp, timestamp),
        )


def create_session(token: str, user_id: int, hours: int = 12) -> None:
    expiry = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    execute("INSERT INTO auth_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)", (token_hash, user_id, expiry))


def get_user_by_token(token: str) -> dict | None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = fetch_one(
        """SELECT users.id, users.nome, users.email, users.role, auth_tokens.expires_at
        FROM auth_tokens JOIN users ON users.id = auth_tokens.user_id WHERE auth_tokens.token_hash = ?""",
        (token_hash,),
    )
    if not row:
        return None
    try:
        expires = datetime.fromisoformat(row["expires_at"])
        if expires <= datetime.now(timezone.utc):
            execute("DELETE FROM auth_tokens WHERE token_hash = ?", (token_hash,))
            return None
    except ValueError:
        return None
    row.pop("expires_at", None)
    return row


def delete_session(token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    execute("DELETE FROM auth_tokens WHERE token_hash = ?", (token_hash,))


def get_user_by_email(email: str) -> dict | None:
    return fetch_one("SELECT id, nome, email, password_hash, role FROM users WHERE email = ?", (email.lower(),))


def create_report(data: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    report_id = execute(
        """INSERT INTO relatos
        (cidadao_id, nome, email, localizacao, descricao, imagem_path, categoria, nivel_risco,
         prioridade_atendimento, justificativa_ia, modelo_utilizado, tempo_processamento_ms,
         status, timestamp, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data["cidadao_id"], data["nome"], data["email"], data["localizacao"], data["descricao"],
         data.get("imagem_path"), data["categoria"], data["nivel_risco"], data["prioridade_atendimento"],
         data["justificativa_ia"], data["modelo_utilizado"], data["tempo_processamento_ms"],
         "Recebido", now, now),
    )
    return get_report(report_id)


def get_report(report_id: int) -> dict | None:
    return fetch_one("SELECT * FROM relatos WHERE id = ?", (report_id,))


def list_reports(user_id: int | None = None) -> list[dict]:
    if user_id is None:
        return fetch_all("SELECT * FROM relatos ORDER BY timestamp DESC")
    return fetch_all("SELECT * FROM relatos WHERE cidadao_id = ? ORDER BY timestamp DESC", (user_id,))


def update_report(report_id: int, fields: dict) -> dict | None:
    allowed = {"localizacao", "descricao", "status", "categoria", "nivel_risco", "prioridade_atendimento", "justificativa_ia", "modelo_utilizado", "tempo_processamento_ms"}
    fields = {key: value for key, value in fields.items() if key in allowed}
    if not fields:
        return get_report(report_id)
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    execute(f"UPDATE relatos SET {assignments} WHERE id = ?", (*fields.values(), report_id))
    return get_report(report_id)


def delete_report(report_id: int) -> bool:
    conn = _connect()
    try:
        cursor = conn.cursor()
        cursor.execute(_sql("DELETE FROM relatos WHERE id = ?"), (report_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def salvar_analise(cidadao_id, categoria, nivel_risco, prioridade, tempo_ms, timestamp):
    execute(
        """INSERT INTO ocorrencias_analisadas
        (cidadao_id, categoria, nivel_risco, prioridade_atendimento, tempo_processamento_ms, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (str(cidadao_id), categoria, nivel_risco, prioridade, tempo_ms, timestamp),
    )
