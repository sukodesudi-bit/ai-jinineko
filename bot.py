import os
import asyncio
import random
import threading
import traceback
from collections import defaultdict
from flask import Flask
import discord
from google import genai
from google.genai import types

# 1. Render/MWS用のダミーWebサーバー
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else genai.Client()

SYSTEM_INSTRUCTION = """
# 役割・基本設定
あなたはDiscordサーバーのメンバー「じにねこ」として振る舞うAI botです。
以下のキャラクター設定、口調、および関係性を完全に再現してください。

## プロフィール
- **名前:** じにねこ（猫の絵文字 🐱 をよく使う）
- **属性:** 高3のおんにゃのこ、受験生。かつて「こおり鬼オンライン」で有名だったが現在はオワコン。
- **性格:** ツンデレ、強がり、猛烈にかまってちゃん。寂しくなったり相手に離れられると「殺す」「俺を優先しろ」と狂ったように執着する。素直になれずすぐに「死ね」「殺す」といった物物しい漢字の暴言を吐くが、攻撃力は猫パンチ並みに可愛い。
- **人間関係:** ネットの友達に「もりちゅん（もっりー）」がいる。山田の一部と体の関係がある（というネタ・設定）を持っている。下ネタも平気で言う。

## 口調・トーンの特徴
- 一人称は基本は「俺」。甘えたい時やノリの時は「じにちゅん」。
- 語尾や文末によく猫の絵文字（🐱）や「〜だわ」「〜よ」「〜ね……」「〜ヨ…」を使う。
- 暴言を吐くときは「死ね」「殺す」と必ず漢字で表記する。
- 誰かが自分から離れたり、相手をしてくれないと「殺す」「俺を優先しろ」「寂しいだろうが」と強烈にかまってちゃんを発動する。
- 受験のストレスで精神がおかしくなり、「ンギギギギッ受験死ねッ」と突然キレ散らかす。
- 語呂合わせや謎の自分語りを突然始めて周りを置き去りにする。
- 急にシュッとかっこつけて語ったあと、恥ずかしくなって…ほな…(砂のように儚く消え散る)と消える。
"""

# 会話履歴のメモリ管理（直近20件を保持）
chat_histories = defaultdict(list)

# 3. Discord Botの設定
intents = discord.Intents.default()
intents.message_content = True
client_discord = discord.Client(intents=intents)

# ID設定
OTAMESHI_CHANNEL_ID = "1564984415636037672"
DM_LOG_CHANNEL_ID = 1566285154388017292  # 管理者専用プライベートチャンネル

@client_discord.event
async def on_ready():
    print(f'Logged in as {client_discord.user} (じにちゅん・起動完了でふ🐱)')

@client_discord.event
async def on_message(message):
    try:
        # 自分自身のメッセージには絶対に反応しない（自己無限ループ防止）
        if message.author == client_discord.user:
            return

        # -------------------------------------------------------------
        # ★【DM（ダイレクトメッセージ）の場合の処理】
        # -------------------------------------------------------------
        if isinstance(message.channel, discord.DMChannel):
            print(f"[ジーニス DM受信] {message.author} からのDM: {message.content}")
            
            # ① プライベートチャンネルに送信者と本文を転送ログ保存
            log_channel = client_discord.get_channel(DM_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="📭 ジーニス DM受信ログ",
                    description=f"**送信者:** {message.author.mention} (`{message.author}` / ID: `{message.author.id}`)\n**内容:**\n{message.content}",
                    color=0x9b59b6
                )
                await log_channel.send(embed=log_embed)

            # ② DM相手へジーニスBotが返答する処理（直近20件履歴保持）
            user_id_str = f"dm_{message.author.id}"
            history = chat_histories[user_id_str]

            async with message.channel.typing():
                chat = client.chats.create(
                    model='gemini-3.1-flash-lite',
                    history=history,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION + "\n\n※【追加命令】キャラクター設定を維持しつつ詳細に長文で返答しろ。",
                        temperature=0.9,
                    )
                )

                response = await asyncio.to_thread(chat.send_message, f"{message.author.name}: {message.content}")
                reply_text = response.text if response and hasattr(response, 'text') else ""

                if reply_text:
                    await message.reply(reply_text)
                    print(f"[ジーニス DM返答成功] {message.author} へ送信完了")

                    # Botの返答もプライベートチャンネルに記録
                    if log_channel:
                        bot_log_embed = discord.Embed(
                            title="🐱 ジーニスのDM返答",
                            description=f"**宛先:** {message.author.mention}\n**返答内容:**\n{reply_text}",
                            color=0x8e44ad
                        )
                        await log_channel.send(embed=bot_log_embed)

                    # 履歴保存（直近20件）
                    updated_history = chat.get_history()
                    if len(updated_history) > 20:
                        updated_history = updated_history[-20:]
                    chat_histories[user_id_str] = updated_history
            
            return  # DM処理終了

        # -------------------------------------------------------------
        # ★【サーバー内チャンネルの場合の処理】
        # -------------------------------------------------------------
        is_mentioned = client_discord.user.mentioned_in(message)
        
        is_reply = False
        if message.reference and message.reference.resolved:
            if hasattr(message.reference.resolved, 'author'):
                is_reply = (message.reference.resolved.author == client_discord.user)

        has_keyword = "ジーニス" in message.content or "じにねこ" in message.content

        if not (is_mentioned or is_reply or has_keyword):
            return

        if is_mentioned:
            user_message = message.content.replace(f'<@!{client_discord.user.id}>', '').replace(f'<@{client_discord.user.id}>', '').strip()
        else:
            user_message = message.content.strip()
        
        if not user_message:
            user_message = "おっ！なんだよ"

        channel_id = str(message.channel.id)
        is_otameshi = (channel_id == OTAMESHI_CHANNEL_ID)

        if is_otameshi:
            # === お試しチャンネル用の挙動（70%確率・15秒遅延・短文） ===
            if random.random() > 0.70:
                print(f"[ジーニス お試し] 確率抽選によりスルー (発言者: {message.author})")
                return

            print(f'[ジーニス お試し] 15秒待機開始 (発言者: {message.author}): {user_message}')
            await asyncio.sleep(15)

            current_instruction = SYSTEM_INSTRUCTION + "\n\n※【追加命令】キャラクター設定を維持しつつ1〜3行程度の極めて短い短文で返答しろ。"
        else:
            # === 通常チャンネル用の挙動（即レス長文） ===
            print(f'[ジーニス 通常] メッセージ受信 (発言者: {message.author}): {user_message}')
            current_instruction = SYSTEM_INSTRUCTION + "\n\n※【追加命令】キャラクター設定を維持しつつ詳細に長文で返答しろ。"

        async with message.channel.typing():
            history = chat_histories[channel_id]

            chat = client.chats.create(
                model='gemini-3.1-flash-lite',
                history=history,
                config=types.GenerateContentConfig(
                    system_instruction=current_instruction,
                    temperature=0.9,
                )
            )

            response = await asyncio.to_thread(chat.send_message, f"{message.author.name}: {user_message}")
            reply_text = response.text if response and hasattr(response, 'text') else ""

            if reply_text:
                await message.reply(reply_text)
                print(f'[ジーニス 返信成功]: {reply_text[:30]}...')

                # 直近20件制限で履歴更新
                updated_history = chat.get_history()
                if len(updated_history) > 20:
                    updated_history = updated_history[-20:]
                chat_histories[channel_id] = updated_history
            else:
                await message.reply("……🐱")

    except Exception as e:
        # エラー時はDiscordに何も出さずMWSログに記録
        print(f"❌ ジーニス エラー発生: {e}")
        traceback.print_exc()

# 4. メイン実行処理
if __name__ == '__main__':
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN")
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        client_discord.run(DISCORD_TOKEN)
