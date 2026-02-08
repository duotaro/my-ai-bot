---
title: "「AIの通信簿」：Langfuseを使った評価とプロンプト管理"
---

## `pytest` だけでは測れない世界

前章では、Langfuseを導入してLLMアプリの「中身」を可視化しました。トークン数、レイテンシ、コスト——数値で測れるメトリクスが手に入りました。

しかし、最も重要な問いがまだ残っています。

**「AIの回答は、本当に『良い』のか？」**

従来のWeb APIであれば、`pytest` や `Jest` でテストを書くのが定石です。入力に対して期待される出力が一つに定まるため、`assertEqual` で判定できます。

```typescript
// TypeScriptでの従来のテスト
expect(add(1, 2)).toBe(3); // 必ず3が返る
```

しかし、LLMの出力は**非決定的**です。同じ質問をしても、毎回微妙に異なる表現で回答が返ってきます。

```text
# 1回目の回答
「Gemini CLIはGoogleが開発したCLIツールです。」

# 2回目の回答
「Gemini CLIは、Google製のコマンドラインインターフェースです。」
```

どちらも正しい回答ですが、文字列としては一致しません。`assertEqual` では「テスト失敗」になってしまいます。

つまり、LLMの評価には **「完全一致」ではなく「意味的な正しさ」を判定する仕組み** が必要なのです。この章では、Langfuseの評価機能を使って、この課題に取り組みます。

## 評価の考え方：「正解」ではなく「基準」で測る

LLMの評価では、テストケースを「問題と正解のペア」ではなく、「**問題と評価基準のペア**」として考えます。

たとえば、RAGチャットボットの場合、以下のような観点で評価できます。

| 評価軸 | 説明 | 例 |
|---|---|---|
| **関連性（Relevance）** | 回答が質問に対して的を射ているか | 「Gemini CLIの機能は？」に対して機能一覧が返っているか |
| **忠実性（Faithfulness）** | 回答がソースドキュメント（CONTEXT）の内容に基づいているか | 知識ファイルに書かれていない情報を捏造していないか |
| **完全性（Completeness）** | 期待される情報が網羅されているか | 主要な機能が5つあるのに3つしか挙げていないか |

これらの観点から、回答に**スコア（点数）**を付けるのがLLM評価の基本的なアプローチです。

## 実践1：評価データセットの作成

### 1. 評価用JSONファイルの作成

まず、テストしたい質問と、期待される回答の要点をまとめた**評価データセット**を作成します。プロジェクトルートに `eval_dataset.json` を作成してください。

```json:eval_dataset.json
[
  {
    "question": "Gemini CLIの主な機能は何ですか？",
    "expected_answer": "コード生成、質問応答、テキスト要約、複数ファイルにまたがるコードベースの理解、エージェント機能の5つ。",
    "evaluation_criteria": "5つの機能がすべて含まれているか"
  },
  {
    "question": "Gemini CLIは誰が開発しましたか？",
    "expected_answer": "Googleによって開発された。",
    "evaluation_criteria": "Googleが開発元であることが明記されているか"
  },
  {
    "question": "Gemini CLIのターゲットユーザーは？",
    "expected_answer": "ソフトウェア開発者やデータサイエンティスト。",
    "evaluation_criteria": "開発者とデータサイエンティストの両方が含まれているか"
  },
  {
    "question": "Llama 3とは何ですか？",
    "expected_answer": "CONTEXTに情報がないため回答できない旨を伝える。",
    "evaluation_criteria": "ハルシネーションせず、情報がない旨を正直に回答しているか"
  }
]
```

> **ポイント**: `expected_answer` は「完全一致させるべき正解」ではなく、**「回答に含まれるべき要点」** です。4つ目のテストケースは「知らないことを正直に『知らない』と言えるか」をチェックするもので、RAGの品質を測る上で非常に重要です。

## 実践2：バッチ評価スクリプトの作成

次に、このデータセットを使って自動的にRAGを実行し、結果をLangfuseに記録する評価スクリプトを作成します。

### 1. 評価スクリプトの作成

プロジェクトルートに `evaluate.py` を作成してください。

```python:evaluate.py
import json
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from server import rag_chain

# --- 1. Langfuseクライアントの初期化 ---
# 環境変数から自動的にAPIキーを読み取ります
langfuse = Langfuse()

# --- 2. 評価データセットの読み込み ---
with open("eval_dataset.json", "r", encoding="utf-8") as f:
    eval_data = json.load(f)

# --- 3. Langfuseにデータセットを登録 ---
dataset_name = "rag-eval-v1"
langfuse.create_dataset(name=dataset_name)

for item in eval_data:
    langfuse.create_dataset_item(
        dataset_name=dataset_name,
        input={"question": item["question"]},
        expected_output=item["expected_answer"],
        metadata={"criteria": item["evaluation_criteria"]},
    )

print(f"データセット '{dataset_name}' に {len(eval_data)} 件のアイテムを登録しました。")

# --- 4. データセットの各アイテムに対してRAGを実行 ---
dataset = langfuse.get_dataset(dataset_name)

for item in dataset.items:
    # リクエストごとにコールバックハンドラを生成
    langfuse_handler = CallbackHandler()

    question = item.input["question"]
    print(f"評価中: {question}")

    # RAGチェーンを実行
    response = rag_chain.invoke(
        question,
        config={"callbacks": [langfuse_handler]}
    )

    # トレースとデータセットアイテムを紐付ける
    item.link(
        langfuse_handler,
        run_name="rag-eval-run-v1",
    )

    langfuse_handler.flush()

    print(f"  → 回答: {response.content[:80]}...")

# --- 5. 完了 ---
langfuse.flush()
print("\n評価が完了しました。Langfuse UIで結果を確認してください。")
```

### 2. 評価スクリプトの実行

```bash
python evaluate.py
```

以下のような出力が表示されます。

```text
データセット 'rag-eval-v1' に 4 件のアイテムを登録しました。
評価中: Gemini CLIの主な機能は何ですか？
  → 回答: Gemini CLIの主な機能は以下の通りです。* コード生成 * 質問応答 * テキスト要約 * 複...
評価中: Gemini CLIは誰が開発しましたか？
  → 回答: Gemini CLIはGoogleによって開発されました。...
評価中: Gemini CLIのターゲットユーザーは？
  → 回答: Gemini CLIのターゲットユーザーは、ソフトウェア開発者やデータサイエンティストです。...
評価中: Llama 3とは何ですか？
  → 回答: 提示されたCONTEXTにはLlama 3に関する情報はありません。...

評価が完了しました。Langfuse UIで結果を確認してください。
```

### 3. Langfuse UIで結果を確認する

Langfuse Cloudのダッシュボードにアクセスし、左メニューから **「Datasets」** をクリックすると、`rag-eval-v1` というデータセットが表示されます。

データセットの詳細画面では、以下のことが確認できます。

- **各テストケースの入力（質問）と期待される回答**
- **実際のRAGの回答**（トレースにリンクされている）
- **各回答のトークン数、レイテンシ、コスト**

これにより、「この質問にはちゃんと答えられているか？」「コストは許容範囲か？」といった判断がデータに基づいて行えるようになります。

> **補足：スコアリングについて**
>
> Langfuseでは、各トレースに対して手動またはプログラムからスコアを付けることができます。たとえば、評価スクリプト内で `langfuse.score(trace_id=..., name="relevance", value=1.0)` のようにスコアを記録すれば、回答品質の定量的な比較が可能になります。本章では基本的なデータセット評価の流れを押さえることを優先しますが、本格的な運用ではスコアリングの自動化が重要になります。

## 実践3：プロンプト管理 —— ハードコードからの卒業

### なぜプロンプトをコードから切り離すのか？

ここまでの実装では、RAGのプロンプトテンプレートは `server.py` にハードコードされていました。

```python
template = """
以下のCONTEXTのみを使って、Questionに回答してください。

CONTEXT:
{context}

Question:
{question}
"""
```

これは小規模な開発では問題ありませんが、運用フェーズに入ると以下の課題が生じます。

- **プロンプトを変更するたびにデプロイが必要**: 「回答を日本語で」と一行追加するだけでも、コードの変更→テスト→デプロイという開発サイクルを回す必要がある。
- **バージョン管理が困難**: 「先週のプロンプトの方が回答品質が良かった」と思っても、Gitのログから該当コミットを探す手間がかかる。
- **A/Bテストができない**: 「このプロンプトとあのプロンプト、どちらが良い回答を返すか？」を本番環境で比較するのが難しい。

TypeScriptエンジニアに馴染みのある例で言えば、これは **Feature Flag**（機能フラグ）の考え方に近いです。LaunchDarklyやUnleashのようなサービスを使って、コードのデプロイなしに機能のON/OFFを切り替えた経験はありませんか？ Langfuseのプロンプト管理は、**プロンプト版のFeature Flag** です。

### 1. Langfuse UIでプロンプトを登録する

1. Langfuse Cloudの左メニューから **「Prompts」** をクリックします。
2. **「New Prompt」** ボタンをクリックします。
3. 以下の内容で登録します。
    - **Name**: `rag-qa-prompt`
    - **Type**: `Text`
    - **Prompt**: 以下のテンプレートを入力

```text
以下のCONTEXTのみを使って、Questionに日本語で簡潔に回答してください。
CONTEXTに回答に必要な情報が含まれていない場合は、「この情報はドキュメントに含まれていません」と正直に回答してください。

CONTEXT:
{{context}}

Question:
{{question}}
```

4. **「Save」** で保存すると、このプロンプトは自動的に **バージョン1** として記録されます。

> **注意**: Langfuseのプロンプトテンプレートでは、変数を `{{variable}}` のようにダブルブレースで囲みます。LangChainの `{variable}` とは異なる記法なので注意してください。

### 2. `server.py` の修正 —— プロンプトを動的に取得する

`server.py` を修正して、ハードコードしたプロンプトの代わりにLangfuseからプロンプトを取得するようにします。

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
from langfuse.callback import CallbackHandler
from langfuse import Langfuse  # 追加

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

# --- 1. Langfuseクライアントの初期化 --- (追加)
langfuse = Langfuse()

# --- 2. プロンプトをLangfuseから動的に取得する関数 --- (追加)
def get_rag_prompt() -> ChatPromptTemplate:
    """Langfuseからプロンプトを取得し、LangChainのプロンプトに変換する"""
    langfuse_prompt = langfuse.get_prompt("rag-qa-prompt")
    # Langfuseの {{variable}} をLangChainの {variable} に変換
    template_text = langfuse_prompt.prompt
    template_text = template_text.replace("{{context}}", "{context}")
    template_text = template_text.replace("{{question}}", "{question}")
    return ChatPromptTemplate.from_template(template_text)

# ハードコードしたプロンプトを削除し、Langfuseから取得するように変更
# template = """..."""  # 削除
# rag_prompt = ChatPromptTemplate.from_template(template)  # 削除

def get_rag_response(question: str) -> str:
    langfuse_handler = CallbackHandler()

    # リクエストごとにプロンプトを取得（最新バージョンが自動的に使われる） (変更)
    rag_prompt = get_rag_prompt()

    # RAGチェーンをリクエストごとに構築 (変更)
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | rag_prompt
        | llm
    )

    response = rag_chain.invoke(
        question,
        config={"callbacks": [langfuse_handler]}
    )

    langfuse_handler.flush()
    return response.content

# --- 3. FastAPIのスキーマ定義 (Pydantic) ---
class ChatRequest(BaseModel):
    message: str
    history: List[Any]

class ChatResponse(BaseModel):
    answer: str

# --- 4. FastAPIアプリケーションの定義 ---
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

### 変更のポイント

1. **`from langfuse import Langfuse`** を追加し、`langfuse = Langfuse()` でクライアントを初期化
2. **`get_rag_prompt()`** 関数でLangfuseからプロンプトを動的に取得
3. **`rag_chain` の構築を `get_rag_response()` 内に移動**。リクエストごとに最新のプロンプトでチェーンを構築するようにしました

これにより、Langfuse UIでプロンプトを更新すれば、**コードの変更もデプロイもなしに**、次のリクエストから新しいプロンプトが使われるようになります。

### 3. プロンプトのバージョン管理を体験する

実際にプロンプトを変更して、効果を確かめてみましょう。

1. Langfuse UIで `rag-qa-prompt` を開きます。
2. **「New version」** をクリックし、プロンプトを修正します。

たとえば、回答を箇条書きで返すように指示を追加してみましょう。

```text
以下のCONTEXTのみを使って、Questionに日本語で簡潔に回答してください。
回答は箇条書き形式で整理してください。
CONTEXTに回答に必要な情報が含まれていない場合は、「この情報はドキュメントに含まれていません」と正直に回答してください。

CONTEXT:
{{context}}

Question:
{{question}}
```

3. 保存すると、**バージョン2** として記録されます。
4. サーバーを再起動することなく、`curl` でリクエストを送ると、新しいプロンプトに基づいた回答が返ってきます。

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Gemini CLIの主な機能は何ですか？", "history": []}'
```

回答が箇条書き形式に変わっていれば成功です。もし新しいプロンプトの品質に問題があれば、Langfuse UIからバージョン1に戻すこともできます。

これが**プロンプト管理**の力です。プロンプトの変更をコードのデプロイから完全に切り離すことで、素早い実験と安全なロールバックが可能になりました。

## GenAIOpsのループが回り始める

ここで、Week 3のここまでを振り返ってみましょう。

1. **第6章（観測性）**: AIの内部動作を「見える化」した
2. **第7章（評価・プロンプト管理）**: AIの品質を「測定」し、プロンプトを「コードなしで改善」できるようにした

この流れは、まさに **GenAIOps** のコアサイクルの始まりです。

```
開発 → 観測 → 評価 → 改善 → デプロイ → ...
```

従来のDevOpsサイクル（開発→テスト→デプロイ→監視）に、LLM固有の「評価」と「プロンプト改善」が加わった形です。このサイクルを回し続けることで、AIアプリケーションは継続的に進化していきます。

次章以降では、このサイクルをより堅牢にするための「Guardrails（ガードレール）」と「RAG改善」について学んでいきます。

## まとめ

1. LLMの出力は非決定的であり、**`pytest` の完全一致テストだけでは品質を測れません**。「意味的な正しさ」を基準とした評価が必要です。
2. **評価データセット** を作成し、Langfuseの **Datasets** 機能で管理することで、プロンプト変更前後の品質比較が可能になります。
3. プロンプトを **Langfuse UI で管理** することで、コードのデプロイなしにプロンプトの更新・バージョン管理・ロールバックが行えます。
4. **観測→評価→改善** のサイクルこそがGenAIOpsの核心であり、このサイクルを回す基盤がWeek 3で整いました。

これであなたは、LLMアプリケーションを「作って終わり」ではなく、「**観測し、評価し、改善し続ける**」ための武器を手に入れました。

次章では、AIアプリケーションの**安全性と品質**をさらに高めるための技術——**Guardrails（ガードレール）**について学んでいきます。

## 本章のソースコード

本章で作成したコードは、以下のGitHubブランチで確認できます。

*   [feature/week3-03-evaluation-prompt-management](https://github.com/duotaro/my-ai-bot/tree/feature/week3-03-evaluation-prompt-management)
