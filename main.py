import os
from typing import List, Iterable # 型定義用のモジュール
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

load_dotenv()

# モデルの初期化 (グローバルまたはクラス内で型指定)
llm: ChatGoogleGenerativeAI = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7
)

def get_chat_response_stream(messages: List[BaseMessage]) -> Iterable:
    """
    会話履歴を受け取り、AIの応答ストリームを返す
    """
    # ここで引数が List[BaseMessage] であることを明示しているため、
    # 呼び出し側で変な値を渡すとエディタが警告してくれます。
    return llm.stream(messages)

def main() -> None:
    # TypeScriptの 'const chatHistory: BaseMessage[] = []' と同等
    chat_history: List[BaseMessage] = []

    print("Bot: 起動しました。（型安全Ver.）")

    while True:
        user_input: str = input("You: ")
        
        if user_input.lower() == "exit":
            break

        chat_history.append(HumanMessage(content=user_input))

        # 関数のシグネチャが明確なので、戻り値の扱いも迷わない
        response_stream = get_chat_response_stream(chat_history)

        print("Bot: ", end="")
        full_response: str = ""
        
        for chunk in response_stream:
            content: str = chunk.content
            print(content, end="", flush=True)
            full_response += content
        
        print()
        chat_history.append(AIMessage(content=full_response))

if __name__ == "__main__":
    main()