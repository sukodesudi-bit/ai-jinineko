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
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# バックグラウンドでWebサーバーを動かす
threading.Thread(target=run_flask, daemon=True).start()

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

# お試しチャンネルのID
OTAMESHI_CHANNEL_ID = 1564984415636037672

@client_discord.event
async def on_ready():
    print(f'Logged in as {client_discord.user} (じにちゅん・20秒遅延＆エラー無視版🐱)')

@client_discord.event
async def on_message(message):
    # お試しチャンネルかどうかを判定
    is_otameshi = (message.channel.id == OTAMESHI_CHANNEL_ID)

    # お試しチャンネル以外では、自分自身のメッセージには絶対に反応しない（通常チャンネルの無限ループ防止）
    if not is_otameshi and message.author == client_discord.user:
        return

    if is_otameshi:
        # === お試しチャンネル用の挙動（他Bot反応可・20秒遅延・短文・エラー時は無視） ===
        is_mentioned = client_discord.user.mentioned_in(message)
        has_keyword = "ジーニス" in message.content
        is_from_any_bot = message.author.bot

        # メンション、キーワード、またはボットからのメッセージであれば反応する
        if is_mentioned or has_keyword or is_from_any_bot:
            print(f'お試しチャンネルメッセージ受信 (20秒待機開始): {message.content}')
            
            try:
                # 15秒の遅延
                await asyncio.sleep(15)

                if is_mentioned:
                    user_message = message.content.replace(f'<@!{client_discord.user.id}>', '').replace(f'<@{client_discord.user.id}>', '').strip()
                else:
                    user_message = message.content.strip()
                
                if not user_message:
                    user_message = "おっ！なんだよ"

                def call_gemini():
                    return client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"以下のメッセージに対して、キャラクター設定を維持しつつ1〜3行程度の極めて短い短文で返答しろ: {user_message}",
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            temperature=0.9,
                        ),
                    )

                response = await asyncio.to_thread(call_gemini)
                
                if response and hasattr(response, 'text') and response.text:
                    await message.reply(response.text, mention_author=(message.author != client_discord.user))
                    print(f'お試し返信成功: {response.text}')
                else:
                    await message.reply("……🐱", mention_author=(message.author != client_discord.user))

            except Exception as e:
                # エラーのときは何も書かず、完全に無視する
                print(f"エラー発生（無視します）: {type(e).__name__} - {e}")
                return

    else:
        # === 通常チャンネル用の挙動（他Bot完全無視・ユーザーのみ・即レス長文） ===
        if message.author.bot:
            return

        is_mentioned = client_discord.user.mentioned_in(message)
        has_keyword = "ジーニス" in message.content

        if is_mentioned or has_keyword:
            print(f'通常チャンネルメッセージ受信: {message.content}')
            try:
                if is_mentioned:
                    user_message = message.content.replace(f'<@!{client_discord.user.id}>', '').replace(f'<@{client_discord.user.id}>', '').strip()
                else:
                    user_message = message.content.strip()
                
                if not user_message:
                    user_message = "おっ！なんだよ"

                async with message.channel.typing():
                    def call_gemini():
                        prompt = f"以下のメッセージに対して、キャラクター設定を維持しつつ詳細に長文で返答しろ: {user_message}"
                        return client.models.generate_content(
                            model='gemini-3.8-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_INSTRUCTION,
                                temperature=0.9,
                            ),
                        )

                    response = await asyncio.to_thread(call_gemini)
                    
                    if response and hasattr(response, 'text') and response.text:
                        await message.reply(response.text)
                        print(f'通常返信成功: {response.text}')
                    else:
                        await message.reply("……🐱")

            except Exception as e:
                err_code = type(e).__name__
                print(f"エラー発生: {err_code} - {e}")
                await message.reply(f"{err_code}")

# 4. メイン実行処理
if __name__ == '__main__':
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        client_discord.run(DISCORD_TOKEN)
