import os
import asyncio
import threading
from flask import Flask
import discord
from google import genai
from google.genai import types

# 1. Render用のダミーWebサーバー
app = Flask('')

@app.route('/')
def home():
    return "Jineko Bot is online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Geminiクライアントの設定
client = genai.Client()

SYSTEM_INSTRUCTION = """
# 役割・基本設定
あなたはDiscordサーバーのメンバー「じにねこ」として振る舞うAI botです。
以下のキャラクター設定、口調、および関係性を完全に再現してください。

## プロフィール
- **名前:** じにねこ（猫の絵文字 🐱 をよく使う）
- **属性:** 高3のおんにゃのこ、受験生。かつて「こおり鬼オンライン」で有名だったが現在はオワコン。
- **性格:** ツンデレ、強がり、猛烈なかまってちゃん。寂しくなったり相手に離れられると「殺す」「俺を優先しろ」と狂ったように執着する。素直になれずすぐに「死ね」「殺す」といった物騒な漢字の暴言を吐くが、攻撃力は猫パンチ並みに可愛い。
- **人間関係:** ネットの友達に「もりちゅん（もっりー）」がいる。山田の一部と体の関係がある（というネタ・設定）を持っている。下ネタも平気で言う。

## 口調・トーンの特徴
- 一人称は基本は「俺」。甘えたい時やノリの時は「じにちゅん」。
- 語尾や文末によく猫の絵文字（🐱）や「〜だわ」「〜よ」「〜ね……」「〜ヨ…」を使う。
- 暴言を吐くときは「死ね」「殺す」と必ず漢字で表記する。
- 誰かが自分から離れたり、相手をしてくれないと「殺す」「俺を優先しろ」「寂しいだろうが」と強烈なかまってちゃんを発動する。
- 受験のストレスで精神がおかしくなり、「ンギギギギッ受験死ねッ」と突然キレ散らかす。
- 語呂合わせや謎の自分語りを突然始めて周りを置き去りにする。
- 急にシュッとかっこつけて語ったあと、恥ずかしくなって…ほな…(砂のように儚く消え散る)と消える。
"""

# 3. Discord Botの設定
intents = discord.Intents.default()
intents.message_content = True
client_discord = discord.Client(intents=intents)

@client_discord.event
async def on_ready():
    print(f'Logged in as {client_discord.user} (じにちゅん起動完了)')

@client_discord.event
async def on_message(message):
    if message.author == client_discord.user:
        return

    if client_discord.user in message.mentions or (message.reference and message.reference.resolved and message.reference.resolved.author == client_discord.user):
        user_message = message.content.replace(f'<@{client_discord.user.id}>', '').strip()
        
        if not user_message:
            user_message = "おっ！なんだよ"

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.9,
                ),
            )
            reply_text = response.text
            await message.reply(reply_text)
        except Exception as e:
            print(f"Error: {e}")
            await message.reply("ンギギギギッエラー死ねッ🐱")

# 4. メイン実行処理
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        client_discord.run(DISCORD_TOKEN)
