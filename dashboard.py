import os
import streamlit as st
import pandas as pd
import plotly.express as px

# Obter a porta do Railway
port = int(os.environ.get("PORT", 8501))

# Configuração da página
st.set_page_config(
    page_title="Kisoft - Pick by Light Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do dashboard
st.title("📦 Kisoft - Sistema Pick by Light")
st.markdown("### Monitoramento do braço A1 - 5 estações de trabalho")
st.markdown("---")

# Função para carregar dados
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('kisoft_pick_by_light.csv')
        df['datetime_chegada'] = pd.to_datetime(df['data'] + ' ' + df['tempo_chegada'], format='%d/%m/%Y %H:%M:%S')
        df['datetime_saida'] = pd.to_datetime(df['data'] + ' ' + df['tempo_saida'], format='%d/%m/%Y %H:%M:%S')
        return df
    except:
        st.error("❌ Arquivo de dados não encontrado. Execute generate_data.py primeiro.")
        return pd.DataFrame()

# Carregar dados
df = load_data()

if df.empty:
    st.stop()

# Sidebar com filtros
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
]

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_itens = len(df_filtrado)
    st.metric("📦 Total de Itens", total_itens)
    
with col2:
    eficiencia = (len(df_filtrado[df_filtrado['status'] == 'CONCLUIDO']) / len(df_filtrado)) * 100
    st.metric("✅ Eficiência", f"{eficiencia:.1f}%")
    
with col3:
    tempo_medio = df_filtrado['tempo_processamento_segundos'].mean()
    st.metric("⏱️ Tempo Médio (s)", f"{tempo_medio:.1f}")
    
with col4:
    itens_por_minuto = len(df_filtrado) / 60
    st.metric("🚀 Itens por Minuto", f"{itens_por_minuto:.1f}")

st.markdown("---")

# Gráficos
col1, col2 = st.columns(2)

with col1:
    # Performance por estação
    performance_estacao = df_filtrado.groupby('estacao').agg({
        'tempo_processamento_segundos': 'mean',
        'status': lambda x: (x == 'CONCLUIDO').mean() * 100
    }).reset_index()
    
    fig_tempo = px.bar(
        performance_estacao,
        x='estacao',
        y='tempo_processamento_segundos',
        title='⏱️ Tempo Médio por Estação (segundos)',
        labels={'estacao': 'Estação', 'tempo_processamento_segundos': 'Tempo Médio (s)'}
    )
    st.plotly_chart(fig_tempo, use_container_width=True)
    
    # Timeline de atividades
    df_timeline = df_filtrado.groupby(pd.Grouper(key='datetime_chegada', freq='1min')).size().reset_index(name='count')
    fig_timeline = px.line(
        df_timeline, 
        x='datetime_chegada', 
        y='count',
        title='📈 Atividade por Minuto',
        labels={'datetime_chegada': 'Hora', 'count': 'Itens Processados'}
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
        title='❌ Taxa de Erro por Estação (%)',
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
            title='📊 Distribuição dos Tipos de Erro'
        )
        st.plotly_chart(fig_tipos_erro, use_container_width=True)

# Tabela de dados
st.markdown("### 📋 Dados Detalhados")
st.dataframe(df_filtrado, use_container_width=True, height=300)

# Download
csv = df_filtrado.to_csv(index=False)
st.download_button(
    label="📥 Download CSV",
    data=csv,
    file_name="kisoft_dados_filtrados.csv",
    mime="text/csv"
)

# ⚠️ IMPORTANTE: Adicione estas linhas no final do arquivo
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    import sys
    sys.argv = ["streamlit", "run", __file__, "--server.port", str(port), "--server.address", "0.0.0.0"]
    sys.exit(stcli.main())
