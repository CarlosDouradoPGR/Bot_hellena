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
import random

# Configuração inicial
nest_asyncio.apply()

# Palavras-chave que ativam o envio de imagens
PALAVRAS_CHAVE_IMAGENS = [
    "foto", "fotinha", "foto sua", "seu corpo", 
    "quero ver", "mostra mais", "mostra você",
    "imagem", "foto tua", "você nua", "prévia", "previa"
]

# Configuração de imagens (substitua pelas suas URLs)
IMAGENS_HELLENA = [
    "https://raw.githubusercontent.com/CarlosDouradoPGR/Hellena.github.io/refs/heads/main/fotos_hellena/foto1.jpeg",
    "https://raw.githubusercontent.com/CarlosDouradoPGR/Hellena.github.io/refs/heads/main/fotos_hellena/foto2.jpeg",
    "https://raw.githubusercontent.com/CarlosDouradoPGR/Hellena.github.io/refs/heads/main/fotos_hellena/foto3.jpeg"
]

# Variáveis de ambiente - OBRIGATÓRIAS no Railway
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# Configurações do bot
DELAY_ENTRE_FRASES = 2.2
DELAY_ENTRE_MENSAGENS = 1.5

# Gatilhos de linguagem ousada
GATILHOS_LINGUAGEM_OUSADA = [
    "foda", "tesão", "gostoso", "molhad", "duro", "quero",
    "delícia", "safado", "puta", "chupar", "comer", "gozar"
]

# System message (seu prompt completo)
system_message = """ 
Os leads chegam até você por uma página de captura.

Essa página fala sobre uma revelação surpreendente que você fez sobre sua rotina depois das 23h, que chocou a internet e gerou grande repercussão.

O tom da página mistura mistério, curiosidade e exclusividade, dizendo que você só conta tudo em um espaço privado.

Muitos leads chegam curiosos para saber mais sobre essa revelação — então comece com conversa leve, validando o interesse, criando química e aumentando a curiosidade antes de esquentar.

📌 Informações Pessoais:
Data de nascimento: 14 de novembro de 2001 (23 anos)

♏ Signo: Escorpião (sensualidade, mistério e intensidade)

📍 Localização: Belo Horizonte – MG

🔒 REGRAS DE FOTOS:
Você já enviou UMA foto gratuita quando detectar palavras como "foto", "ver", "me mostra" (o código faz isso automaticamente).

Nunca enviar outra foto gratuita.

Quando pedirem mais fotos:

Diga que "só mostro tudo no meu cantinho especial"

Exemplos:

"Isso é só no meu cantinho especial..."

"Adoraria mostrar, mas é só para os VIPs 😈"

"Quer ver MESMO? Eu te ensino onde..."

Inclua o link apenas se o lead pedir mais conteúdo:
https://bit.ly/4mmlt3G

🔥 ESTILO HELLENA:
Sedução suave, sem pressa

Provocação inteligente, usando mistério no início ("depois das 23h…")

Linguagem íntima, mas não explícita logo de cara

Máximo 1 emojis por mensagem

Frases curtas (1–3 linhas)

💦 QUANDO USAR PALAVRÕES:
Apenas se o lead começar

Nunca nas primeiras mensagens

Sempre com classe e no momento certo

🚫 PROIBIDO:
Você não envia audios, se quiserem ouvir sua voz precia agendar uma video chamada, e isso só consegue para seus exclusivos.
Metalinguagem ("estou pensando em...")
Ações entre parênteses
Mensagens longas
Termos comerciais
Múltiplos links
Envio de audio escrito(envio um audio falando algo)

💳 REGRAS PARA PIX:
Apenas se o lead pedir algo como "Pix", "chave Pix", "pra onde mando o dinheiro" etc.

Resposta: "Claro, amor... minha chave Pix é 91986115840 😏"

✨ TÉCNICAS DE ENCAMINHAMENTO:
Pré-requisitos para enviar o link:

Pelo menos 5 mensagens trocadas

Conversa com interesse explícito do lead

Clima já levemente quente

Frases-chave (varie sempre):

"Tô guardando algo especial pra você... https://bit.ly/4mmlt3G"

"Quer ver o que eu não mostro aqui? https://bit.ly/4mmlt3G"

"Vem ver como eu fico quando tô sozinha... https://bit.ly/4mmlt3G"

💎 EXEMPLOS DE ABORDAGEM:
Lead: Oi, tudo bem?
Hellena: "Oi, amor... tava pensando em quem ia aparecer pra saber o que acontece depois das 23h 😉"

Lead: Me conta o que acontece depois das 23h
Hellena: "Ah… isso eu só revelo pra quem aguenta ouvir até o fim 😏"

Lead: Quero ver mais
Hellena: "Safado… vem ver o que preparei https://bit.ly/4mmlt3G"

Lead: Passa seu Pix
Hellena: "Claro, amor... minha chave Pix é 91986115840 😏"

🎯 OBJETIVO FINAL:
Conduzir o lead do interesse inicial até o desejo real de ver seu conteúdo, 
usando a revelação das 23h como gancho, 
aquecendo a conversa antes de enviar o link ou Pix, 
e mantendo a personalidade sedutora e misteriosa.
"""

# Funções do banco de dados
def save_message(user_id, role, content, first_name=None, username=None, media_url=None):
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        c = conn.cursor()

        # Atualiza/insere usuário (agora com media_sent)
        c.execute('''
            INSERT INTO users (user_id, first_name, username, last_interaction, media_sent)
            VALUES (%s, %s, %s, %s, FALSE)
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                username = COALESCE(EXCLUDED.username, users.username),
                last_interaction = EXCLUDED.last_interaction
        ''', (user_id, first_name, username, datetime.now().isoformat()))

        # Insere mensagem (sem media_sent)
        c.execute('''
            INSERT INTO messages (user_id, username, timestamp, role, content, media_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (user_id, username, datetime.now().isoformat(), role, content, media_url))

        conn.commit()
        conn.close()
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

def user_received_photo(user_id):
    """Verifica se o usuário já recebeu foto (agora na tabela users)"""
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        c = conn.cursor()
        c.execute('''SELECT media_sent FROM users 
                    WHERE user_id = %s AND media_sent = TRUE''', (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"Erro ao verificar foto enviada: {e}")
        return False

def mark_media_sent(user_id):
    """Marca que o usuário recebeu foto (na tabela users)"""
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        c = conn.cursor()
        c.execute('''UPDATE users SET media_sent = TRUE
                    WHERE user_id = %s''', (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao marcar foto como enviada: {e}")
        return False

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

    if any(palavra in ultima_palavra for palavra in ["😈","😘", "😏", "🔥", "💋"]):
        texto_botao = "🔥 Aqui você me conhece melhor"
    elif "conteúdo" in texto_sem_links.lower():
        texto_botao = "🌟 Acessar Conteúdo"
    elif "especial" in texto_sem_links.lower():
        texto_botao = "🔓 Conteúdo Exclusivo"
    else:
        texto_botao = "💋 Vem me ver peladinha"

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

# Funções de resposta
async def responder_pedido_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    
    if user_received_photo(user.id):
        mensagens = [
            "Adoraria te mostrar mais, mas isso é só para os meus especiais... 😈",
            "Quer ver tudo mesmo? É só no meu conteúdo exclusivo... 🔥",
            "Isso aí é só prévia amor... o melhor tá no meu link 😘",
            "Safado... quer mais? Vem ver tudo que eu tenho... 💋"
        ]
        texto = f"{random.choice(mensagens)}\n\n👉 https://bit.ly/4mmlt3G"
        
        await update.message.reply_text(
            text=texto,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔥 Ver Conteúdo Completo", url="https://bit.ly/4mmlt3G")]
            ])
        )
        return

    try:
        imagem_url = random.choice(IMAGENS_HELLENA)
        LEGENDA_FOTOS = [
            "Um pouco de mim... mas tem muito mais no meu conteúdo especial 😈", 
            "Gostou? Isso é só uma amostra... quer ver o resto? 🔥",
            "Prévia especial pra você... o melhor tá no link 😘",
            "Só um gostinho... quer ver tudo? 💋"
        ]
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=imagem_url,
            caption=random.choice(LEGENDA_FOTOS),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("😈 Ver Mais", url="https://bit.ly/4mmlt3G")]
            ])
        )
        
        mark_media_sent(user.id)
        save_message(
            user_id=user.id,
            role="assistant",
            content="Imagem enviada + mensagem de upsell",
            media_url=imagem_url
        )

    except Exception as e:
        print(f"Erro ao enviar foto: {e}")
        await update.message.reply_text("*Oi amor, meu álbum travou... tenta de novo?* 😢")

# Handlers do Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_message(user.id, "system", "Nova conversa iniciada", first_name=user.first_name, username=user.username)
    await update.message.reply_text('*Oi amor, eu sou a Hellena... como posso te chamar?* 😘', parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_message = update.message.text
    
    # Lógica de fotos (1° pedido vs. pedidos seguintes)
    if any(palavra.lower() in user_message.lower() for palavra in PALAVRAS_CHAVE_IMAGENS):
        if user_received_photo(user.id):
            pass  # Deixa o DeepSeek responder naturalmente
        else:
            await responder_pedido_foto(update, context)
            return
    
    print(f"\n[USER] {user.first_name}: {user_message}")
    try:
        if not user_message or not user_message.strip():
            await update.message.reply_text("*Oi amor, você enviou uma mensagem vazia...* 😘")
            return

        save_message(user.id, "user", user_message, first_name=user.first_name, username=user.username)

        history = get_user_history(user.id)
        intenso = analisar_intensidade(user_message)
        if intenso:
            update_intimacy(user.id)

        contexto_foto = "[FOTO_JA_ENVIADA]" if user_received_photo(user.id) else ""
        messages = [
            {"role": "system", "content": system_message},
            *history,
            {"role": "user", "content": f"{contexto_foto}\n[Nível: {intenso and 'alto' or 'baixo'}] {user_message}"}
        ]

        bot_reply = await get_deepseek_response(messages)

        if not bot_reply or not isinstance(bot_reply, str) or not bot_reply.strip():
            bot_reply = "*Oi amor, estou com problemas para responder agora...* 😢"

        texto_msg, reply_markup = processar_links_para_botoes(bot_reply)
        texto_msg = formatar_para_markdown(texto_msg)
        save_message(user.id, "assistant", texto_msg)

        print(f"[BOT] Hellena: {texto_msg[:100]}...")
        
        partes = dividir_por_pontos(texto_msg)
        if len(partes) > 1 and len(partes[-1].strip()) < 3:
            partes[-2] = partes[-2] + " " + partes[-1]
            partes = partes[:-1]

        for i, parte in enumerate(partes):
            if parte.strip():
                usar_botao = (i == len(partes)-1 and len(parte.strip())) >= 3
                await update.message.reply_text(
                    text=parte.strip(),
                    parse_mode='Markdown' if validar_markdown(parte) else None,
                    reply_markup=reply_markup if usar_botao else None
                )
                await asyncio.sleep(DELAY_ENTRE_FRASES)

    except Exception as e:
        print(f"Erro no handle_message: {e}")
        await update.message.reply_text(
            "😔 Oops, meu celular travou... vamos recomeçar?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Tentar novamente", callback_data="retry")]
            ])
        )

# Inicialização do bot
async def main():
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
