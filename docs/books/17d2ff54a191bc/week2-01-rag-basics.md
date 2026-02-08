---
title: "第4章: AIに「ドキュメント」を読ませる技術 (RAG入門)"
---

## Week 1のおさらいと、LLMの限界

Week 1では、PythonでGeminiを操り、記憶（コンテキスト）を持ったチャットボットを構築しました。しかし、このボットには大きな限界があります。それは **「モデルが元々持っている知識しか話せない」** ということです。

LLMは、その学習データに含まれていない情報（最新のニュース、社内ドキュメント、特定の専門知識）については答えることができません。知らないことを無理に答えようとして、もっともらしい嘘（**ハルシネーション**）をついてしまうことさえあります。

この問題を解決し、AIに「外部の知識」を与えて賢くする技術が、今回学ぶ **RAG (Retrieval-Augmented Generation)** です。日本語では「検索拡張生成」と訳されます。

この概念は「オープンブック試験（教科書持ち込み可の試験）」に例えると分かりやすいでしょう。LLMが自身の記憶だけを頼りに回答するのが「暗記だけの試験」だとすれば、RAGは「**特定の参考資料（ドキュメント）を参照しながら回答する**」ようなものです。

## Vector Databaseとは何か？「意味のデータベース」という発想

RAGの頭脳となるのが **Vector Database（ベクトルデータベース）** です。

データベースといえばSQL (MySQL, PostgreSQL) やNoSQL (MongoDB, DynamoDB) を思い浮かべる方が多いでしょう。これらは基本的に「キーワード」や「インデックス」に基づいて、完全に一致するデータを高速に検索するのが得意です。

```sql
SELECT * FROM users WHERE name = 'Taro Yamada';
```

一方、Vector DBは **「意味の近さ」** で検索します。

例えば、「悲しくて青い気分の時に聴くジャズ」という曖昧な文章で検索した時に、`genre = 'blues'` や `mood = 'sad'` といったタグを持つ音楽を推薦してくれるようなデータベースです。これは、キーワード検索では不可能です。

### なぜ「意味」を検索できるのか？

Vector DBの裏側では、**Embedding（エンベディング、埋め込み）** という技術が動いています。

1.  **テキストを「意味のベクトル」に変換**: `GoogleGenerativeAIEmbeddings` のようなEmbeddingモデルが、文章や単語を「意味」を表現する数値の配列（ベクトル）に変換します。このベクトルは、意味空間における「住所」のようなものだと考えればよいでしょう。例えば、「犬」と「ワンちゃん」は非常に近い住所に、「犬」と「コンピュータ」は遠い住所にマッピングされます。
2.  **ベクトル間の距離を計算**: ユーザーからの質問も同様にベクトルに変換し、データベースに保存されている全データのベクトルと「距離」を比較します。この距離が最も近いものが、「意味的に最も関連性が高いデータ」として返されます。

エンジニアに馴染みのある言葉で言えば、これは「**超高性能なファジー検索**」です。単なる文字列のマッチングではなく、文脈やニュアンスを理解した上で、最も関連性の高い情報を探し出してくれるのです。

## 実践：ChromaDBでRAGを実装する

今回は、Vector DBの中でも特に手軽に始められる `ChromaDB` を使ってみましょう。ChromaDBは、`SQLite` のようにサーバーレスで、ローカルファイルとしてVector DBを構築できるのが特徴で、すぐに試すことができます。

### 1. 準備：ライブラリと知識ファイルの作成

まず、RAGに必要なライブラリを `requirements.txt` に追記しましょう。

```text:requirements.txt
# ... 既存のライブラリ ...
# 以下追加するライブラリ
langchain-community>=0.3.0
langchain-chroma>=0.2.0
fastapi==0.112.0
uvicorn[standard]==0.30.5
```

ターミナルで `pip install -r requirements.txt` を実行するのを忘れないでくださいね。

次に、AIに読ませたい知識源として、プロジェクトルートに `knowledge.txt` というファイルを作成します。

```text:knowledge.txt
Gemini CLIは、Googleによって開発されたコマンドラインインターフェース（CLI）ツールです。開発者は、自身のターミナルから直接、Googleの最新の生成AIモデルであるGeminiファミリーと対話できます。

主な機能には、コード生成、質問応答、テキスト要約、複数ファイルにまたがるコードベースの理解、そしてシェルのように使えるエージェント機能などがあります。

このツールは、特にソフトウェア開発者やデータサイエンティストが、開発ワークフローを離れることなく、AIの支援を受けられるように設計されています。
```

### 2. RAG実装スクリプトの作成

`rag_gemini_embedding.py` という新しいファイルを作成し、以下のコードを記述します。これがRAG処理の全体像です。

```python:rag_gemini_embedding.py
import os
from typing import List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma

load_dotenv()

# 0. モデルの初期化
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# 1. ドキュメントの読み込み (Loader)
loader = TextLoader("knowledge.txt")
documents = loader.load()

# 2. ドキュメントの分割 (Splitter)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)
chunks = text_splitter.split_documents(documents)
print(f"ドキュメントを {len(chunks)} 個のチャンクに分割しました。")

# 3. ベクトル化とVector DBへの保存 (Vector Store)
vector_store = Chroma.from_documents(
    documents=chunks, 
    embedding=embeddings,
    persist_directory="./chroma_db" 
)
print("チャンクのベクトル化とChromaDBへの保存が完了しました。")

# 4. 検索エージェントの作成 (Retriever)
retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# 5. プロンプトテンプレートの定義
template = """
以下のCONTEXTのみを使って、Questionに回答してください。

CONTEXT:
{context}

Question:
{question}
"""
prompt = ChatPromptTemplate.from_template(template)

# 6. RAGチェーンの構築
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
)

def ask_rag(question: str) -> str:
    print(f"質問: {question}")
    response = rag_chain.invoke(question)
    return response.content

if __name__ == "__main__":
    answer = ask_rag("Gemini CLIの主な機能は何ですか？")
    print(f"回答:\n{answer}")
    
    print("-" * 20)

    # 知識を持っていないはずの質問をしてみる
    answer_no_context = ask_rag("Llama 3とは何ですか？")
    print(f"回答:\n{answer_no_context}")
```

### 3. 実行と解説

ターミナルで、**rag_gemini_embedding.py** を実行してみましょう。

```bash
python rag_gemini_embedding.py
```

#### 3.1 実行結果：エラーが発生する

環境によっては、以下のようなエラーが発生します。（エラーメッセージは多少異なる場合があります）

```text
PermissionDenied: 403 The embedding model `models/embedding-001` requires billing to be enabled.
```

#### 3.2 なぜこのエラーが出るのか？

RAG（Retrieval-Augmented Generation）では、次の処理が必須になります。

1. ドキュメントを **Embedding（数値ベクトル）** に変換
2. ベクトル検索で関連文書を取得
3. LLM に文書＋質問を渡して生成

このうち、

* Gemini（**LLM**） → 無料枠あり
* **Gemini Embedding（`models/embedding-001`） → 無料枠なし**

という仕様になっています。つまり、**RAG は LLM だけでは動かない**という事実を、このエラーは示しています。



#### 3.3 ここからの進め方

ここから先は、次の2通りの進め方があります。

##### ルートA：Gemini Embedding を使い続ける（課金が必要）

* Google Cloud で Billing を有効化
* Generative Language API（Embedding）を有効化
* `models/embedding-001` のクォータを設定

この場合は、以下のファイルをそのまま使用します。

```text
rag_gemini_embedding.py
```

```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001"
)
```

※ 本記事では、このルートの詳細解説は行いません。

##### ルートB：ローカル Embedding に切り替える（本記事で採用）

RAG の本質は **「検索のためのベクトルを作れること」** であり、Embedding が Gemini である必要はありません。そこで本記事では、**無料・ローカルで完結する Embedding モデル**に切り替えて先へ進みます。

#### 3.4 ローカル Embedding 版で再実行（以降はこちらを使用）

次に、ローカル Embedding を使うファイルを作成します。このファイルでは、Embedding を以下のように差し替えています。

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
```

このとき、ローカル Embedding では **追加の Python 依存ライブラリ** が必要になります。

`HuggingFaceEmbeddings` は内部で `sentence-transformers` を利用しているため、
これがインストールされていない場合、次のようなエラーが発生します。

```text
ModuleNotFoundError: No module named 'sentence_transformers'
````

そのため、`requirements.txt` に`sentence-transformers` を追記します。
`requirements.txt`を次のように修正してください。

```txt
# 以下追加するライブラリ
langchain-community>=0.3.0
langchain-chroma>=0.2.0
fastapi==0.112.0
uvicorn[standard]==0.30.5
sentence-transformers>=2.6.0 # ←追加
```
追加したら、ターミナルで`pip install -r requirements.txt`を実行しましょう。

依存関係を追加したら、`python rag_local_embedding.py` を実行してください。
エラーが発生せず、RAG が正常に動作します。

```bash
python rag_local_embedding.py
```


### 3.5 実行成功：RAG が動作する

初回実行時は、Embeddingモデルが `knowledge.txt` の内容をベクトルに変換するため少し時間がかかります。実行が終わると、プロジェクト内に `chroma_db` というディレクトリが作成されているはずです。これがVector DBの実体になります。

これで、

* RAG には **Embedding が必須**
* Embedding は **LLM とは別のコスト設計が必要**
* 無料で試すなら **ローカル Embedding が現実的**

という構造を、実行結果として確認できました。

**実行結果の例：**
```text
ドキュメントを 1 個のチャンクに分割しました。
チャンクのベクトル化とChromaDBへの保存が完了しました。
質問: Gemini CLIの主な機能は何ですか？
回答:
Gemini CLIの主な機能は以下の通りです。

*   コード生成
*   質問応答
*   テキスト要約
*   複数ファイルにまたがるコードベースの理解
*   シェルのように使えるエージェント機能
--------------------
質問: Llama 3とは何ですか？
回答:
提示されたCONTEXTにはLlama 3に関する情報はありません。

CONTEXTにはGemini CLIとGeminiファミリーについて記述されています。
```

注目すべきは2つ目の質問です。プロンプトで「CONTEXTのみを使って」と強く指示したため、LLMは知らない情報に対して正直に「分からない」と答えています。これにより、ハルシネーションを大幅に抑制できるのです。

#### コード解説

- **Loader**: `TextLoader` がテキストファイルを読み込みます。他にもPDF用 (`PyPDFLoader`) やWebページ用 (`WebBaseLoader`) などがあります。
- **Splitter**: `RecursiveCharacterTextSplitter` がドキュメントを適切なサイズに分割します。LLMが一度に読み込める文字数（コンテキスト長）には限りがあり、また、検索精度を高めるためにも、文章を意味のある塊（チャンク）に分割する工程は非常に重要です。
- **Vector Store**: `Chroma.from_documents` が、分割されたチャンクをEmbeddingモデル (`GoogleGenerativeAIEmbeddings`) を使ってベクトル化し、`ChromaDB` に保存します。この処理がRAGの「インデックス作成」に相当します。
- **Retriever**: `as_retriever()` で作成された検索機です。ユーザーの質問をベクトル化し、DB内から最も意味の近いチャンクを `k` 個（今回は3個）取ってきます。
- **RAG Chain (LCEL)**: LangChain Expression Language (LCEL) という記法で、一連の処理を `|` パイプで繋いで定義しています。`{ "context": retriever, "question": RunnablePassthrough() }` の部分がRAGの肝です。ユーザーの質問 (`RunnablePassthrough()`) をそのまま `question` として後段に渡すと同時に、その質問を `retriever` に投げて取得したコンテキストを `context` として渡しています。

## まとめ

1.  LLMの知識を外部ドキュメントで拡張する技術が **RAG** です。
2.  RAGの心臓部である **Vector Database** は、「キーワード」ではなく「意味の近さ」で情報を検索します。
3.  **LangChain** を使えば、`Loader`→`Splitter`→`Vector Store`→`Retriever` という一連のRAGパイプラインを宣言的に構築できます。

これで、あなたのAIはただの物知りではなく、**特定の知識体系に基づいた回答ができる専門家**に進化しました。

次章では、このRAG機能を持ったチャットボットを、いよいよWeb APIとして公開します。使い慣れたExpress/NestJSと比較しながら、PythonのモダンなWebフレームワーク **FastAPI** の世界に飛び込んでいきましょう。


## 本章のソースコード

本章で作成したコードは、以下のGitHubブランチで確認できます。

*   [feature/week2-01-rag-basics](https://github.com/duotaro/my-ai-bot/tree/feature/week2-01-rag-basics)