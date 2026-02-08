---
title: "第6章: AIの「健康診断」：Langfuseで観測性を手に入れる"
---

## 動いている、でも「中身が見えない」

前章では、FastAPIを使ってRAGチャットボットをWeb APIとして公開しました。
`uvicorn server:app --reload` でサーバーが起動し、Swagger UIからリクエストを投げれば、AIが答えてくれる状態です。しかし、一つ大きな問題が残っています。

**サーバーの中で何が起きているのか、まったく見えません。**

従来のWeb APIであれば、レスポンスタイムやHTTPステータスコードを見れば、サーバーの健康状態はある程度把握できました。しかし、LLMを組み込んだAPIは、それだけでは不十分です。なぜなら、LLMには以下のような「従来のAPIにはない特性」があるからです。

- **非決定的な出力**: 同じリクエストを投げても、毎回微妙に異なる回答が返ってくる。HTTPステータス200（成功）でも、回答内容がデタラメかもしれない。
- **見えないコスト**: LLMへのAPIコールは、トークン数に応じて課金されます。1リクエストあたりの単価は小さくても、大量のリクエストが発生すれば、月末に「えっ、こんなに？」という請求が届くかもしれません。
- **変動するレイテンシ**: LLMの応答時間は、プロンプトの長さやモデルの負荷によって大きく変動します。「昨日は速かったのに今日は遅い」が日常的に起こります。

Webエンジニアであれば、**Datadog**、**New Relic**、**Sentry** といったAPM（Application Performance Monitoring）ツールを使って、アプリケーションの挙動を監視した経験があるでしょう。これらのツールは「このAPIエンドポイントの平均レスポンスタイムは200ms」「エラー率は0.1%」といった情報をダッシュボードで可視化してくれます。

LLMアプリケーションにも、同じような「**観測性（Observability）**」が必要です。しかし、LLM特有のメトリクス —— 使用トークン数、コスト、プロンプトと応答の中身 —— を追跡するには、専用のツールが求められます。

それが、今回導入する **Langfuse** です。

## Langfuseとは？ LLMアプリのための観測プラットフォーム

**Langfuse**（ラングフューズ）は、LLMアプリケーションのための**オープンソース観測プラットフォーム**です。LangfuseはLLMアプリの「入力」「出力」「コスト」「レイテンシ」を追跡します。

Langfuseが提供する主な機能は以下の通りです。

| 機能 | 説明 | Webエンジニア向けの類推 |
|---|---|---|
| **Traces（トレース）** | 各APIコールの入出力、処理時間、使用トークン数を記録 | DatadogのAPMトレース |
| **Cost Tracking** | トークン数からAPIコストを自動計算 | クラウドのコスト管理ダッシュボード |
| **Prompt Management** | プロンプトをバージョン管理し、UIから切り替え | Feature Flagサービス（LaunchDarkly等） |
| **Evaluation** | LLMの出力品質をスコアリング・比較 | E2Eテスト結果のダッシュボード |

Langfuseには **Cloud版**（無料プランあり）と **Self-hosted版**（Docker Composeで自前デプロイ）がありますが、本章ではセットアップが簡単なCloud版を使用します。

## 実践：FastAPIサーバーにLangfuseを統合する

### 1. Langfuse Cloudアカウントの作成

まず、Langfuseのアカウントを作成します。

1. [Langfuse Cloud](https://cloud.langfuse.com/) にアクセスし、サインアップします。
2. ログイン後、「New Organization」からOrganizationsを作成後、「New Project」を選択してプロジェクトを作成します。プロジェクト名はお好みの名前でOKです。ここでは `my-ai-bot` として進めます。
3. プロジェクトの **Settings > API Keys** から、APIキーを生成します。以下の3つの値をメモしてください。
    - **Secret Key**: `sk-lf-...`
    - **Public Key**: `pk-lf-...`
    - **Host**: `https://cloud.langfuse.com`

### 2. 環境変数の追加

メモした3つの値を `.env` ファイルに追記します。

```text:.env
# こちらは第１章で追加しているはず
GOOGLE_API_KEY=your-google-api-key

# Langfuse設定（追加）
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

> **ポイント**: LangfuseのPython SDKは、これらの環境変数名を**自動的に読み取る**仕様になっています。コード内で明示的にキーを渡す必要はありません。Node.jsのライブラリで `process.env.DATABASE_URL` を自動参照するのと同じ慣習です。

### 3. `server.py` の修正 —— たった数行の変更

驚くほど少ない変更で、Langfuseの統合は完了します。LangChainには **コールバック（Callback）** という仕組みがあり、チェーンの実行前後にフック処理を挟むことができます。Langfuseはこのコールバックのハンドラーを提供しており、これを差し込むだけで、すべてのLLMコールが自動的にトレースされます。

TypeScriptエンジニアに馴染みのある概念で言えば、Express.jsの**ミドルウェア**のようなものです。リクエスト処理の前後に割り込んで、ログ記録や認証チェックを行うのと同じ仕組みです。

`server.py` を以下のように修正してください。変更箇所には `# 追加` や `# 変更` のコメントを付けています。

```python:server.py
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langfuse.langchain import CallbackHandler  # 追加

load_dotenv()

# --- 0. モデルの初期化とRAGコンポーネントの設定 ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

loader = TextLoader("knowledge.txt")
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)
chunks = text_splitter.split_documents(documents)

vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})

template = """
以下のCONTEXTのみを使って、Questionに回答してください。

CONTEXT:
{context}

Question:
{question}
"""
rag_prompt = ChatPromptTemplate.from_template(template)

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
)

def get_rag_response(question: str) -> str:
    # --- Langfuseコールバックハンドラの作成 --- (追加)
    # リクエストごとにハンドラを生成し、トレースを分離する
    langfuse_handler = CallbackHandler()

    # configにcallbacksを渡すだけで、トレースが自動記録される (変更)
    response = rag_chain.invoke(
        question,
        config={"callbacks": [langfuse_handler]}
    )

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
    question_for_rag = request.message
    ai_response = get_rag_response(question_for_rag)

    return ChatResponse(answer=ai_response)
```

### 変更点のまとめ

変更はたったの **3箇所** です。

1. **`from langfuse.callback import CallbackHandler`** をインポートに追加
2. **`langfuse_handler = CallbackHandler()`** でリクエストごとにハンドラを生成
3. **`config={"callbacks": [langfuse_handler]}`** を `rag_chain.invoke()` に渡す

これだけで、RAGチェーン内で実行されるすべての処理——Retrieverの検索、プロンプトの組み立て、LLMへのリクエストと応答——が自動的にLangfuseに記録されるようになります。

> **なぜリクエストごとにハンドラを生成するのか？**: Langfuse v2以降、`CallbackHandler` は `invoke()` のたびに自動的に新しいトレースを作成するため、グローバルに1つだけ作ってもトレースが混ざることはありません。しかし、リクエストごとにハンドラを生成することで、**リクエスト固有のメタデータ**（`user_id` や `session_id` など）をハンドラに設定しやすくなり、並行リクエスト時のスレッドセーフティも確保できます。後の章でユーザーごとのトレース管理を行う際に、この設計が活きてきます。

### 4. 動作確認：トレースを見てみよう

修正が完了したら、サーバーを起動してリクエストを送ってみましょう。

```bash
uvicorn server:app --reload
```

別のターミナルから `curl` でリクエストを送ります。

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Gemini CLIの主な機能は何ですか？", "history": []}'
```

レスポンスが返ってきたら、ブラウザで **Langfuse Cloud** のダッシュボードを開いてみましょう。

### 5. Langfuse UIでトレースを確認する

Langfuse Cloudの左メニューから **「Traces」** をクリックすると、いま送信したリクエストのトレースが表示されているはずです。トレースをクリックすると、以下のような詳細情報が確認できます。

#### トレースの全体像

各トレースには、RAGチェーンの処理ステップがツリー構造で表示されます。

```
Trace
├── Retriever（ベクトル検索）
│   └── 検索クエリと取得されたドキュメント
├── ChatPromptTemplate（プロンプト組み立て）
│   └── CONTEXTとQuestionが埋め込まれたプロンプト
└── ChatGoogleGenerativeAI（LLM呼び出し）
    ├── Input: 組み立てられたプロンプト全文
    ├── Output: AIの回答
    ├── Tokens: 入力トークン数 / 出力トークン数
    ├── Latency: 応答にかかった時間
    └── Cost: 推定コスト
```

#### 確認できるメトリクスの例

| メトリクス | 内容 | 例 |
|---|---|---|
| **Total Tokens** | 入力 + 出力の合計トークン数 | 入力: 245, 出力: 89 |
| **Latency** | LLMの応答時間 | 1.2秒 |
| **Cost** | トークン数から算出されるAPI利用コスト | $0.00012 |
| **Input** | LLMに送信されたプロンプトの全文 | CONTEXTとQuestionを含むテキスト |
| **Output** | LLMが返した回答テキスト | 「Gemini CLIの主な機能は…」 |

これが **「観測性」** です。ブラックボックスだったLLMの内部動作が、すべて可視化されました。

### 6. 複数リクエストを送って傾向を観察する

1回だけでなく、いくつか異なる質問を投げてみましょう。

```bash
# 質問1: 知識ファイルにある情報
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Gemini CLIは誰が開発しましたか？", "history": []}'

# 質問2: 知識ファイルにない情報
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Llama 3とは何ですか？", "history": []}'
```

Langfuseのダッシュボードに戻ると、複数のトレースが並んでいます。それぞれのトレースを比較してみると、質問の内容によってトークン数やレイテンシが異なることが分かるはずです。

これが「データに基づいた改善」の第一歩です。「この質問は応答が遅い」「この質問はトークンを使いすぎている」といった気づきが得られれば、プロンプトの最適化やチャンクサイズの調整など、具体的なアクションにつなげることができます。

## まとめ

1. LLMアプリケーションには、**コスト・レイテンシ・品質** を追跡する「観測性」が不可欠です。
2. **Langfuse** はLLMアプリ専用のオープンソース観測プラットフォームで、LangChainとシームレスに統合できます。
3. `server.py` への変更は**たった数行**。`CallbackHandler` を `config` に渡すだけで、すべてのLLM処理が自動的にトレースされます。
4. Langfuse UIで、各リクエストの**入出力・トークン数・レイテンシ・コスト**をリアルタイムに確認できます。

これで、あなたのAIサーバーは「何を考え、どれだけコストがかかっているのか」が丸見えになりました。Webアプリ開発で言えば、APMツールを導入した瞬間と同じ感動があるはずです。

次章では、この観測データをさらに活用して、AIの回答品質を**評価**し、プロンプトを**バージョン管理**する方法を学びます。AIの「通信簿」を作り、継続的な改善サイクルを回していきましょう。

## 本章のソースコード

本章で作成したコードは、以下のGitHubブランチで確認できます。

*   [feature/week3-02-observability-langfuse](https://github.com/duotaro/my-ai-bot/tree/feature/week3-02-observability-langfuse)
