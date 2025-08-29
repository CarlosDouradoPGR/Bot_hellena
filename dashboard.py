import streamlit as st
import pandas as pd
import plotly.express as px
import random

# ==============================
# CONFIGURAÇÃO DE AUTENTICAÇÃO
# ==============================
USER_CREDENTIALS = {
    "Carlos": "87654321"
}

def check_authentication():
    """Verifica se o usuário está autenticado"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    return st.session_state.authenticated

def login_form():
    """Exibe o formulário de login"""
    st.title("🔐 Sistema Kisoft - Autenticação")
    st.markdown("---")
    
    with st.form("login_form"):
        username = st.text_input("👤 Usuário")
        password = st.text_input("🔒 Senha", type="password")
        submit_button = st.form_submit_button("Entrar")
        
        if submit_button:
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state.authenticated = True
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos")

# ==============================
# VERIFICAÇÃO DE AUTENTICAÇÃO
# ==============================
if not check_authentication():
    login_form()
    st.stop()

# ==============================
# FUNCIONALIDADES DO DASHBOARD
# ==============================
# Configuração da página
st.set_page_config(
    page_title="Kisoft - Pick by Light Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Botão de logout na sidebar
with st.sidebar:
    st.markdown("---")
    if st.button("🚪 Sair"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown(f"**Usuário:** TPCcas")
    st.markdown("---")

# ==============================
# Função para gerar dados simulados
# ==============================
def gerar_dados_simulados():
    num_rows = 500
    data_unica = "15/05/2023"

    estacoes = ['A1-E1', 'A1-E2', 'A1-E3', 'A1-E4', 'A1-E5']
    operadores = ['OP001', 'OP002', 'OP003', 'OP004', 'OP005']

    skus_por_estacao = {
        'A1-E1': [1001, 1002, 1003, 1004, 1005],
        'A1-E2': [2001, 2002, 2003, 2004, 2005],
        'A1-E3': [3001, 3002, 3003, 3004, 3005],
        'A1-E4': [4001, 4002, 4003, 4004, 4005],
        'A1-E5': [5001, 5002, 5003, 5004, 5005]
    }

    dados = []
    for i in range(num_rows):
        estacao = random.choice(estacoes)
        operador = operadores[estacoes.index(estacao)]
        sku = random.choice(skus_por_estacao[estacao])

        # Tempo de chegada
        segundos_totais = random.randint(0, 3599)
        minutos = segundos_totais // 60
        segundos = segundos_totais % 60
        tempo_chegada = f"14:{minutos:02d}:{segundos:02d}"

        # Processamento
        tempo_processamento = random.randint(5, 30)

        # Saída
        segundos_saida = segundos_totais + tempo_processamento
        minutos_saida = min(59, segundos_saida // 60)
        segundos_saida_resto = min(59, segundos_saida % 60)
        tempo_saida = f"14:{minutos_saida:02d}:{segundos_saida_resto:02d}"

        quantidade = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03])[0]
        status = random.choices(['CONCLUIDO', 'ERRO'], weights=[0.95, 0.05])[0]
        prioridade = random.choices(['NORMAL', 'URGENTE'], weights=[0.8, 0.2])[0]

        dados.append([
            data_unica, tempo_chegada, tempo_saida, sku, 'A1', estacao,
            operador, quantidade, status, prioridade, tempo_processamento, minutos
        ])

    df = pd.DataFrame(dados, columns=[
        'data', 'tempo_chegada', 'tempo_saida', 'sku', 'braco', 'estacao',
        'operador', 'quantidade', 'status', 'prioridade',
        'tempo_processamento_segundos', 'minuto'
    ])
    return df

# ==============================
# Carregar dados
# ==============================
def load_data():
    try:
        return gerar_dados_simulados()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# ==============================
# Título do dashboard
# ==============================
st.title("📦 Kisoft - Sistema Pick by Light")
st.markdown("### Monitoramento do braço A1 - 5 estações de trabalho")
st.markdown("---")

df = load_data()

if not df.empty:

    # ==============================
    # Filtros na Sidebar
    # ==============================
    st.sidebar.header("🔧 Filtros")

    estacao_selecionada = st.sidebar.multiselect(
        "Estação:",
        options=df['estacao'].unique(),
        default=df['estacao'].unique()
    )

    operador_selecionado = st.sidebar.multiselect(
        "Operador:",
        options=df['operador'].unique(),
        default=df['operador'].unique()
    )

    sku_selecionado = st.sidebar.multiselect(
        "SKU:",
        options=df['sku'].unique(),
        default=df['sku'].unique()
    )

    status_selecionado = st.sidebar.multiselect(
        "Status:",
        options=df['status'].unique(),
        default=df['status'].unique()
    )

    prioridade_selecionada = st.sidebar.multiselect(
        "Prioridade:",
        options=df['prioridade'].unique(),
        default=df['prioridade'].unique()
    )

    tempo_range = st.sidebar.slider(
        "Tempo de Processamento (s):",
        int(df['tempo_processamento_segundos'].min()),
        int(df['tempo_processamento_segundos'].max()),
        (int(df['tempo_processamento_segundos'].min()), int(df['tempo_processamento_segundos'].max()))
    )

    # Aplicar filtros
    df_filtrado = df[
        (df['estacao'].isin(estacao_selecionada)) &
        (df['operador'].isin(operador_selecionado)) &
        (df['sku'].isin(sku_selecionado)) &
        (df['status'].isin(status_selecionado)) &
        (df['prioridade'].isin(prioridade_selecionada)) &
        (df['tempo_processamento_segundos'].between(tempo_range[0], tempo_range[1]))
    ].copy()

    # ==============================
    # KPIs principais
    # ==============================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📦 Total de Itens", len(df_filtrado))

    with col2:
        concluidos = len(df_filtrado[df_filtrado['status'] == 'CONCLUIDO'])
        eficiencia = (concluidos / len(df_filtrado)) * 100 if len(df_filtrado) > 0 else 0
        st.metric("✅ Eficiência", f"{eficiencia:.1f}%")

    with col3:
        tempo_medio = df_filtrado['tempo_processamento_segundos'].mean() if len(df_filtrado) > 0 else 0
        st.metric("⏱️ Tempo Médio (s)", f"{tempo_medio:.1f}")

    with col4:
        itens_por_minuto = len(df_filtrado) / (df_filtrado['minuto'].max()+1 if len(df_filtrado) > 0 else 1)
        st.metric("🚀 Itens por Minuto", f"{itens_por_minuto:.2f}")

    st.markdown("---")

    # ==============================
    # Abas de Navegação
    # ==============================
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "🏭 Estações", "⚠️ Alertas"])

    # ------------------------------
    # Aba 1 - Visão Geral
    # ------------------------------
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            # Evolução por minuto
            df_min = df_filtrado.groupby(['minuto']).size().reset_index(name='qtd')
            fig = px.line(
                df_min, x='minuto', y='qtd',
                markers=True,
                title="Evolução de Processos ao Longo do Tempo (minuto a minuto)"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Média de itens/minuto e meta
            itens_minuto = df_filtrado.groupby('minuto').size().reset_index(name='qtd')
            media = itens_minuto['qtd'].mean() if len(itens_minuto) > 0 else 0
            meta = media * 0.95

            fig = px.bar(itens_minuto, x='minuto', y='qtd', title="Itens/Minuto vs Meta")
            fig.add_hline(y=media, line_dash="dot", line_color="blue", annotation_text="Média", annotation_position="top left")
            fig.add_hline(y=meta, line_dash="dash", line_color="red", annotation_text="Meta (-5%)", annotation_position="bottom left")
            st.plotly_chart(fig, use_container_width=True)

    # ------------------------------
    # Aba 2 - Estações
    # ------------------------------
    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            performance = df_filtrado.groupby('estacao').agg({
                'tempo_processamento_segundos': 'mean'
            }).reset_index()
            fig = px.bar(
                performance,
                x='estacao', y='tempo_processamento_segundos',
                title='⏱️ Tempo Médio por Estação',
                labels={'tempo_processamento_segundos': 'Tempo (s)'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.box(
                df_filtrado,
                x='estacao', y='tempo_processamento_segundos',
                title="Distribuição dos Tempos por Estação"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 🔥 Heatmap Operador x Estação")
        heatmap_data = df_filtrado.groupby(['operador', 'estacao']).size().reset_index(name='count')
        fig = px.density_heatmap(
            heatmap_data,
            x='estacao', y='operador', z='count',
            title="Volume por Operador x Estação",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------
    # Aba 3 - Alertas
    # ------------------------------
    with tab3:
        urgentes = df_filtrado[df_filtrado['prioridade'] == 'URGENTE']

        st.subheader("🚨 Itens Urgentes")
        st.dataframe(urgentes.head(15), use_container_width=True, height=300)

        # Alerta de eficiência
        if eficiencia < 95:  # exemplo de meta de eficiência
            st.error(f"⚠️ Eficiência abaixo da meta: {eficiencia:.1f}%")
        else:
            st.success(f"✅ Eficiência dentro da meta: {eficiencia:.1f}%")

    # ==============================
    # Dados em Tabela
    # ==============================
    st.markdown("---")
    st.markdown("### 📋 Últimos 20 Registros")
    st.dataframe(df_filtrado.head(20), use_container_width=True, height=300)

else:
    st.error("❌ Não foi possível carregar os dados.")

# ==============================
# Rodapé
# ==============================
st.markdown("---")
st.caption("Dashboard Kisoft Pick by Light - Sistema de monitoramento")
