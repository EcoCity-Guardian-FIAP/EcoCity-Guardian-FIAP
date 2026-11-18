CREATE DATABASE IF NOT EXISTS ecocity_guardian
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecocity_guardian;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL,
  created_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS auth_tokens (
  token_hash CHAR(64) PRIMARY KEY,
  user_id INT NOT NULL,
  expires_at VARCHAR(40) NOT NULL,
  CONSTRAINT fk_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS relatos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cidadao_id INT NOT NULL,
  nome VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL,
  localizacao VARCHAR(255) NOT NULL,
  descricao TEXT NOT NULL,
  imagem_path VARCHAR(500) NULL,
  categoria VARCHAR(120) NOT NULL,
  nivel_risco INT NOT NULL,
  prioridade_atendimento VARCHAR(40) NOT NULL,
  justificativa_ia TEXT NOT NULL,
  modelo_utilizado VARCHAR(120) NOT NULL,
  tempo_processamento_ms DOUBLE NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'Recebido',
  timestamp VARCHAR(40) NOT NULL,
  updated_at VARCHAR(40) NOT NULL,
  CONSTRAINT fk_relatos_user FOREIGN KEY (cidadao_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ocorrencias_analisadas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cidadao_id VARCHAR(120),
  categoria VARCHAR(120),
  nivel_risco INT,
  prioridade_atendimento VARCHAR(40),
  tempo_processamento_ms DOUBLE,
  timestamp VARCHAR(40)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
