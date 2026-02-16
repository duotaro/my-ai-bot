import os
from typing import List, Dict, Any
from typing import Optional # 追加
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
from langfuse import get_client
from input_validator import validate_input, InputValidationError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from output_filter import filter_output, OutputFilterError

# 追加 出力構造をPydanticモデルとして定義
class StructuredChatResponse(BaseModel):
    """構造化されたチャット応答"""
    answer: str = Field(description="ユーザーの質問に対する回答")
    confidence: float = Field(
        description="回答の信頼度（0.0〜1.0）",
        ge=0.0,
        le=1.0
    )
    sources: List[str] = Field(
        description="回答の根拠となったソース（ファイル名や行番号）",
        default=[]
    )
    follow_up_questions: List[str] = Field(
        description="ユーザーが次に尋ねそうな質問の候補",
        default=[],
        max_length=3
    )

# OutputParserの初期化（「第8章」で定義済み）
output_parser = PydanticOutputParser(pydantic_object=StructuredChatResponse)

# メソッド追加 検索処理でメタデータフィルタを使う
def get_rag_response_structured_with_filter(
    question: str,
    metadata_filter: Optional[Dict[str, Any]] = None
) -> StructuredChatResponse:
    """メタデータフィルタ付きでRAG検索を実行し、構造化された応答を返す"""
    langfuse_handler = CallbackHandler()

    # Retrieverの設定（フィルタ付き）
    search_kwargs = {"k": 3}
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter

    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    # プロンプトにformat instructionsを追加（week3-03と同じ形式）
    rag_prompt_template = """
以下のCONTEXTを使って、ユーザーの質問に答えてください。

CONTEXT:
{context}

QUESTION:
{question}

{format_instructions}
"""

    rag_prompt = ChatPromptTemplate.from_template(rag_prompt_template)

    # RAGチェーンを構築
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough(),
            "format_instructions": lambda _: output_parser.get_format_instructions()
        }
        | rag_prompt
        | llm
        | output_parser  # パーサーをチェーンの最後に追加
    )

    response = rag_chain.invoke(
        question,
        config={"callbacks": [langfuse_handler]}
    )

    langfuse.flush()
    return response

# 既存メソッド
def get_rag_response_structured(question: str) -> StructuredChatResponse:
    """RAGチェーンを実行し、構造化された応答を返す"""
    langfuse_handler = CallbackHandler()

    # プロンプトにformat instructionsを追加
    rag_prompt_template = """
    以下のCONTEXTを使って、ユーザーの質問に答えてください。

    CONTEXT:
    {context}

    QUESTION:
    {question}

    {format_instructions}
    """

    rag_prompt = ChatPromptTemplate.from_template(rag_prompt_template)

    # RAGチェーンを構築
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough(),
            "format_instructions": lambda _: output_parser.get_format_instructions()
        }
        | rag_prompt
        | llm
        | output_parser  # パーサーをチェーンの最後に追加
    )

    response = rag_chain.invoke(
        question,
        config={"callbacks": [langfuse_handler]}
    )

    langfuse.flush()
    return response

load_dotenv()

# --- 0. モデルの初期化とRAGコンポーネントの設定 ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# ドキュメント読み込み（複数ソース）
all_documents = []

# ドキュメント1: プロダクトドキュメント
loader_product = TextLoader("knowledge.txt")
product_docs = loader_product.load()
for doc in product_docs:
    doc.metadata.update({
        "source": "knowledge.txt",
        "category": "product",
        "language": "ja",
        "last_updated": "2024-01-15",
        "version": "1.0"
    })
all_documents.extend(product_docs)

# ドキュメント2: FAQ
loader_faq = TextLoader("faq.txt")
faq_docs = loader_faq.load()
for doc in faq_docs:
    doc.metadata.update({
        "source": "faq.txt",
        "category": "faq",
        "language": "ja",
        "last_updated": "2024-02-01"
    })
all_documents.extend(faq_docs)

# チャンク分割（メタデータは自動的に引き継がれる）
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)
chunks = text_splitter.split_documents(all_documents)

# ベクトルDB構築
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
# 【変更】metadata_filterを追加
class ChatRequest(BaseModel):
    message: str
    history: List[Any]
    metadata_filter: Optional[Dict[str, Any]] = None  # 追加

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

# 新: StructuredChatResponse を使用
@app.post("/chat", response_model=StructuredChatResponse)
def chat_endpoint(request: ChatRequest):
    # 入力バリデーション（「8章」で実装）
    try:
        validate_input(request.message)
    except InputValidationError as e:
        # バリデーションエラーをLangfuseに記録
        with langfuse.start_as_current_span(
            name="input_validation_error",
            input={"message": request.message},
            output={"error": str(e)},
            metadata={"error_type": "input_validation"},
            level="ERROR"
        ):
            pass
        langfuse.flush()
        raise HTTPException(status_code=400, detail=str(e))

    # 【変更】メタデータフィルタ付きでRAG実行（構造化出力を取得） 
    structured_response = get_rag_response_structured_with_filter(
        request.message,
        metadata_filter=request.metadata_filter
    )

    # 出力フィルタリング（「8章」で実装）
    try:
        filter_output(structured_response.answer)
    except OutputFilterError as e:
        # フィルタリングエラーをLangfuseに記録
        with langfuse.start_as_current_span(
            name="output_filter_error",
            input={"message": request.message},
            output={"answer": structured_response.answer, "error": str(e)},
            metadata={"error_type": "output_filter"},
            level="ERROR"
        ):
            pass
        langfuse.flush()
        raise HTTPException(
            status_code=500,
            detail="申し訳ございません。適切な回答を生成できませんでした。"
        )

    return structured_response