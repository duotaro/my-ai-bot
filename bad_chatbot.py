import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

def main_bad_ai():

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7
    )

    print("Bot: 起動しました。（終了するには 'exit' と入力）")

    while True:
        # ユーザー入力を受け付け
        user_input = input("You: ")
        
        if user_input.lower() == "exit":
            break


        # 3. 履歴「すべて」をAPIに投げる
        # これにより、AIは過去の会話（自分の発言含む）を「読む」ことができる
        response_stream = llm.stream([
            HumanMessage(content=user_input)
        ])

        print("Bot: ", end="")
        full_response = ""
        
        # ストリーミング表示処理
        for chunk in response_stream:
            content = chunk.content
            print(content, end="", flush=True)
            full_response += content

if __name__ == "__main__":
    main_bad_ai()