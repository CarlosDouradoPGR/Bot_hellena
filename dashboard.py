import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# =====================
# Simulação de Dados
# =====================
np.random.seed(42)
dados = pd.DataFrame({
    "minuto": np.tile(np.arange(1, 6), 20),
    "linha": np.random.choice(["Linha 1", "Linha 2"], 100),
    "operador": np.random.choice(["Operador A", "Operador B", "Operador C"], 100),
    "estacao": np.random.choice(["Estação 1", "Estação 2", "Estação 3"], 100),
    "itens": np.random.poisson(5, 100),
    "tempo": np.random.normal(30, 5, 100)
})

# =====================
# Layout Principal
# =====================
st.set_page_config(page_title="Dashboard de Produção", layout="wide")
st.title("📊 Dashboard de Produção e Performance")

# =====================
# Abas
# =====================
abas = st.tabs(["📈 Evolução", "🏭 Estações", "👷 Operadores"])

# =====================
# Aba 1 - Evolução ao longo do tempo
# =====================
with abas[0]:
    st.subheader("📈 Evolução de Processos ao Longo do Tempo")

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.lineplot(data=dados, x="minuto", y="itens", hue="linha", style="operador", markers=True, ax=ax)
    ax.set_title("Itens Separados por Minuto")
    ax.set_ylabel("Quantidade de Itens")
    ax.set_xlabel("Minuto")
    st.pyplot(fig)

    # Média e meta (-5%)
    media_itens = dados.groupby("minuto")["itens"].mean().mean()
    meta = media_itens * 0.95

    st.write(f"📌 **Média geral de itens por minuto:** {media_itens:.2f}")
    st.write(f"🎯 **Meta de produtividade (95% da média):** {meta:.2f}")

    fig2, ax2 = plt.subplots(figsize=(8, 4))
    dados_group = dados.groupby("minuto")["itens"].mean().reset_index()
    ax2.plot(dados_group["minuto"], dados_group["itens"], marker="o", label="Média Itens")
    ax2.axhline(y=meta, color="r", linestyle="--", label="Meta (95%)")
    ax2.set_title("Média de Itens por Minuto vs Meta")
    ax2.set_ylabel("Média de Itens")
    ax2.set_xlabel("Minuto")
    ax2.legend()
    st.pyplot(fig2)

# =====================
# Aba 2 - Estações
# =====================
with abas[1]:
    st.subheader("🏭 Análise por Estação")

    fig3, ax3 = plt.subplots(figsize=(8, 4))
    sns.boxplot(data=dados, x="estacao", y="tempo", ax=ax3)
    ax3.set_title("Distribuição dos Tempos por Estação")
    ax3.set_ylabel("Tempo (segundos)")
    ax3.set_xlabel("Estação")
    st.pyplot(fig3)

    st.write("""
    📊 **Interpretação:**  
    O boxplot mostra como os tempos estão distribuídos em cada estação.  
    - A linha central é a **mediana** do tempo.  
    - As caixas representam o intervalo onde estão 50% dos tempos.  
    - Pontos fora (outliers) indicam tempos muito diferentes da média.  
    """)

# =====================
# Aba 3 - Operadores
# =====================
with abas[2]:
    st.subheader("👷 Resumo por Operador")

    # Ranking de produtividade (itens/minuto por operador)
    produtividade = dados.groupby("operador")["itens"].mean().reset_index().sort_values(by="itens", ascending=False)

    fig4, ax4 = plt.subplots(figsize=(6, 4))
    sns.barplot(data=produtividade, x="operador", y="itens", palette="viridis", ax=ax4)
    ax4.set_title("Produtividade Média por Operador (Itens/Minuto)")
    ax4.set_ylabel("Itens por Minuto")
    ax4.set_xlabel("Operador")
    st.pyplot(fig4)

    media_geral = produtividade["itens"].mean()
    st.write(f"📌 **Média geral entre operadores:** {media_geral:.2f} itens/minuto")

    melhor = produtividade.iloc[0]
    st.success(f"🏆 O operador com melhor desempenho foi **{melhor['operador']}**, com média de **{melhor['itens']:.2f} itens/minuto**.")
