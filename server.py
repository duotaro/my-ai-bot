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