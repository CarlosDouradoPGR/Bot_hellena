import csv
import random
from datetime import datetime

# Configurações
num_rows = 3600  # 3600 interações em 1 hora
data_unica = "15/05/2023"

# Configurações específicas do braço A1
estacoes = ['A1-E1', 'A1-E2', 'A1-E3', 'A1-E4', 'A1-E5']
operadores = ['OP001', 'OP002', 'OP003', 'OP004', 'OP005']

# SKUs por estação (cada estação tem 5 SKUs diferentes)
skus_por_estacao = {
    'A1-E1': [1001, 1002, 1003, 1004, 1005],
    'A1-E2': [2001, 2002, 2003, 2004, 2005],
    'A1-E3': [3001, 3002, 3003, 3004, 3005],
    'A1-E4': [4001, 4002, 4003, 4004, 4005],
    'A1-E5': [5001, 5002, 5003, 5004, 5005]
}

# Status possíveis
status_options = ['CONCLUIDO', 'ERRO']
tipos_erro = ['SKU_INCORRETO', 'QUANTIDADE_INCORRETA', 'TEMPO_EXCEDIDO', 'NENHUM']

# Gerar dados
dados = []

for i in range(num_rows):
    # Selecionar estação e operador correspondente
    estacao = random.choice(estacoes)
    operador = operadores[estacoes.index(estacao)]
    
    # Selecionar SKU da estação
    sku = random.choice(skus_por_estacao[estacao])
    
    # Gerar tempo de chegada aleatório dentro da hora (14:00:00 to 14:59:59)
    segundos_totais = random.randint(0, 3599)
    minutos = segundos_totais // 60
    segundos = segundos_totais % 60
    tempo_chegada = f"14:{minutos:02d}:{segundos:02d}"
    
    # Tempo de processamento (5-30 segundos para picking)
    tempo_processamento = random.randint(5, 30)
    
    # 5% de chance de erro com tempo maior
    if random.random() < 0.05:
        status = 'ERRO'
        tempo_processamento = random.randint(31, 120)
        tipo_erro = random.choice(tipos_erro[:3])
    else:
        status = 'CONCLUIDO'
        tipo_erro = 'NENHUM'
    
    # Calcular tempo de saída
    segundos_saida = segundos_totais + tempo_processamento
    minutos_saida = segundos_saida // 60
    segundos_saida_resto = segundos_saida % 60
    tempo_saida = f"14:{minutos_saida:02d}:{segundos_saida_resto:02d}"
    
    # Quantidade (normalmente 1, mas pode ter mais)
    quantidade = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03])[0]
    
    # Prioridade
    prioridade = random.choices(['NORMAL', 'URGENTE'], weights=[0.8, 0.2])[0]
    
    # ID da caixa
    id_caixa = f"CAIXA-{random.randint(1, 500)}"
    
    dados.append([
        data_unica,
        tempo_chegada,
        tempo_saida,
        sku,
        'A1',
        estacao,
        operador,
        quantidade,
        status,
        tipo_erro,
        prioridade,
        id_caixa,
        tempo_processamento
    ])

# Ordenar por tempo de chegada
dados.sort(key=lambda x: x[1])

# Escrever no arquivo CSV
with open('kisoft_pick_by_light.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow([
        'data', 'tempo_chegada', 'tempo_saida', 'sku', 'braco', 'estacao',
        'operador', 'quantidade', 'status', 'tipo_erro', 'prioridade',
        'id_caixa', 'tempo_processamento_segundos'
    ])
    writer.writerows(dados)

print(f"✅ Arquivo 'kisoft_pick_by_light.csv' criado com {num_rows} linhas")
print("📊 Todos os registros são do braço A1 com 5 estações")
print("⏰ Período: 15/05/2023 das 14:00:00 às 14:59:59")
