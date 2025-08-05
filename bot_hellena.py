# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import csv
from datetime import datetime
import time
import nest_asyncio
import requests
import re
import psycopg2
import os
import asyncio

# Configuração inicial
nest_asyncio.apply()

# Variáveis de ambiente - OBRIGATÓRIAS no Railway
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')

# Configurações do bot
DELAY_ENTRE_FRASES = 2.2
DELAY_ENTRE_MENSAGENS = 1.5

# Gatilhos de linguagem ousada
GATILHOS_LINGUAGEM_OUSADA = [
    "foda", "tesão", "gostoso", "molhad", "duro", "quero",
    "delícia", "safado", "puta", "chupar", "comer", "gozar"
]

# Inicialização do banco de dados PostgreSQL
def init_db():
    try:
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
        print("Banco de dados inicializado com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")
        raise

init_db()

# Funções do banco de dados
def save_message(user_id, role, content, first_name=None, username=None):
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        c = conn.cursor()
        
        # Atualiza ou insere usuário
        c.execute('''
            INSERT INTO users (user_id, first_name, username, last_interaction)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                username = COALESCE(EXCLUDED.username, users.username),
                last_interaction = EXCLUDED.last_interaction
        ''', (user_id, first_name, username, datetime.now().isoformat()))
        
        # Insere a mensagem
        c.execute('''
            INSERT INTO messages (user_id, username, timestamp, role, content)
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, username, datetime.now().isoformat(), role, content))
        
        conn.commit()
        conn.close()
        
        # Log opcional (pode ser removido em produção)
        print(f"Mensagem salva: {user_id} - {role} - {content[:50]}...")
        
    except Exception as e:
        print(f"Erro ao salvar mensagem: {e}")

def get_user_history(user_id, limit=6):
    try:
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
    except Exception as e:
        print(f"Erro ao obter histórico: {e}")
        return []

def update_intimacy(user_id):
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        c = conn.cursor()
        c.execute('''UPDATE users SET intimacy_level = intimacy_level + 1
                     WHERE user_id = %s AND intimacy_level < 5''', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao atualizar intimidade: {e}")

# Funções auxiliares
def analisar_intensidade(mensagem):
    return any(palavra in mensagem.lower() for palavra in GATILHOS_LINGUAGEM_OUSADA)

def filtrar_metalinguagem(texto):
    proibidos = ["obs:", "nota:", "(", ")", "[...]", "tom de", "mensagem enviada"]
    return not any(palavra in texto.lower() for palavra in proibidos)

def processar_links_para_botoes(texto):
    """Versão melhorada que considera o contexto da mensagem"""
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

def formatar_para_markdown(texto):
    if not isinstance(texto, str):
        return texto

    texto = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', texto)
    texto = re.sub(r'__([^_]+)__', r'*\1*', texto)
    texto = re.sub(r'`([^`]+)`', r'*\1*', texto)
    texto = re.sub(r'(?<!\\)[*_`]', '', texto)
    texto = re.sub(r'\\[*_`]', '', texto)
    texto = re.sub(r'\*(\S)', r'* \1', texto)

    return texto.strip()

def validar_markdown(texto):
    if not isinstance(texto, str):
        return False

    asteriscos = texto.count('*')
    underscores = texto.count('_')
    backticks = texto.count('`')

    return asteriscos % 2 == 0 and underscores % 2 == 0 and backticks % 2 == 0

def dividir_por_pontos(texto):
    if not texto:
        return ["*Oops... algo aconteceu* 😅"]

    partes = []
    buffer = ""
    for i, char in enumerate(texto):
        buffer += char
        if char == '.':
            next_is_space = (i + 1 < len(texto)) and (texto[i+1] == ' ')
            prev_not_digit = (i > 0) and (not texto[i-1].isdigit())

            if (i + 1 == len(texto)) or (next_is_space and prev_not_digit):
                formatted = formatar_para_markdown(buffer.strip())
                if formatted:
                    partes.append(formatted)
                buffer = ""

    if buffer:
        formatted = formatar_para_markdown(buffer.strip())
        if formatted:
            partes.append(formatted)

    return partes if partes else ["*Oops... algo aconteceu* 😅"]

# Funções da API DeepSeek
async def get_deepseek_response(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0.4
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        bot_reply = response.json()["choices"][0]["message"]["content"]

        if not bot_reply or not isinstance(bot_reply, str) or len(bot_reply.strip()) == 0:
            return "*Estou com problemas para pensar... vamos tentar de novo?* 😘"

        while not filtrar_metalinguagem(bot_reply):
            bot_reply = await get_deepseek_response(messages)
            if not bot_reply:
                return "*Estou com dificuldades... me chama de novo?* 💋"

        return bot_reply
    except Exception as e:
        print(f"Erro na API DeepSeek: {str(e)}")
        return "*Houve um erro* ao processar sua mensagem. Por favor, tente novamente mais tarde."

# Handlers do Telegram
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

        # Log da conversa (opcional)
        try:
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
            print(f"Erro ao salvar log: {e}")

    except Exception as e:
        print(f"Erro no handle_message: {e}")
        await update.message.reply_text(
            "😔 Oops, meu celular travou... vamos recomeçar?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Tentar novamente", callback_data="retry")]
            ])
        )

# System message (seu prompt completo)
system_message = """
[SEU SYSTEM MESSAGE COMPLETO AQUI]
"""

# Inicialização do bot
async def main():
    # Verificação das variáveis de ambiente
    required_vars = ['DATABASE_URL', 'DEEPSEEK_API_KEY', 'TELEGRAM_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"ERRO: Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        return
    
    application = ApplicationBuilder().token(TOKEN_TELEGRAM).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot iniciado com sucesso!")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
