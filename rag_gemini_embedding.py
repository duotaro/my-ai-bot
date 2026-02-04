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
# 今回は `knowledge.txt` という単一のテキストファイルを読み込む
loader = TextLoader("knowledge.txt")
documents = loader.load()

# 2. ドキュメントの分割 (Splitter)
# 読み込んだドキュメントを、意味的に関連性のあるまとまり（チャンク）に分割する
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, # チャンクの最大文字数
    chunk_overlap=50, # チャンク間のオーバーラップ文字数
)
chunks = text_splitter.split_documents(documents)

print(f"ドキュメントを {len(chunks)} 個のチャンクに分割しました。")

# 3. ベクトル化とVector DBへの保存 (Vector Store)
# 分割したチャンクをベクトル化し、ChromaDBに保存する
# `npm install` のように、初回実行時にベクトルの計算と保存が行われる
vector_store = Chroma.from_documents(
    documents=chunks, 
    embedding=embeddings,
    persist_directory="./chroma_db" # ベクトルデータを保存するディレクトリ
)

print("チャンクのベクトル化とChromaDBへの保存が完了しました。")

# 4. 検索エージェントの作成 (Retriever)
# Vector DBから関連性の高いチャンクを検索するためのRetrieverを作成
retriever = vector_store.as_retriever(
    search_type="similarity", # 類似度で検索
    search_kwargs={"k": 3}      # 上位3件を取得
)

# 5. プロンプトテンプレートの定義
# RAGでは、LLMに「この情報だけを元に答えて」と指示するのが一般的
template = """
以下のCONTEXTのみを使って、Questionに回答してください。

CONTEXT:
{context}

Question:
{question}
"""
prompt = ChatPromptTemplate.from_template(template)

# 6. RAGチェーンの構築
# LangChain Expression Language (LCEL) を使って、各コンポーネントを連結する
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
)

def ask_rag(question: str) -> str:
    """
    RAGチェーンを実行して、質問に対する回答を生成する
    """
    print(f"質問: {question}")
    response = rag_chain.invoke(question)
    return response.content

if __name__ == "__main__":
    # 実行例
    answer = ask_rag("Gemini CLIの主な機能は何ですか？")
    print(f"回答:\n{answer}")

    print("-" * 20)

    # 知識を持っていないはずの質問をしてみる
    answer_no_context = ask_rag("Llama 3とは何ですか？")
    print(f"回答:\n{answer_no_context}")
