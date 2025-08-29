import os
import streamlit as st
import pandas as pd
import plotly.express as px
import random
from datetime import datetime

# Obter a porta do Railway
port = int(os.environ.get("PORT", 8501))

# Configuração da página
st.set_page_config(
    page_title="Kisoft - Pick by Light Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para gerar dados simulados
def gerar_dados_simulados():
    num_rows = 1000  # Reduzido para performance
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
    
    status_options = ['CONCLUIDO', 'ERRO']
    tipos_erro = ['SKU_INCORRETO', 'QUANTIDADE_INCORRETA', 'TEMPO_EXCEDIDO', 'NENHUM']
    
    dados = []
    for i in range(num_rows):
        estacao = random.choice(estacoes)
        operador = operadores[estacoes.index(estacao)]
        sku = random.choice(skus_por_estacao[estacao])
        
        segundos_totais = random.randint(0, 3599)
        minutos = segundos_totais // 60
        segundos = segundos_totais % 60
        tempo_chegada = f"14:{minutos:02d}:{segundos:02d}"
        
        tempo_processamento = random.randint(5, 30)
        
        if random.random() < 0.05:
            status = 'ERRO'
            tempo_processamento = random.randint(31, 120)
            tipo_erro = random.choice(tipos_erro[:3])
        else:
            status = 'CONCLUIDO'
            tipo_erro = 'NENHUM'
        
        segundos_saida = segundos_totais + tempo_processamento
        minutos_saida = segundos_saida // 60
        segundos_saida_resto = segundos_saida % 60
        tempo_saida = f"14:{minutos_saida:02d}:{segundos_saida_resto:02d}"
        
        quantidade = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03])[0]
        prioridade = random.choices(['NORMAL', 'URGENTE'], weights=[0.8, 0.2])[0]
        id_caixa = f"CAIXA-{random.randint(1, 100)}"
        
        dados.append([
            data_unica, tempo_chegada, tempo_saida, sku, 'A1', estacao,
            operador, quantidade, status, tipo_erro, prioridade, id_caixa, tempo_processamento
        ])
    
    df = pd.DataFrame(dados, columns=[
        'data', 'tempo_chegada', 'tempo_saida', 'sku', 'braco', 'estacao',
        'operador', 'quantidade', 'status', 'tipo_erro', 'prioridade',
        'id_caixa', 'tempo_processamento_segundos'
    ])
    
    df['datetime_chegada'] = pd.to_datetime(df['data'] + ' ' + df['tempo_chegada'], format='%d/%m/%Y %H:%M:%S')
    df['datetime_saida'] = pd.to_datetime(df['data'] + ' ' + df['tempo_saida'], format='%d/%m/%Y %H:%M:%S')
    
    return df

# Carregar dados - SEM CACHE para evitar problemas
def load_data():
    try:
        # Tenta carregar do CSV
        df = pd.read_csv('kisoft_pick_by_light.csv')
        
        # Verifica se tem as colunas necessárias
        colunas_necessarias = ['estacao', 'operador', 'status', 'tempo_processamento_segundos']
        for coluna in colunas_necessarias:
            if coluna not in df.columns:
                st.warning(f"Coluna {coluna} não encontrada no CSV. Gerando dados simulados...")
                return gerar_dados_simulados()
        
        df['datetime_chegada'] = pd.to_datetime(df['data'] + ' ' + df['tempo_chegada'], format='%d/%m/%Y %H:%M:%S')
        df['datetime_saida'] = pd.to_datetime(df['data'] + ' ' + df['tempo_saida'], format='%d/%m/%Y %H:%M:%S')
        return df
        
    except FileNotFoundError:
        st.info("Arquivo CSV não encontrado. Gerando dados simulados...")
        return gerar_dados_simulados()
    except Exception as e:
        st.warning(f"Erro ao carregar dados: {e}. Gerando dados simulados...")
        return gerar_dados_simulados()

# Título do dashboard
st.title("📦 Kisoft - Sistema Pick by Light")
st.markdown("### Monitoramento do braço A1 - 5 estações de trabalho")
st.markdown("---")

# Carregar dados
df = load_data()

# Sidebar com informações
st.sidebar.header("ℹ️ Informações")
st.sidebar.info(f"Total de registros: {len(df)}")
st.sidebar.info(f"Período: {df['data'].iloc[0]} das 14:00 às 14:59")

# Filtros
st.sidebar.header("🔧 Filtros")

# Filtro por estação
estacao_selecionada = st.sidebar.multiselect(
    "Estação:",
    options=df['estacao'].unique(),
    default=df['estacao'].unique()
)

# Filtro por operador
operador_selecionado = st.sidebar.multiselect(
    "Operador:",
    options=df['operador'].unique(),
    default=df['operador'].unique()
)

# Filtro por status
status_selecionado = st.sidebar.multiselect(
    "Status:",
    options=df['status'].unique(),
    default=df['status'].unique()
)

# Aplicar filtros
df_filtrado = df[
    (df['estacao'].isin(estacao_selecionada)) &
    (df['operador'].isin(operador_selecionado)) &
    (df['status'].isin(status_selecionado))
].copy()

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_itens = len(df_filtrado)
    st.metric("📦 Total de Itens", total_itens)
    
with col2:
    concluidos = len(df_filtrado[df_filtrado['status'] == 'CONCLUIDO'])
    eficiencia = (concluidos / total_itens) * 100 if total_itens > 0 else 0
    st.metric("✅ Eficiência", f"{eficiencia:.1f}%")
    
with col3:
    tempo_medio = df_filtrado['tempo_processamento_segundos'].mean() if total_itens > 0 else 0
    st.metric("⏱️ Tempo Médio (s)", f"{tempo_medio:.1f}")
    
with col4:
    itens_por_minuto = total_itens / 60
    st.metric("🚀 Itens por Minuto", f"{itens_por_minuto:.1f}")

st.markdown("---")

# Gráficos
tab1, tab2 = st.tabs(["📊 Desempenho", "📈 Timeline"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # Tempo médio por estação
        if total_itens > 0:
            tempo_por_estacao = df_filtrado.groupby('estacao')['tempo_processamento_segundos'].mean().reset_index()
            fig_tempo = px.bar(
                tempo_por_estacao,
                x='estacao',
                y='tempo_processamento_segundos',
                title='⏱️ Tempo Médio por Estação (segundos)',
                labels={'estacao': 'Estação', 'tempo_processamento_segundos': 'Tempo Médio (s)'}
            )
            st.plotly_chart(fig_tempo, use_container_width=True)
    
    with col2:
        # Taxa de conclusão por estação
        if total_itens > 0:
            conclusao_por_estacao = df_filtrado.groupby('estacao')['status'].apply(
                lambda x: (x == 'CONCLUIDO').mean() * 100
            ).reset_index(name='taxa_conclusao')
            
            fig_conclusao = px.bar(
                conclusao_por_estacao,
                x='estacao',
                y='taxa_conclusao',
                title='✅ Taxa de Conclusão por Estação (%)',
                labels={'estacao': 'Estação', 'taxa_conclusao': 'Conclusão (%)'}
            )
            st.plotly_chart(fig_conclusao, use_container_width=True)

with tab2:
    # Timeline simplificada
    if total_itens > 0:
        df_filtrado['minuto'] = df_filtrado['datetime_chegada'].dt.floor('min')
        timeline = df_filtrado.groupby('minuto').size().reset_index(name='itens')
        
        fig_timeline = px.line(
            timeline,
            x='minuto',
            y='itens',
            title='📈 Itens Processados por Minuto',
            labels={'minuto': 'Hora', 'itens': 'Itens'}
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

# Dados em tabela
st.markdown("### 📋 Últimos 20 Registros")
st.dataframe(df_filtrado.head(20), use_container_width=True, height=300)

# Footer
st.markdown("---")
st.caption("Dashboard Kisoft Pick by Light - Desenvolvido para monitoramento em tempo real")

# Para Railway - IMPORTANTE
if __name__ == "__main__":
    # Esta parte é necessária para o Railway
    import streamlit.web.cli as stcli
    import sys
    from streamlit import config as _config
    
    # Configurações para o Railway
    _config.set_option("server.port", port)
    _config.set_option("server.address", "0.0.0.0")
    
    # Executar o Streamlit
    sys.argv = ["streamlit", "run", __file__]
    stcli.main()
