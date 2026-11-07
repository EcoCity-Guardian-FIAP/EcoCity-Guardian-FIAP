import streamlit as st
import pandas as pd
import sqlite3
import os
import random
from datetime import datetime, timedelta

# -------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------------------------------------------
st.set_page_config(
    page_title="EcoCity Guardian | Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# ESTILIZAÇÃO CUSTOMIZADA (CSS HIGH-TECH)
# -------------------------------------------------------------
st.markdown("""
<style>
    /* Estilo Global */
    .main {
        background-color: #0b0f19;
    }

    /* Header principal */
    .header-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 22px 28px;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    .header-title {
        color: #38bdf8;
        font-size: 2.1rem;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .header-sub {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 6px;
    }

    /* Cards de Métricas */
    .kpi-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    .kpi-title {
        color: #94a3b8;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 4px;
        margin-bottom: 2px;
    }

    /* Cores das Métricas */
    .val-blue { color: #38bdf8; }
    .val-green { color: #4ade80; }
    .val-amber { color: #fbbf24; }
    .val-red { color: #f87171; }

    /* Badge de status */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-critico { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }
    .badge-medio { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }
    .badge-baixo { background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# CONEXÃO BANCO DE DADOS & FUNÇÕES
# -------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), 'ecocity.db')


def carregar_dados():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM ocorrencias_analisadas", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def gerar_dados_mock():
    """Gera registros fictícios para facilitar prints do PDF e Pitch"""
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

    categorias = [
        ("Risco de Enchente / Alagamento", 5, "ALTA - Emergência"),
        ("Zeladoria / Bueiro Obstruído", 3, "MÉDIA"),
        ("Zeladoria Geral", 1, "BAIXA"),
        ("Risco de Deslizamento", 4, "ALTA"),
        ("Iluminação Pública", 2, "BAIXA")
    ]

    agora = datetime.now()
    for i in range(25):
        cat, risco, prioridade = random.choice(categorias)
        cidadao = f"CID-{random.randint(1000, 9999)}"
        tempo = round(random.uniform(0.12, 0.45) * 1000, 2)
        data_registro = (agora - timedelta(minutes=random.randint(5, 1440))).isoformat()

        cursor.execute('''
            INSERT INTO ocorrencias_analisadas 
            (cidadao_id, categoria, nivel_risco, prioridade_atendimento, tempo_processamento_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cidadao, cat, risco, prioridade, tempo, data_registro))

    conn.commit()
    conn.close()


# -------------------------------------------------------------
# CABEÇALHO DO DASHBOARD
# -------------------------------------------------------------
st.markdown("""
<div class="header-box">
    <div class="header-title">🛡️ EcoCity Guardian — Central de BI & Analytics</div>
    <div class="header-sub">Plataforma de Monitorização Urbana em Tempo Real • Módulo Big Data & Triagem Cognitiva por IA</div>
</div>
""", unsafe_allow_html=True)

df = carregar_dados()

# -------------------------------------------------------------
# TRATAMENTO DE BANCO VAZIO
# -------------------------------------------------------------
if df.empty:
    st.info("💡 **O banco `ecocity.db` ainda não possui registros.**")
    st.caption(
        "Você pode disparar requisições via API de IA (`POST /api/v1/analisar-ocorrencia`) ou gerar dados simulados para a apresentação.")

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🎲 Gerar Dados Simulado (Demo)"):
            gerar_dados_mock()
            st.rerun()
    with col_btn2:
        if st.button("🔄 Recarregar"):
            st.rerun()
else:
    # -------------------------------------------------------------
    # SIDEBAR: FILTROS & CONTROLES
    # -------------------------------------------------------------
    st.sidebar.markdown("### 🔍 Filtros Analíticos")

    categorias_opts = ["Todas"] + list(df['categoria'].unique())
    categoria_sel = st.sidebar.selectbox("Categoria da Ocorrência", categorias_opts)

    risco_min = int(df['nivel_risco'].min())
    risco_max = int(df['nivel_risco'].max())
    risco_sel = st.sidebar.slider("Faixa de Risco (1 a 5)", risco_min, risco_max, (risco_min, risco_max))

    # Filtragem
    df_filtrado = df.copy()
    if categoria_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado['categoria'] == categoria_sel]

    df_filtrado = df_filtrado[
        (df_filtrado['nivel_risco'] >= risco_sel[0]) &
        (df_filtrado['nivel_risco'] <= risco_sel[1])
        ]

    st.sidebar.markdown("---")
    if st.sidebar.button("➕ Gerar +25 Registros Simulado"):
        gerar_dados_mock()
        st.rerun()

    # -------------------------------------------------------------
    # METRIC CARDS (KPIs)
    # -------------------------------------------------------------
    total_ocorrencias = len(df_filtrado)
    media_risco = df_filtrado['nivel_risco'].mean() if total_ocorrencias > 0 else 0
    tempo_medio = df_filtrado['tempo_processamento_ms'].mean() if total_ocorrencias > 0 else 0
    emergencias = len(df_filtrado[df_filtrado['nivel_risco'] >= 4])

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total de Chamados</div>
            <div class="kpi-value val-blue">{total_ocorrencias}</div>
            <div style="font-size:0.75rem; color:#64748b;">Registros Ingeridos</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Nível de Risco Médio</div>
            <div class="kpi-value val-amber">{media_risco:.2f} <span style="font-size:1rem; color:#64748b;">/ 5</span></div>
            <div style="font-size:0.75rem; color:#64748b;">Gravidade Agregada</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Tempo Médio Triagem IA</div>
            <div class="kpi-value val-green">{tempo_medio:.1f} <span style="font-size:1rem; color:#64748b;">ms</span></div>
            <div style="font-size:0.75rem; color:#64748b;">Desempenho Cognitivo</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Alertas Críticos</div>
            <div class="kpi-value val-red">{emergencias}</div>
            <div style="font-size:0.75rem; color:#64748b;">Risco &ge; 4 (Prioridade Alta)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # GRÁFICOS INTERATIVOS
    # -------------------------------------------------------------
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("#### 📌 Distribuição por Categoria")
        cat_counts = df_filtrado['categoria'].value_counts().reset_index()
        cat_counts.columns = ['Categoria', 'Quantidade']
        st.bar_chart(cat_counts.set_index('Categoria'), color="#38bdf8")

    with g2:
        st.markdown("#### ⚠️ Volume por Nível de Risco")
        risco_counts = df_filtrado['nivel_risco'].value_counts().sort_index().reset_index()
        risco_counts.columns = ['Nível de Risco', 'Ocorrências']
        st.area_chart(risco_counts.set_index('Nível de Risco'), color="#f87171")

    st.markdown("---")

    # -------------------------------------------------------------
    # TABELA DE INGESTÃO DE DADOS TRATADOS
    # -------------------------------------------------------------
    st.markdown("#### 📋 Registros Processados pelo Pipeline (Data Lake / Ingestão Big Data)")
    st.dataframe(
        df_filtrado.sort_values(by="id", ascending=False),
        use_container_width=True,
        hide_index=True
    )