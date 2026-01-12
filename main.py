import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langfuse.langchain import CallbackHandler
from langfuse import Langfuse

# 環境変数の読み込み
load_dotenv()

def main():
    print("AIにリクエストを送信中...")

        # Geminiモデルの初期化
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7
    )

    # APIリクエストの実行
    # 通常の直接呼び出し
    response_stream = llm.stream(
        [
            {"role": "user", "content": "GenAIOpsエンジニアの役割を、3つの箇条書きで説明して。"}
        ]
    )

    # レスポンスの表示
    print("=== AIからの返答 ===")
    for chunk in response_stream:
        # 返答が届くたびに画面に出力（ストリーミング）
        print(chunk.content, end="", flush=True)
    print()

if __name__ == "__main__":
    main()
