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
from langfuse.langchain import CallbackHandler
from langfuse import get_client  # 追加

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
langfuse = get_client()

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

    langfuse.flush()
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