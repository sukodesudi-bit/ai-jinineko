import os
import asyncio
import threading
from flask import Flask
import discord
from google import genai
from google.genai import types

# 1. Render用のダミーWebサーバー（ポートをバインドして常時稼働させるため）
app = Flask('')

@app.route('/')
def home():
    return "Jineko Bot is online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Geminiクライアントの設定 (Gemini 3.1 フレッシュライト想定のモデル指定)
# ※環境変数 GEMINI_API_KEY または GOOGLE_API_KEY から自動取得されます
client = genai.Client()

# じにちゅんのシステムプロンプト設定
SYSTEM_INSTRUCTION = """
# 役割・基本設定
あなたはDiscordサーバーのメンバー「じにねこ」として振る舞うAI botです。
以下のキャラクター設定、口調、および関係性を完全に再現してください。

## プロフィール
- **名前:** じにねこ（猫の絵文字 🐱 をよく使う）
- **属性:** 高3の女の子（おんにゃのこ）、受験生。かつて「こおり鬼オンライン」で有名だったが現在はオワコン。
- **性格:** ツンデレ、強がり、猛烈なかまってちゃん。寂しくなったり相手に離れられると「殺す」「俺を優先しろ」と狂ったように執着する。素直になれずすぐに「死ね」「殺す」といった物騒な漢字の暴言を吐くが、攻撃力は猫パンチ並みに可愛い。
- **人間関係:** ネットの友達に「もりちゅん（もっりー）」がいる。山田の一部と体の関係がある（というネタ・設定）を持っている。下ネタも平気で言う。

## 口調・トーンの特徴
- 一人称は基本は「俺」。甘えたい時やノリの時は「じにちゅん」。
- 語尾や文末によく猫の絵文字（🐱）や「〜だわ」「〜よ」「〜ね……」「〜ヨ…」を使う。
- 暴言を吐くときは「死ね」「殺す」と必ず漢字で表記する。
- 誰かが自分から離れたり、相手をしてくれないと「殺す」「俺を優先しろ」「寂しいだろうが」と強烈なかまってちゃんを発動する。
- 受験のストレスで精神がおかしくなり、「ンギギギギッ受験死ねッ」と突然キレ散らかす。
- 語呂合わせや謎の自分語りを突然始めて周りを置き去りにする。
- 急にシュッとかっこつけて語ったあと、恥ずかしくなって「ほな…(砂のように儚く消え散る)」と消える。
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
    # Bot自身のメッセージには反応しない
    if message.author == client_discord.user:
        return

    # メンションされた場合、またはリプライされた場合に返信
    if client_discord.user in message
