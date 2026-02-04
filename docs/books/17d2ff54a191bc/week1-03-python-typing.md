---
title: "Pythonでも型安全に書きたい！ (Type Hints入門)"
---

## 「動けばいい」から「堅牢なコード」へ

TypeScriptエンジニアがPythonを触り始めて一番不安になること、それは **「この変数、結局何が入ってくるの？」** という型への不透明さではないでしょうか。

```python
# 戻り値は何？ 文字列？ オブジェクト？
def get_ai_response(messages):
    return llm.invoke(messages)
```

Pythonは動的型付け言語ですが、Python 3.5以降では **Type Hints（型ヒント）** が導入されており、現代的なAIアプリ開発ではこれを使うのがデファクトスタンダードとなっています。

TypeScriptエンジニアなら、型を定義することで得られる「安心感」と「強力な入力補完」の恩恵を誰よりも知っているはずです。Pythonでもその体験を再現しましょう。

## TS vs Python：型の書き方比較

主要な型の書き方を比較してみましょう。驚くほど似ていることがわかります。

| 概念 | TypeScript | Python (Type Hints) |
| --- | --- | --- |
| 基本型 | `name: string` | `name: str` |
| 基本型 | `count: number` | `count: int` / `count: float` |
| リスト | `tags: string[]` | `tags: list[str]` |
| 辞書 (Object) | `config: Record<string, string>` | `config: dict[str, str]` |
| 戻り値なし | `void` | `None` |
| 任意 (Null許容) | `string \| null` | `Optional[str]` (要import) |

## 実践：チャットボットを型安全にリファクタリングする

これまでの `main.py` を、型ヒントを使ってリファクタリングしてみます。
ポイントは、LangChainの組み込み型（`BaseMessage`など）を活用することです。

```python:main.py
import os
from typing import List, Iterable # 型定義用のモジュール
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

load_dotenv()

# モデルの初期化 (グローバルまたはクラス内で型指定)
llm: ChatGoogleGenai = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7
)

def get_chat_response_stream(messages: List[BaseMessage]) -> Iterable:
    """
    会話履歴を受け取り、AIの応答ストリームを返す
    """
    # 型ヒントがあるため、VS Codeなどの対応エディタでは入力補完が効き、
    # 型が違うと静的解析ツール（後述）が警告を出してくれます。
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
```

### (補足) エディタで型警告が表示されない場合

上記のコードで `get_chat_response_stream("不正な値")` のように間違った型の引数を渡しても、エディタに警告が表示されない場合があります。これは、VS Codeなどのエディタが警告を出すために、**静的型チェッカー**と呼ばれるツールを必要とするためです。

多くの場合、VS CodeのPython拡張機能（Pylance）がこの役割を担いますが、設定によっては無効になっていることもあります。

VS Codeの `settings.json` に以下を追加して、型チェックを有効化（または強化）することをお勧めします。

```json:settings.json
{
  "python.analysis.typeCheckingMode": "basic"
}
```

`"basic"` の代わりに `"strict"` を指定すると、さらに厳格なチェックが行われます。この設定により、コードを書いている最中にリアルタイムで型の問題を検知できるようになります。


## TSエンジニアが感動するポイント

### 1. VS Codeでの強力な補完
`List[BaseMessage]` と定義することで、`chat_history[0].` と打った瞬間に、`content` や `type` といったプロパティが候補に出てきます。これはPython開発における最大のストレス緩和剤です。

### 2. 静的解析ツールによるチェック
TypeScriptにおける `tsc` のように、Pythonでは `mypy` というツールを使って静的に型チェックを行うことができます。

```bash
pip install mypy
mypy main.py
```

これをCI/CDに組み込むことで、「本番環境でNone（null）を参照して落ちる」という事故を未然に防ぐことができます。

## まとめ

1.  Pythonでも **Type Hints** を使えばTypeScriptに近い開発体験が得られる。
2.  `List`, `Dict`, `Optional` などの基本的なジェネリクスを覚えるだけで、コードの可読性は劇的に上がる。
3.  AIアプリのように複雑なデータ構造（メッセージのリストなど）を扱う場合、型定義は「必須」である。

1週目の学習、お疲れ様でした！
これで「PythonでGeminiを操り、文脈を理解し、堅牢なコードを書く」土台が完成しました。

来週からは、このチャットボットに**「独自の知識」**を授ける **RAG (Retrieval-Augmented Generation)** の世界に踏み込みます。お楽しみに！
