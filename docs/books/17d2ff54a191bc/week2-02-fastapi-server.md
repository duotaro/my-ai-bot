---
title: "第5章: FastAPIでPython製のAI APIサーバーを構築する"
---

## CLIからの卒業、Web APIへの道

Week 2の前半では、RAGによってAIに外部知識を授ける方法を学びました。しかし、現状の `rag_local_embedding.py` や `main.py` は、開発者のターミナルでしか動かないCLIアプリケーションのままです。

これをWebアプリケーションやスマートフォンアプリから利用できるようにするには、**Web API**として機能を公開する必要があります。TypeScript/Node.jsエンジニアであれば、ExpressやNestJSを使ってAPIサーバーを立てるのがお馴染みの手法でしょう。

Pythonの世界にも、DjangoやFlaskといった強力なWebフレームワークが存在します。しかし、現代的なAI API開発シーンでは、**FastAPI** というフレームワークが圧倒的な人気を誇っています。今回はその理由を探りながら、Week 1で作ったチャットボットをAPI化していきましょう。

## なぜFastAPIなのか？ そのモダンな特徴

FastAPIが現代のPython Webフレームワークとして、特にAI/ML系のAPI開発で急速に支持を集めているのには明確な理由があります。

1.  **高性能かつ非同期ネイティブ**: FastAPIはPythonの `async/await` 構文をフル活用し、高いパフォーマンスを発揮します。ネットワークI/OやLLMへのリクエストなど、時間がかかる処理でブロッキングを起こさず、多数のリクエストを効率的に処理できます。

2.  **型ヒントによる堅牢なAPI定義**: Pythonの型ヒントと、データ検証ライブラリ **Pydantic** が統合されている点がFastAPIの大きな魅力です。これにより、リクエストのボディ、クエリパラメータ、レスポンスの形式などを型として宣言的に定義できます。FastAPIはこれらの型定義に基づき、実行時のデータバリデーション、シリアライズ、そしてエラーハンドリングを自動で行い、堅牢で予測可能なAPIインターフェースを構築できます。

3.  **直感的なデコレータベースのルーティング**: シンプルなデコレータを使うことで、特定のURLパスとHTTPメソッドに関数を紐付けることができます。これにより、APIエンドポイントの定義が非常に分かりやすく、コードの可読性と保守性が向上します。

4.  **自動生成されるAPIドキュメント**: FastAPIは、OpenAPI (Swagger UI) および ReDoc 形式のインタラクティブなAPIドキュメントを自動で生成します。Pydanticによる型定義がそのままドキュメントに反映されるため、APIの仕様書作成の手間を省き、フロントエンド開発者との連携をスムーズにします。ブラウザ上でAPIの動作確認まで行えるため、開発効率が飛躍的に向上します。

## 実践：チャットボットをFastAPIで公開する

### 1. 準備：ライブラリのインストール

まず、FastAPIと、それを動かすためのASGIサーバーである `uvicorn` を `requirements.txt` に追記しましょう。

```text:requirements.txt
# ... 既存のライブラリ ...
langchain-community>=0.3.0
langchain-chroma>=0.2.0
fastapi==0.112.0
uvicorn[standard]==0.30.5
sentence-transformers>=2.6.0
```

`pip install -r requirements.txt` を実行してインストールしてください。

### 2. APIサーバスクリプトの作成

`server.py` という新しいファイルを作成し、以下のコードを記述します。前章で構築したローカルEmbeddingによるRAG（Retrieval-Augmented Generation）のロジックをFastAPIのAPIエンドポイントに統合したものです。

```python:server.py
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings # 追加
from langchain.text_splitter import RecursiveCharacterTextSplitter # 追加
from langchain_community.document_loaders import TextLoader # 追加
from langchain_chroma import Chroma # 追加
from langchain_core.prompts import ChatPromptTemplate # 追加
from langchain_core.runnables import RunnablePassthrough # 追加

load_dotenv()

# --- 0. モデルの初期化とRAGコンポーネントの設定 ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
# 前章で採用したローカルEmbeddingモデルを使用
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2") # 変更

# 知識ファイルの読み込みと分割 (必要に応じてパスを調整)
# `server.py`がプロジェクトルートにあると仮定
loader = TextLoader("knowledge.txt")
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)
chunks = text_splitter.split_documents(documents)

# Vector DBの初期化またはロード
# persist_directoryは前章で作成されたChromaDBのパスを指定
vector_store = Chroma.from_documents(
    documents=chunks, 
    embedding=embeddings,
    persist_directory="./chroma_db" 
)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# プロンプトテンプレートの定義
template = """
以下のCONTEXTのみを使って、Questionに回答してください。

CONTEXT:
{context}

Question:
{question}
"""
rag_prompt = ChatPromptTemplate.from_template(template) # プロンプト名をrag_promptに変更

# RAGチェーンの構築
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
)

def get_rag_response(question: str) -> str: # 関数名をask_ragからget_rag_responseに変更
    response = rag_chain.invoke(question)
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
    # Chat historyはここではRAGチェーンに直接渡さないため、単純な質問応答に変換
    # より高度な実装では、履歴も考慮したRetrievalやRe-rankingを検討
    # 現在のRAGチェーンは単一の質問に対する応答に特化
    question_for_rag = request.message
    ai_response = get_rag_response(question_for_rag) # RAG関数を呼び出す
    
    return ChatResponse(answer=ai_response)
```

> **補足：チャット履歴の扱いについて**
>
> 現在の `chat_endpoint` の実装では、受け取った `history` はRAGの応答生成には直接利用されず、`message` に含まれる単一の質問のみがRAGチェーンに渡されます。これは、本記事で導入するRAGチェーンが、ドキュメントからの関連情報検索と、その情報に基づいた単一の質問応答に特化しているためです。チャット履歴を考慮したより高度な対話システム（例：過去の会話内容を基に質問の意図を汲み取ったり、関連文書の検索を最適化したりする）を構築するには、RAGチェーンの設計にさらなる工夫が必要です。

### 3. サーバーの起動と動作確認

すべての準備が整いました。ターミナルで以下のコマンドを実行し、開発サーバーを起動しましょう。

```bash
uvicorn server:app --reload
```

- **`server:app`**: `server.py` ファイルの中にある `app` という名前のFastAPIインスタンスを実行せよ、という意味です。
- **`--reload`**: `nodemon` のように、コードが変更されたら自動でサーバーをリロードする開発モードです。

ターミナルに `Application startup complete.` と表示されたら、ブラウザで `http://127.0.0.1:8000/docs` を開いてみましょう。

そこには、あなたが定義した `/chat` エンドポイントの仕様が書かれた、美しいSwagger UI（APIドキュメント）が表示されているはずです。このUIを使って、実際にAPIをテストしてみましょう。

**`/chat` エンドポイントのテスト手順:**

1.  **`/chat` エンドポイントを展開**: Swagger UI上で `POST /chat` と書かれたセクションをクリックし、詳細を展開します。
2.  **「Try it out」ボタンをクリック**: 右上にあるこのボタンをクリックすると、リクエストの編集と実行が可能になります。
3.  **リクエストボディを入力**: 「Request body」という入力欄に、以下のJSON形式のデータを入力します。
    ```json
    {
      "message": "Gemini CLIの主な機能は何ですか？",
      "history": []
    }
    ```
4.  **「Execute」ボタンをクリック**: リクエストがサーバーに送信され、応答が返ってきます。
5.  **応答を確認**: 「Responses」セクションの「Response body」に、AIからの回答がJSON形式で表示されます。`"answer": "..."` の部分に注目してください。

    **応答の例:**
    ```json
    {
      "answer": "Gemini CLIの主な機能は以下の通りです。\n\n*   コード生成\n*   質問応答\n*   テキスト要約\n*   複数ファイルにまたがるコードベースの理解\n*   シェルのように使えるエージェント機能"
    }
    ```

これにより、Web APIとしてRAGチャットボットが正常に機能していることを確認できます。




## まとめ

1.  **FastAPI** は、PythonでモダンなAPIを構築するための強力なフレームワークです。
2.  **Pydantic** を使った型定義は、TypeScriptエンジニアにとって馴染みやすく、開発体験を劇的に向上させます。
3.  **自動生成されるAPIドキュメント** は、チーム開発やフロントエンドとの連携において絶大な威力を発揮します。

Week 2の学習、お疲れ様でした。これであなたのAIは、CLIの世界を飛び出し、Webの標準的なインターフェースを手に入れました。

来週からは、いよいよ**GenAIOps**の本丸、「Ops（運用）」の世界に足を踏み入れます。作成したFastAPIサーバーを**Dockerコンテナ**化し、クラウドにデプロイする旅が始まります。お楽しみに。
