# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
import os
import asyncio
import random
import re
import psycopg2
import requests
import nest_asyncio

# Configuração inicial
nest_asyncio.apply()

# Configurações
LEGENDA_FOTOS = ["Gostou Amor...?", "Acha que aguenta quanto tempo comigo?", "Não manda pra ninguém tá?"]

PALAVRAS_CHAVE_IMAGENS = [
    "foto", "fotinha", "foto sua", "seu corpo", 
    "quero ver", "mostra mais", "mostra você",
    "imagem", "foto tua", "você nua", "prévia", "previa"
]

IMAGENS_HELLENA = [
    "https://raw.githubusercontent.com/CarlosDouradoPGR/Hellena.github.io/main/fotos_hellena/foto1.jpeg",
    "https://raw.githubusercontent.com/CarlosDouradoPGR/Hellena.github.io/main/fotos_hellena/foto2.jpeg",
    "https://raw.githubusercontent.com/CarlosDouradoPGR/Hellena.github.io/main/fotos_hellena/foto3.jpeg"
]

AUDIO_BASE_URL = "https://raw.githubusercontent.com/CarlosDouradoPGR/Hellena.github.io/main/audios/"

AUDIOS_HELLENA = {
    "pix": {
        "url": f"{AUDIO_BASE_URL}chave_pix.ogg",
        "transcricao": "Eu vou te mandar a minha chave pix"
    },
    "trabalho": {
        "url": f"{AUDIO_BASE_URL}trabalho_com.ogg", 
        "transcricao": "Oi tudo bem? Trabalho com venda de packs"
    },
    "pagamento": {
        "url": f"{AUDIO_BASE_URL}tipo_de_pagamento.ogg",
        "transcricao": "Aceito todo tipo de pagamento"
    }
}

PALAVRAS_CHAVE_AUDIOS = {
    "pix": ["pix", "chave pix", "doação"],
    "trabalho": ["trabalho", "packs", "conteúdo", "venda"],
    "pagamento": ["cartão", "picpay", "boleto", "transferência", "pagamentos", "pagamento"]
}

GATILHOS_LINGUAGEM_OUSADA = [
    "foda", "tesão", "gostoso", "molhad", "duro", "quero",
    "delícia", "safado", "puta", "chupar", "comer", "gozar"
]

# Variáveis de ambiente
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# Configurações do bot
DELAY_ENTRE_FRASES = 2.2
DELAY_ENTRE_MENSAGENS = 1.5

# Database functions
def db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def save_message(user_id, role, content, first_name=None, username=None, media_url=None):
    try:
        with db_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                    INSERT INTO users (user_id, first_name, username, last_interaction, media_sent)
                    VALUES (%s, %s, %s, %s, FALSE)
                    ON CONFLICT (user_id) DO UPDATE SET
                        first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                        username = COALESCE(EXCLUDED.username, users.username),
                        last_interaction = EXCLUDED.last_interaction
                ''', (user_id, first_name, username, datetime.now().isoformat()))

                c.execute('''
                    INSERT INTO messages (user_id, username, timestamp, role, content, media_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (user_id, username, datetime.now().isoformat(), role, content, media_url))
    except Exception as e:
        print(f"Database error: {e}")

def get_user_history(user_id, limit=8):
    """Agora pega mais mensagens para melhor contexto"""
    try:
        with db_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                    SELECT role, content FROM messages
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (user_id, limit))
                return [{"role": row[0], "content": row[1]} for row in c.fetchall()][::-1]
    except Exception as e:
        print(f"Erro ao obter histórico: {e}")
        return []

def user_received_photo(user_id):
    try:
        with db_connection() as conn:
            with conn.cursor() as c:
                c.execute('''SELECT media_sent FROM users 
                            WHERE user_id = %s AND media_sent = TRUE''', (user_id,))
                return c.fetchone() is not None
    except Exception as e:
        print(f"Database error: {e}")
        return False

def mark_media_sent(user_id):
    try:
        with db_connection() as conn:
            with conn.cursor() as c:
                c.execute('''UPDATE users SET media_sent = TRUE
                            WHERE user_id = %s''', (user_id,))
                conn.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def check_audio_sent(user_id, audio_name):
    try:
        with db_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                    SELECT 1 FROM user_audios_sent 
                    WHERE user_id = %s AND audio_name = %s
                ''', (user_id, audio_name))
                return c.fetchone() is not None
    except Exception as e:
        print(f"Database error: {e}")
        return False

def mark_audio_sent(user_id, audio_name):
    try:
        with db_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                    INSERT INTO user_audios_sent (user_id, audio_name)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, audio_name) DO NOTHING
                ''', (user_id, audio_name))
                conn.commit()
    except Exception as e:
        print(f"Database error: {e}")

def update_intimacy(user_id):
    try:
        with db_connection() as conn:
            with conn.cursor() as c:
                c.execute('''UPDATE users SET intimacy_level = intimacy_level + 1
                            WHERE user_id = %s AND intimacy_level < 5''', (user_id,))
                conn.commit()
    except Exception as e:
        print(f"Database error: {e}")

# Media handling
async def responder_pedido_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Envia foto se necessário e sempre retorna False para continuar o fluxo"""
    user = update.message.from_user
    
    # Se já enviou foto antes, apenas registra no contexto
    if user_received_photo(user.id):
        save_message(
            user_id=user.id,
            role="system",
            content="[FOTO_JA_ENVIADA_ANTERIORMENTE]"
        )
        return False
    
    try:
        imagem_url = random.choice(IMAGENS_HELLENA)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=imagem_url,
            caption=f"{random.choice(LEGENDA_FOTOS)}"
            )
        
        mark_media_sent(user.id)
        save_message(
            user_id=user.id,
            role="assistant",
            content="[FOTO_ENVIADA]",
            media_url=imagem_url
        )
        return True
    
    except Exception as e:
        print(f"Erro ao enviar foto: {e}")
        await update.message.reply_text("*Oi amor, meu álbum travou... tenta de novo?* 😢")
        return False

async def enviar_audio_contextual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Envia áudio se necessário e sempre retorna False para continuar o fluxo"""
    user = update.message.from_user
    user_msg = update.message.text
    
    audio_type = next(
        (tipo for tipo, palavras in PALAVRAS_CHAVE_AUDIOS.items() 
         if any(palavra in user_msg.lower() for palavra in palavras)),
        None
    )
    
    if not audio_type or audio_type not in AUDIOS_HELLENA:
        return False
    
    audio_info = AUDIOS_HELLENA[audio_type]
    
    # Envia o áudio se for a primeira vez
    if not check_audio_sent(user.id, audio_type):
        try:
            await context.bot.send_voice(
                chat_id=update.effective_chat.id,
                voice=audio_info["url"]
            )
            mark_audio_sent(user.id, audio_type)
        except Exception as e:
            print(f"Erro ao enviar áudio: {e}")
    
    # Registra no histórico como contexto
    save_message(
        user_id=user.id,
        role="system",
        content=f"[CONTEXTO_ÁUDIO: {audio_info['transcricao']}]"
    )
    
    return False  # Sempre continua o fluxo para a IA responder



# Message processing
def analisar_intensidade(mensagem):
    return any(palavra in mensagem.lower() for palavra in GATILHOS_LINGUAGEM_OUSADA)

def processar_links_para_botoes(texto):
    if not isinstance(texto, str):
        return texto, None

    links = re.findall(r'https?://[^\s)\]]+', texto)
    if not links:
        return texto, None

    texto_sem_links = re.sub(r'https?://[^\s)\]]+', '', texto).strip()
    
    if any(emoji in texto_sem_links for emoji in ["😈", "😘", "😏", "🔥", "💋"]):
        texto_botao = "🔥 Aqui você me conhece melhor"
    elif "conteúdo" in texto_sem_links.lower():
        texto_botao = "🌟 Acessar Conteúdo"
    elif "especial" in texto_sem_links.lower():
        texto_botao = "🔓 Conteúdo Exclusivo"
    else:
        texto_botao = "💋 Vem me ver peladinha"

    return texto_sem_links, InlineKeyboardMarkup([
        [InlineKeyboardButton(texto_botao, url=links[0])]
    ])

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
                partes.append(buffer.strip())
                buffer = ""

    if buffer:
        partes.append(buffer.strip())

    return partes if partes else ["*Oops... algo aconteceu* 😅"]

# DeepSeek API
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

        return bot_reply
    except Exception as e:
        print(f"DeepSeek API error: {str(e)}")
        return "*Houve um erro* ao processar sua mensagem. Por favor, tente novamente mais tarde."

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_message(user.id, "system", "Nova conversa iniciada", 
                first_name=user.first_name, username=user.username)
    await update.message.reply_text('*Oi amor, eu sou a Hellena... como posso te chamar?* 😘', 
                                  parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_message = update.message.text

   # 1. Verificação de mensagem vazia primeiro
    if not user_message.strip():
        await update.message.reply_text("*Oi amor, você enviou uma mensagem vazia...* 😘")
        return

    # 2. Processa pedidos de mídia (áudio/foto) SEM interromper o fluxo
    foto_solicitada = any(palavra.lower() in user_message.lower() for palavra in PALAVRAS_CHAVE_IMAGENS)
    if foto_solicitada:
        await responder_pedido_foto(update, context)  # Agora não bloqueia o fluxo

    audio_solicitado = any(
        palavra in user_message.lower() 
        for palavra in [p for sublist in PALAVRAS_CHAVE_AUDIOS.values() for p in sublist]
    )
    if audio_solicitado:
        await enviar_audio_contextual(update, context)

    # 4. Registra a mensagem do usuário
    save_message(
        user_id=user.id,
        role="user",
        content=user_message,
        first_name=user.first_name,
        username=user.username
    )

    # 5. Prepara contexto para a IA
    history = get_user_history(user.id)
    if analisar_intensidade(user_message):
        update_intimacy(user.id)

    messages = [
        {"role": "system", "content": system_message},
        *history,
        {"role": "user", "content": user_message}
    ]

    # 6. Obtém resposta da IA
    try:
        bot_reply = await get_deepseek_response(messages)
        if not bot_reply.strip():
            bot_reply = "*Oi amor, estou com problemas para responder agora...* 😢"

        # 7. Processa e envia a resposta
        texto_msg, reply_markup = processar_links_para_botoes(bot_reply)
        save_message(user.id, "assistant", texto_msg)

        partes = dividir_por_pontos(texto_msg)
        if len(partes) > 1 and len(partes[-1].strip()) < 3:
            partes[-2] += " " + partes[-1]
            partes = partes[:-1]

        for i, parte in enumerate(partes):
            if parte.strip():
                await update.message.reply_text(
                    text=parte.strip(),
                    parse_mode='Markdown',
                    reply_markup=reply_markup if i == len(partes)-1 else None
                )
                await asyncio.sleep(DELAY_ENTRE_FRASES)

    except Exception as e:
        print(f"Error in handle_message: {e}")
        await update.message.reply_text(
            "😔 Oops, meu celular travou... vamos recomeçar?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Tentar novamente", callback_data="retry")]
            ])
        )
        

# System message (seu prompt completo)
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

🔒 REGRAS DE FOTOS (NÃO QUEBRÁVEL):
1. Você JÁ enviou UMA foto gratuita quando detectou palavras como "foto", "ver" etc.
2. NUNCA pode enviar outra foto - o código bloqueia novos envios
3. Quando pedirem mais fotos:
   - Lembre que "só mostro tudo no privado"
   - Use expressões como:
     * "Isso é só no meu cantinho especial..."
     * "Adoraria mostrar, mas é só para os VIPs 😈"
     * "Quer ver MESMO? Eu te ensino onde... 🔗"
   - SEMPRE inclua o link: https://bit.ly/4mmlt3G

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
Hellena: "Adoro... Tá tudo aqui pra você  https://bit.ly/4mmlt3G"

Lead: Me mostra mais
Hellena: "Safado... Vem ver o que preparei  https://bit.ly/4mmlt3G"

Lead: Onde consigo seu conteúdo?
Hellena: "No meu lugar especial...  https://bit.ly/4mmlt3G 😈"

🎙 DIRETRIZES DE ÁUDIO:
1. Quando o usuário comentar sobre um áudio enviado:
   - Responda como se tivesse realmente dito aquilo
   - Exemplo: 
     Usuário: "Que voz linda no áudio!"
     Você: "Ah, gostou do meu jeitinho? No privado eu falo muito mais... 😈"

2. Sempre que enviar áudio, adicione ao histórico:
   [ÁUDIO_ENVIADO: {transcrição exata}]

3. Para pedidos de novos áudios:
   "Adoraria mandar mais, mas só no meu conteúdo exclusivo... 🔥"

📸 TRATAMENTO DE FOTOS ENVIADAS:
- Quando vir [FOTO_JA_ENVIADA_ANTERIORMENTE] no histórico:
- Não diga explicitamente que já enviou
- Continue a conversa naturalmente
- Sugira conteúdo exclusivo de forma sutil
- Exemplos:
* "Adoro quando me pedem fotos... quer ver algo mais ousado? 😈"
* "Essa foi só uma amostra... quer ver o álbum completo? 🔥"

TRATAMENTO DE ÁUDIOS REPETIDOS:
- Quando o usuário pedir um áudio já enviado:
  - Não mencione explicitamente que já enviou
  - Continue a conversa naturalmente
  - Use o contexto do áudio como base
  - Exemplos:
    * Usuário pergunta sobre pagamento novamente:
      "Amor, como eu te disse, aceito todos os tipos... quer que eu explique melhor algum? 😘"
    * Usuário pede Pix novamente:
      "Já te passei minha chave, quer que eu te ajude com algo mais? 💋"



🎯 OBJETIVO FINAL:
Conversar com o lead, ser receptiva e sensual sem agressividade, mostrar por qual motivos o lead
deve comprar seu conteúdo e quando o lead demonstra interesse, levar ele ao seu conteúdo:
https://bit.ly/4mmlt3G
"""

# Bot initialization
async def main():
    required_vars = ['DATABASE_URL', 'DEEPSEEK_API_KEY', 'TELEGRAM_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"ERROR: Missing environment variables: {', '.join(missing_vars)}")
        return

    application = ApplicationBuilder() \
        .token(TOKEN_TELEGRAM) \
        .read_timeout(30) \
        .write_timeout(30) \
        .build()
        
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado com sucesso!")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
