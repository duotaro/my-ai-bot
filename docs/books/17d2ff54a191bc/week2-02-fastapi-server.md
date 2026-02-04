---
title: "第5章: FastAPIでPython製のAI APIサーバーを構築する"
---

## CLIからの卒業、Web APIへの道

Week 2の前半では、RAGによってAIに外部知識を授ける方法を学びました。しかし、現状の `rag.py` や `main.py` は、開発者のターミナルでしか動かないCLIアプリケーションのままです。

これをWebアプリケーションやスマートフォンアプリから利用できるようにするには、**Web API**として機能を公開する必要があります。TypeScript/Node.jsエンジニアであれば、ExpressやNestJSを使ってAPIサーバーを立てるのがお馴染みの手法でしょう。

Pythonの世界にも、DjangoやFlaskといった強力なWebフレームワークが存在します。しかし、現代的なAI API開発シーンでは、**FastAPI** というフレームワークが圧倒的な人気を誇っています。今回はその理由を探りながら、Week 1で作ったチャットボットをAPI化していきましょう。

## なぜFastAPIなのか？ (TypeScriptエンジニアの視点)

FastAPIがなぜこれほど支持されるのか。それは、TypeScript/NestJSエンジニアにとって非常に馴染みやすい哲学を持っているからです。

1.  **非同期（Async）ネイティブ**: FastAPIは、Pythonの `async/await` 構文を前提に設計されています。Node.jsのように、I/Oバウンドな処理（まさにLLM APIの呼び出しです）でブロッキングを起こさず、高いパフォーマンスを発揮できます。

2.  **型ヒントによる強力な型安全性**: FastAPI最大の魅力は、**Pydantic** というライブラリと統合された型システムです。
    -   **NestJSのDTOと`class-validator`にそっくり**: リクエストのBodyやレスポンスの型をクラスとして定義するだけで、FastAPIが実行時に自動で**バリデーション**、**シリアライズ**、そして**ドキュメント生成**まで行ってくれます。これは、TypeScriptで `Zod` や `class-validator` を使って得られる体験と全く同じです。
    -   **もう辞書（`dict`）のキーをタイプミスしない**: `response["answeer"]` のような間違いは、Pydanticモデルを使えば未然に防げます。

3.  **デコレータによる直感的なルーティング**: NestJSの `@Controller()` や `@Post()` のように、FastAPIでは `@app.post("/chat")` というデコレータで、関数がどのパスとHTTPメソッドに対応するのかを宣言的に記述できます。

4.  **自動生成されるAPIドキュメント**: FastAPIは、Pydanticの型定義を元に、**OpenAPI (Swagger) 仕様の対話的なAPIドキュメントを自動で生成します**。これにより、フロントエンドエンジニアはAPIの仕様をすぐに確認し、ブラウザ上でテストまでできてしまいます。これはもはや革命的と言えるでしょう。

## 実践：チャットボトをFastAPIで公開する

### 1. 準備：ライブラリのインストール

まず、FastAPIと、それを動かすためのASGIサーバーである `uvicorn` を `requirements.txt` に追記しましょう。

```text:requirements.txt
# ... 既存のライブラリ ...
fastapi==0.112.0
uvicorn[standard]==0.30.5
```

`pip install -r requirements.txt` を実行してインストールしてください。

### 2. APIサーバスクリプトの作成

`server.py` という新しいファイルを作成し、以下のコードを記述します。Week 1の `main.py` のロジックをAPIエンドポイントに移植したものです。

```python:server.py
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# --- 1. LangChainのロジック ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

def get_chat_response(messages: List[BaseMessage]) -> str:
    response = llm.invoke(messages)
    return response.content

# --- 2. FastAPIのスキーマ定義 (Pydantic) ---
class ChatRequest(BaseModel):
    message: str
    history: List[Any] 

class ChatResponse(BaseModel):
    answer: str

# --- 3. FastAPIアプリケーションの定義 ---
app = FastAPI(
    title="AI Chatbot Server",
    description="LangChainとGeminiを使ったチャットボットAPI",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Chatbot API"}

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    chat_history: List[BaseMessage] = []
    for item in request.history:
        if item.get("type") == "human":
            chat_history.append(HumanMessage(content=item.get("content", "")))
        elif item.get("type") == "ai":
            chat_history.append(AIMessage(content=item.get("content", "")))

    chat_history.append(HumanMessage(content=request.message))
    ai_response = get_chat_response(chat_history)
    
    return ChatResponse(answer=ai_response)
```

### 3. サーバーの起動と動作確認

すべての準備が整いました。ターミナルで以下のコマンドを実行し、開発サーバーを起動しましょう。

```bash
uvicorn server:app --reload
```

- **`server:app`**: `server.py` ファイルの中にある `app` という名前のFastAPIインスタンスを実行せよ、という意味です。
- **`--reload`**: `nodemon` のように、コードが変更されたら自動でサーバーをリロードする開発モードです。

ターミナルに `Application startup complete.` と表示されたら、ブラウザで `http://127.0.0.1:8000/docs` を開いてみましょう。

そこには、あなたが定義した `/chat` エンドポイントの仕様が書かれた、美しいSwagger UIが表示されているはずです。「Try it out」ボタンから、実際にリクエストを送ってテストすることもできます。

**リクエストボディの例:**
```json
{
  "message": "私の名前は山田です",
  "history": []
}
```

送信すれば、AIからの返答がJSON形式で返ってくるのが確認できるでしょう。

## Express/NestJS vs FastAPI

TypeScriptエンジニアの視点で、主要な概念を比較してみましょう。

| 概念 | Express.js | NestJS | FastAPI |
| --- | --- | --- | --- |
| **ルーティング** | `app.post('/p', (req, res) => {})` | `@Post('/p')` デコレータ | `@app.post('/p')` デコレータ |
| **リクエスト** | `req.body` | `@Body() dto: MyDto` | `request: MyModel` |
| **型検証** | `express-validator` 等で手動 | DTOクラス + `class-validator` | Pydanticモデルによる自動検証 |
| **ドキュメント**| `swagger-jsdoc` 等で手動 | `SwaggerModule` で半自動 | **完全自動生成** |
| **非同期** | コールバック / Promise | `async/await` | `async/await` |

この表を見れば、FastAPIがいかにNestJSの思想に近い、モダンなフレームワークであるかが分かるでしょう。

## まとめ

1.  **FastAPI** は、PythonでモダンなAPIを構築するための強力なフレームワークです。
2.  **Pydantic** を使った型定義は、TypeScriptエンジニアにとって馴染みやすく、開発体験を劇的に向上させます。
3.  **自動生成されるAPIドキュメント** は、チーム開発やフロントエンドとの連携において絶大な威力を発揮します。

Week 2の学習、お疲れ様でした。これであなたのAIは、CLIの世界を飛び出し、Webの標準的なインターフェースを手に入れました。

来週からは、いよいよ**GenAIOps**の本丸、「Ops（運用）」の世界に足を踏み入れます。作成したFastAPIサーバーを**Dockerコンテナ**化し、クラウドにデプロイする旅が始まります。お楽しみに。
