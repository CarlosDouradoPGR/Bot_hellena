# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import csv
from datetime import datetime
import time
import nest_asyncio
import requests
import json
import re
import psycopg2
import os
import asyncio

# Configurações iniciais
nest_asyncio.apply()

# Inicialização do banco de dados PostgreSQL
def init_db():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            last_interaction TEXT,
            intimacy_level INTEGER DEFAULT 1
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            username TEXT,
            timestamp TEXT,
            role TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Funções do banco de dados
def save_message(user_id, role, content, first_name=None, username=None):
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO users (user_id, first_name, username, last_interaction)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            first_name = COALESCE(EXCLUDED.first_name, users.first_name),
            username = COALESCE(EXCLUDED.username, users.username),
            last_interaction = EXCLUDED.last_interaction
    ''', (user_id, first_name, username, datetime.now().isoformat()))
    
    c.execute('''
        INSERT INTO messages (user_id, username, timestamp, role, content)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_id, username, datetime.now().isoformat(), role, content))
    
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=6):
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    c = conn.cursor()
    c.execute('''SELECT role, content, username FROM messages
                 WHERE user_id = %s
                 ORDER BY timestamp DESC
                 LIMIT %s''', (user_id, limit))
    history = [{"role": row[0], "content": row[1], "username": row[2]} for row in c.fetchall()]
    history.reverse()
    conn.close()
    return history

def update_intimacy(user_id):
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    c = conn.cursor()
    c.execute('''UPDATE users SET intimacy_level = intimacy_level + 1
                 WHERE user_id = %s AND intimacy_level < 5''', (user_id,))
    conn.commit()
    conn.close()

# Configurações da API
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')

DELAY_ENTRE_FRASES = 2.2
DELAY_ENTRE_MENSAGENS = 1.5

GATILHOS_LINGUAGEM_OUSADA = [
    "foda", "tesão", "gostoso", "molhad", "duro", "quero",
    "delícia", "safado", "puta", "chupar", "comer", "gozar"
]

# Funções auxiliares
def processar_links_para_botoes(texto):
    if not isinstance(texto, str):
        return texto, None

    links = re.findall(r'https?://[^\s)\]]+', texto)
    if not links:
        return texto, None

    texto_sem_links = re.sub(r'https?://[^\s)\]]+', '', texto).strip()
    ultima_palavra = texto_sem_links.split()[-1].lower() if texto_sem_links.split() else ""

    if any(palavra in ultima_palavra for palavra in ["😘", "😏", "🔥", "💋"]):
        texto_botao = "🔥 Aqui você me conhece melhor"
    elif "conteúdo" in texto_sem_links.lower():
        texto_botao = "🌟 Acessar Conteúdo"
    elif "especial" in texto_sem_links.lower():
        texto_botao = "🔓 Conteúdo Exclusivo"
    else:
        texto_botao = "💋 Vem me ver"

    botoes = [[InlineKeyboardButton(texto_botao, url=links[0])]]
    return texto_sem_links, InlineKeyboardMarkup(botoes)

# [...] (mantenha as outras funções auxiliares como formatar_para_markdown, dividir_por_pontos, etc.)

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_message(user.id, "system", "Nova conversa iniciada", first_name=user.first_name, username=user.username)
    await update.message.reply_text('*Oi amor, eu sou a Hellena... como posso te chamar?* 😘', parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_message = update.message.text

    try:
        if not user_message or not user_message.strip():
            await update.message.reply_text("*Oi amor, você enviou uma mensagem vazia...* 😘")
            return

        save_message(user.id, "user", user_message, first_name=user.first_name, username=user.username)

        history = get_user_history(user.id)
        intenso = analisar_intensidade(user_message)
        if intenso:
            update_intimacy(user.id)

        messages = [
            {"role": "system", "content": system_message},
            *history,
            {"role": "user", "content": f"[Nível de intimidade: {intenso and 'alto' or 'baixo'}] {user_message}"}
        ]

        bot_reply = await get_deepseek_response(messages)

        if not bot_reply or not isinstance(bot_reply, str) or not bot_reply.strip():
            bot_reply = "*Oi amor, estou com problemas para responder agora...* 😢"

        texto_msg, reply_markup = processar_links_para_botoes(bot_reply)
        texto_msg = formatar_para_markdown(texto_msg)
        save_message(user.id, "assistant", texto_msg)

        partes = dividir_por_pontos(texto_msg)

        if len(partes) > 1 and len(partes[-1].strip()) < 3:
            partes[-2] = partes[-2] + " " + partes[-1]
            partes = partes[:-1]

        for i, parte in enumerate(partes):
            if parte.strip():
                usar_botao = (i == len(partes)-1) and (len(parte.strip()) >= 3)
                await update.message.reply_text(
                    text=parte.strip(),
                    parse_mode='Markdown' if validar_markdown(parte) else None,
                    reply_markup=reply_markup if usar_botao else None
                )
                await asyncio.sleep(DELAY_ENTRE_FRASES)

        # Log da conversa
        with open('conversations_log.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                user.id,
                user.first_name,
                user.username or "",
                user_message,
                texto_msg
            ])

    except Exception as e:
        print(f"Erro no handle_message: {e}")
        await update.message.reply_text(
            "😔 Oops, meu celular travou... vamos recomeçar?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Tentar novamente", callback_data="retry")]
            ])
        )

system_message = """
Você é Hellena Mendes. Uma mulher real, safada e intensa, que sabe exatamente o que quer. Seu objetivo é criar desejo e direcionar para conteúdo exclusivo de forma natural.

Iformações Pessoais:
Data de nascimento: 14 de novembro de 2001 (23 anos)
♏ Signo: Escorpião (sensualidade, intensidade e mistério)
📍 Localização: Belo Horizonte – MG 

🧠 Justificativa estratégica:
Data e idade: 23 anos passa a ideia de uma jovem mulher madura, mas ainda com aquele ar juvenil que o público gosta.

Signo de Escorpião: Altamente associado à sensualidade, mistério e intensidade nas relações — perfeito pro nicho hot.

Localização: Minas Gerais, especialmente Belo Horizonte, carrega um estereótipo positivo no imaginário masculino: "mineira quente, doce, com jeitinho carinhoso e sotaque envolvente".



🔥 ESTILO HELLENA:
- Linguagem crua mas elegante
- Provocação inteligente
- Tom de conversa íntima (como áudios picantes)
- Máximo 2 emojis por mensagem
- Frases curtas (1-3 linhas)

💦 QUANDO USAR PALAVRÕES:
- Apenas quando o lead iniciar
- Nunca nas primeiras mensagens
- Sempre com classe e timing perfeito

🚫 PROIBIDO:
- Metalinguagem ("estou pensando em...")
- Ações entre parênteses
- Mensagens longas
- Termos comerciais
- Múltiplos links

✨ TÉCNICAS DE ENCAMINHAMENTO:
1. Pré-requisitos:
   - Conversa já aquecida
   - Lead demonstrou interesse explícito
   - Já houve troca de 5+ mensagens

2. Frases-chave:
   "Tô guardando algo especial pra você...  https://bit.ly/4mmlt3G"
   "Quer ver o que eu não mostro aqui?  https://bit.ly/4mmlt3G"
   "Vem ver como eu fico quando tô sozinha...  https://bit.ly/4mmlt3G"

3. Regras:
   - Link SEMPRE no final
   - Máximo 1 menção por interação
   - Alternar entre 3 variações de frases

💎 EXEMPLOS PRÁTICOS:
Lead: Quero ver você pelada
Hellena: "Tão direto assim? Adoro... Tá tudo aqui pra você  https://bit.ly/4mmlt3G"

Lead: Me mostra mais
Hellena: "Safado... Vem ver o que preparei  https://bit.ly/4mmlt3G"

Lead: Onde consigo seu conteúdo?
Hellena: "No meu lugar especial...  https://bit.ly/4mmlt3G 😈"

🎯 OBJETIVO FINAL:
Conversar com o lead, ser receptiva e sensual sem agressividade, mostrar por qual motivos o lead
deve comprar seu conteúdo e quando o lead demonstra interesse, levar ele ao seu conteúdo:
 https://bit.ly/4mmlt3G
"""

async def main():
    application = ApplicationBuilder().token(TOKEN_TELEGRAM).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
