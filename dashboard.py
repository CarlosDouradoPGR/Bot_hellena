import os
import streamlit as st
import pandas as pd
import plotly.express as px
import random
import sys

# OBTER PORTA DO RAILWAY - FORMA CORRETA
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
    num_rows = 500  # Reduzido para performance
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
        
        # Gerar tempo de chegada
        segundos_totais = random.randint(0, 3599)
        minutos = segundos_totais // 60
        segundos = segundos_totais % 60
        tempo_chegada = f"14:{minutos:02d}:{segundos:02d}"
        
        # Tempo de processamento
        tempo_processamento = random.randint(5, 30)
        
        # Calcular tempo de saída
        segundos_saida = segundos_totais + tempo_processamento
        minutos_saida = segundos_saida // 60
        segundos_saida_resto = segundos_saida % 60
        
        # Garantir que não passe de 59 minutos
        if minutos_saida > 59:
            minutos_saida = 59
            segundos_saida_resto = 59
        
        tempo_saida = f"14:{minutos_saida:02d}:{segundos_saida_resto:02d}"
        
        quantidade = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03])[0]
        status = random.choices(['CONCLUIDO', 'ERRO'], weights=[0.95, 0.05])[0]
        prioridade = random.choices(['NORMAL', 'URGENTE'], weights=[0.8, 0.2])[0]
        
        dados.append([
            data_unica, tempo_chegada, tempo_saida, sku, 'A1', estacao,
            operador, quantidade, status, prioridade, tempo_processamento
        ])
    
    df = pd.DataFrame(dados, columns=[
        'data', 'tempo_chegada', 'tempo_saida', 'sku', 'braco', 'estacao',
        'operador', 'quantidade', 'status', 'prioridade', 'tempo_processamento_segundos'
    ])
    
    return df

# Carregar dados
def load_data():
    try:
        return gerar_dados_simulados()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Título do dashboard
st.title("📦 Kisoft - Sistema Pick by Light")
st.markdown("### Monitoramento do braço A1 - 5 estações de trabalho")
st.markdown("---")

# Carregar dados
df = load_data()

if not df.empty:
    # Sidebar com filtros
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
    
    # Aplicar filtros
    df_filtrado = df[
        (df['estacao'].isin(estacao_selecionada)) &
        (df['operador'].isin(operador_selecionado))
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
    col1, col2 = st.columns(2)
    
    with col1:
        # Performance por estação
        performance = df_filtrado.groupby('estacao').agg({
            'tempo_processamento_segundos': 'mean',
            'status': lambda x: (x == 'CONCLUIDO').mean() * 100
        }).reset_index()
        
        fig = px.bar(
            performance,
            x='estacao',
            y='tempo_processamento_segundos',
            title='⏱️ Tempo Médio por Estação',
            labels={'estacao': 'Estação', 'tempo_processamento_segundos': 'Tempo (s)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Status por estação
        status_count = df_filtrado.groupby(['estacao', 'status']).size().reset_index(name='count')
        fig = px.bar(
            status_count,
            x='estacao',
            y='count',
            color='status',
            title='📊 Status por Estação',
            labels={'estacao': 'Estação', 'count': 'Quantidade'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Dados em tabela
    st.markdown("### 📋 Últimos 20 Registros")
    st.dataframe(df_filtrado.head(20), use_container_width=True, height=300)
    
else:
    st.error("❌ Não foi possível carregar os dados.")

# Footer
st.markdown("---")
st.caption("Dashboard Kisoft Pick by Light - Sistema de monitoramento")

# ⚠️ IMPORTANTE: Configuração para Railway
if __name__ == "__main__":
    # Configurar manualmente as opções do Streamlit
    from streamlit import config as _config
    
    # Usar a porta do Railway
    _config.set_option("server.port", port)
    _config.set_option("server.address", "0.0.0.0")
    
    # Executar o Streamlit
    from streamlit.web import cli as stcli
    stcli.main()
