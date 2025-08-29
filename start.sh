#!/bin/bash
# Script de inicialização para Railway

PORT=${PORT:-8501}

echo "🚀 Iniciando Streamlit na porta $PORT"

# Executar o dashboard
python dashboard.py --server.port $PORT --server.address 0.0.0.0
