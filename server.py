import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# -- 1. LangChainのロジック (Week1で作成したものをベース) --

# モデルの初期化
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

def get_chat_response(messages: List[BaseMessage]) -> str:
    """
    会話履歴を受け取り、AIの応答を返す（ストリーミングなしの同期版）
    """
    response = llm.invoke(messages)
    return response.content

# -- 2. FastAPIのスキーマ定義 (Pydantic) --

# NestJSのDTO (Data Transfer Object) に相当する
class ChatRequest(BaseModel):
    # ユーザーからの現在のメッセージ
    message: str
    # フロントエンドから送られてくる過去の会話履歴
    # history: List[Dict[str, str]] のように定義することもできる
    history: List[Any] 

class ChatResponse(BaseModel):
    # AIからの返答
    answer: str

# -- 3. FastAPIアプリケーションの定義 --

app = FastAPI(
    title="AI Chatbot Server",
    description="LangChainとGeminiを使ったチャットボットAPI",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Chatbot API"}

# NestJSの `@Post('/chat')` デコレータと非常によく似ている
@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    チャットリクエストを受け取り、AIの応答を返すエンドポイント
    """
    # 1. フロントエンドから送られた履歴をLangChainの形式に変換
    chat_history: List[BaseMessage] = []
    for item in request.history:
        # 'type' フィールドを見て、どのメッセージクラスを使うか判断
        if item.get("type") == "human":
            chat_history.append(HumanMessage(content=item.get("content", "")))
        elif item.get("type") == "ai":
            chat_history.append(AIMessage(content=item.get("content", "")))

    # 2. 現在のユーザーメッセージを履歴に追加
    chat_history.append(HumanMessage(content=request.message))

    # 3. LLMにリクエストを送信
    ai_response = get_chat_response(chat_history)

    # 4. Pydanticモデルに詰めて返却
    # 自動的にJSONにシリアライズされる
    return ChatResponse(answer=ai_response)

# uvicornでこのファイルを実行するためのコマンド:
# uvicorn server:app --reload
