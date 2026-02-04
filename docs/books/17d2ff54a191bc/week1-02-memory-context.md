---
title: "ステートレスなAIに「記憶」を実装する"
---

## AIはなぜ「さっきの話」を忘れるのか？

第1章では、固定の質問を1回だけ投げるシンプルなプログラムを作りました。
もしこれを拡張して、`input()` でユーザー入力を受け付けるループ処理にしたとしても、AIは会話を続けることができません。

実際に、`ChatGoogleGenerativeAI` を使いながらも、記憶を持たせることに失敗したプログラムを見てみましょう。
このコードは、ユーザーからの入力があるたびに、AIとのやり取りを最初からやり直してしまいます。

```python:bad_chatbot.py
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
        response_stream = llm.stream(HumanMessage(content=user_input))

        print("Bot: ", end="")
        full_response = ""
        
        # ストリーミング表示処理
        for chunk in response_stream:
            content = chunk.content
            print(content, end="", flush=True)
            full_response += content

if __name__ == "__main__":
    main_bad_ai()
```

このプログラム (`bad_chatbot.py`) を実行して、AIに名前を覚えさせようとしても、次の質問では忘れられてしまいます。

```bash
python bad_chatbot.py
```

例えば、以下のようなやり取りになってしまうのです。

```text
You: 私の名前は田中です。覚えておいて。
Bot: 承知いたしました。何かご質問はありますか、田中さん？

You: 私の名前は何ですか？
Bot: 申し訳ありません、私にはあなたの名前を知る方法がありません。
```

Webエンジニアの皆さんなら、この挙動にピンとくるはずです。そう、 **LLM（大規模言語モデル）のAPIは、HTTPプロトコルと同様に「完全なステートレス」** なのです。

サーバー側（GoogleやOpenAI）はセッション状態を保持しません。彼らにとって、あなたの1回目のリクエストと2回目のリクエストは、全く無関係な赤の他人からのアクセスと同じです。

## 「文脈（Context）」の注入

会話を成立させるための唯一の方法は、 **「クライアント側（私たちのPythonコード）が会話の全履歴を管理し、リクエストのたびに過去のやり取りを全てセットにして送信する」** ことです。

これを**コンテキストの注入**と呼びます。

### LangChainにおけるメッセージ管理

LangChainでは、この会話履歴を管理するために専用のメッセージクラスを提供しています。

*   **`HumanMessage`**: ユーザー（人間）の発言
*   **`AIMessage`**: AIモデルからの返答
*   **`SystemMessage`**: AIへのキャラ設定や指示（今回はまだ使いませんが、重要です）

これらをリスト（配列）に格納し、雪だるま式に増やしながらAPIに投げ続けるのが、チャットボットの基本的な仕組みです。

## 実装：記憶を持ったCLIチャットボット

では、`main.py` を修正して、対話ができるようにループ処理と履歴管理を追加しましょう。

```python:main.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

def main():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7
    )

    # 1. 会話履歴を保持するリスト（ここが「記憶」の実体）
    chat_history = []

    print("Bot: 起動しました。（終了するには 'exit' と入力）")

    while True:
        # ユーザー入力を受け付け
        user_input = input("You: ")
        
        if user_input.lower() == "exit":
            break

        # 2. ユーザーの発言を履歴に追加
        chat_history.append(HumanMessage(content=user_input))

        # 3. 履歴「すべて」をAPIに投げる
        # これにより、AIは過去の会話（自分の発言含む）を「読む」ことができる
        response_stream = llm.stream(chat_history)

        print("Bot: ", end="")
        full_response = ""
        
        # ストリーミング表示処理
        for chunk in response_stream:
            content = chunk.content
            print(content, end="", flush=True)
            full_response += content
        
        print() # 改行

        # 4. AIの返答も履歴に追加
        # これを忘れると、AIは「自分がさっき何を言ったか」を忘れてしまう
        chat_history.append(AIMessage(content=full_response))

if __name__ == "__main__":
    main()
```

### 実行してみよう

```bash
python main.py
```

このコードを実行すると、AIはあなたの名前を覚え、文脈を踏まえた回答をしてくれるようになります。

```text
You: 私の名前は田中です。覚えておいて。
Bot: 承知いたしました、田中様。お名前を教えていただきありがとうございます。

You:  私の名前は何ですか？
Bot:  はい、田中様でいらっしゃいますね。
```

最初の会話で提示した名前を覚えているのは、`chat_history` に前の会話（名前）が含まれている状態でリクエストが送られているからです。

## コスト構造への気づき

この仕組みを実装したエンジニアが次に気づくべきは、**「コストの構造」**です。

会話が長く続けば続くほど、APIに送信する `chat_history` のリストは長くなります。
LLMのAPI課金は通常「入力トークン数 ＋ 出力トークン数」で計算されます。つまり、**「長く話せば話すほど、たった一言の "はい" を送るだけでも、過去の全履歴分のコストがかかる」**ということです。

実務レベルのアプリでは、無限に増え続ける履歴をそのまま送ることはしません。「古い会話を消す」「要約して圧縮する」といった**メモリ管理戦略**が必要になりますが、それはまた別の機会に。

まずは「AIアプリ＝ステートレスAPIへの履歴全送付」という基本原理を体得してください。

## まとめ

1.  **LLMのAPIはステートレス**であり、HTTPプロトコルと同様にセッション状態を保持しない。
2.  会話を成立させるためには、**クライアント側で会話の全履歴を管理し、リクエストのたびに全てをAPIに送信する**「コンテキストの注入」が必要。
3.  LangChainでは `HumanMessage`、`AIMessage`、`SystemMessage` といったクラスを使って会話履歴を効果的に管理できる。
4.  会話履歴が長くなると、APIへの送信データ量が増え、それに伴い**API利用コストが増加する**という課題がある。

次章では、Pythonの型ヒントについて深く掘り下げ、大規模なAIアプリケーション開発におけるコードの可読性と保守性の向上について学びます。

## 本章のソースコード

本章で作成したコードは、以下のGitHubブランチで確認できます。

*   [feature/week1-02-memory-context](https://github.com/duotaro/my-ai-bot/tree/feature/week1-02-memory-context)