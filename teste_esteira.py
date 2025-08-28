import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# Configuração da página
st.set_page_config(
    page_title="Kisoft - Pick by Light Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do dashboard
st.title("📦 Kisoft - Sistema Pick by Light")
st.markdown("Monitoramento do braço A1 - 5 estações de trabalho")
st.markdown("---")

# Função para gerar dados simulados
@st.cache_data
def gerar_dados_kisoft():
    num_rows = 3600
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
        id_caixa = f"CAIXA-{random.randint(1, 500)}"
        
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

# Carregar dados
try:
    df = pd.read_csv('kisoft_pick_by_light.csv')
    df['datetime_chegada'] = pd.to_datetime(df['data'] + ' ' + df['tempo_chegada'], format='%d/%m/%Y %H:%M:%S')
    df['datetime_saida'] = pd.to_datetime(df['data'] + ' ' + df['tempo_saida'], format='%d/%m/%Y %H:%M:%S')
except:
    st.info("📁 Gerando dados simulados do sistema Kisoft...")
    df = gerar_dados_kisoft()

# Sidebar com filtros
st.sidebar.header("🔧 Filtros")

# Filtro por estação
estacao_selecionada = st.sidebar.multiselect(
    "Selecione a(s) estação(ões):",
    options=df['estacao'].unique(),
    default=df['estacao'].unique()
)

# Filtro por operador
operador_selecionado = st.sidebar.multiselect(
    "Selecione o(s) operador(es):",
    options=df['operador'].unique(),
    default=df['operador'].unique()
)

# Filtro por status
status_selecionado = st.sidebar.multiselect(
    "Selecione o status:",
    options=df['status'].unique(),
    default=df['status'].unique()
)

# Aplicar filtros
df_filtrado = df[
    (df['estacao'].isin(estacao_selecionada)) &
    (df['operador'].isin(operador_selecionado)) &
    (df['status'].isin(status_selecionado))
]

# Layout principal
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_itens = len(df_filtrado)
    st.metric("Total de Itens", total_itens)
    
with col2:
    eficiencia = (len(df_filtrado[df_filtrado['status'] == 'CONCLUIDO']) / len(df_filtrado)) * 100
    st.metric("Eficiência", f"{eficiencia:.1f}%")
    
with col3:
    tempo_medio = df_filtrado['tempo_processamento_segundos'].mean()
    st.metric("Tempo Médio (s)", f"{tempo_medio:.1f}")
    
with col4:
    itens_por_minuto = len(df_filtrado) / 60
    st.metric("Itens por Minuto", f"{itens_por_minuto:.1f}")

st.markdown("---")

# Gráficos
col1, col2 = st.columns(2)

with col1:
    # Performance por estação
    performance_estacao = df_filtrado.groupby('estacao').agg({
        'tempo_processamento_segundos': 'mean',
        'status': lambda x: (x == 'CONCLUIDO').mean() * 100
    }).reset_index()
    
    fig_performance = px.bar(
        performance_estacao,
        x='estacao',
        y='tempo_processamento_segundos',
        title='Tempo Médio por Estação (segundos)',
        labels={'estacao': 'Estação', 'tempo_processamento_segundos': 'Tempo Médio (s)'}
    )
    st.plotly_chart(fig_performance, use_container_width=True)
    
    # Timeline de atividades
    df_timeline = df_filtrado.groupby(pd.Grouper(key='datetime_chegada', freq='1min')).size().reset_index(name='count')
    fig_timeline = px.line(
        df_timeline, 
        x='datetime_chegada', 
        y='count',
        title='Atividade ao Longo do Tempo (itens por minuto)',
        labels={'datetime_chegada': 'Hora', 'count': 'Itens'}
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

with col2:
    # Taxa de erro por estação
    erro_estacao = df_filtrado[df_filtrado['status'] == 'ERRO'].groupby('estacao').size().reset_index(name='erros')
    total_estacao = df_filtrado.groupby('estacao').size().reset_index(name='total')
    erro_estacao = pd.merge(erro_estacao, total_estacao, on='estacao')
    erro_estacao['taxa_erro'] = (erro_estacao['erros'] / erro_estacao['total']) * 100
    
    fig_erro = px.bar(
        erro_estacao,
        x='estacao',
        y='taxa_erro',
        title='Taxa de Erro por Estação (%)',
        labels={'estacao': 'Estação', 'taxa_erro': 'Taxa de Erro (%)'}
    )
    st.plotly_chart(fig_erro, use_container_width=True)
    
    # Tipos de erro
    if not df_filtrado[df_filtrado['status'] == 'ERRO'].empty:
        tipos_erro_count = df_filtrado[df_filtrado['status'] == 'ERRO']['tipo_erro'].value_counts().reset_index()
        tipos_erro_count.columns = ['tipo_erro', 'quantidade']
        fig_tipos_erro = px.pie(
            tipos_erro_count,
            values='quantidade',
            names='tipo_erro',
            title='Distribuição dos Tipos de Erro'
        )
        st.plotly_chart(fig_tipos_erro, use_container_width=True)
    else:
        st.info("Nenhum erro encontrado nos dados filtrados")

# Tabela de dados
st.markdown("### 📋 Dados Detalhados do Pick by Light")
st.dataframe(df_filtrado, use_container_width=True)

# Download dos dados filtrados
csv = df_filtrado.to_csv(index=False)
st.download_button(
    label="📥 Download dos dados filtrados (CSV)",
    data=csv,
    file_name="kisoft_dados_filtrados.csv",
    mime="text/csv"
)
