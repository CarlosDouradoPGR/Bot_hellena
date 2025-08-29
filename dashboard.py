    # Filtros adicionais
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

    # Reaplicar filtros
    df_filtrado = df_filtrado[
        (df_filtrado['sku'].isin(sku_selecionado)) &
        (df_filtrado['status'].isin(status_selecionado)) &
        (df_filtrado['prioridade'].isin(prioridade_selecionada)) &
        (df_filtrado['tempo_processamento_segundos'].between(tempo_range[0], tempo_range[1]))
    ].copy()

    # Abas
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "🏭 Estações", "⚠️ Erros & Prioridades"])

    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Pizza de status
            fig = px.pie(
                df_filtrado, 
                names='status', 
                title="Proporção de Status",
                hole=0.4,
                color='status',
                color_discrete_map={'CONCLUIDO': 'green', 'ERRO': 'red'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Evolução temporal
            df_time = df_filtrado.groupby('tempo_chegada').size().reset_index(name='count')
            fig = px.line(
                df_time, x='tempo_chegada', y='count',
                title="Processamentos ao Longo do Tempo"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Boxplot de tempos
            fig = px.box(
                df_filtrado,
                x='estacao', y='tempo_processamento_segundos',
                title="Distribuição de Tempos por Estação"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Heatmap Operador x Estação
            heatmap_data = df_filtrado.groupby(['operador', 'estacao']).size().reset_index(name='count')
            fig = px.density_heatmap(
                heatmap_data,
                x='estacao', y='operador', z='count',
                title="Volume por Operador x Estação",
                color_continuous_scale="Blues"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Itens urgentes e erros
        urgentes = df_filtrado[df_filtrado['prioridade'] == 'URGENTE']
        erros = df_filtrado[df_filtrado['status'] == 'ERRO']

        st.subheader("🚨 Itens Urgentes")
        st.dataframe(urgentes.head(10), use_container_width=True, height=200)

        st.subheader("❌ Erros")
        st.dataframe(erros.head(10), use_container_width=True, height=200)
