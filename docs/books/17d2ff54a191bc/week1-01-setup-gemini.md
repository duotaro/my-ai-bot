---
title: "TSエンジニアのためのPython環境構築とGemini API"
---

## はじめに：なぜTypeScriptエンジニアが今、Pythonを触るのか？

普段TypeScriptやNode.jsをメインにしているフロントエンド・バックエンドエンジニアにとって、Pythonは「機械学習の人が使う、ちょっと独特な文法の言語」というイメージかもしれません。

しかし、2025年〜2026年にかけてのAIアプリ開発において、**「GenAIOps（生成AI運用）」**という領域が急成長しています。最新のAIライブラリ（LangChainやLlamaIndex）や評価ツールは、依然としてPython版が最も進化が早く、多機能です。

「使い慣れたTypeScriptで作りたい」という気持ちをグッと抑え、まずはAI開発のメインストリームであるPythonのエコシステムに飛び込んでみましょう。意外とTypeScriptとの共通点が多く、驚くはずです。

## 1. Python環境構築： `npm` と `venv` の対比で理解する

Node.jsにおける `npm init` や `node_modules` は、Pythonではどう表現されるのでしょうか？

### 仮想環境（Virtual Environment）

Node.jsではプロジェクトごとに `node_modules` が作られますが、Pythonでは**「仮想環境（venv）」**という仕組みを使って、プロジェクトごとに独立したPython実行環境を作ります。

```bash
# プロジェクトフォルダへ移動
mkdir my-ai-bot
cd my-ai-bot

# 仮想環境（.venvフォルダ）を作成
python3 -m venv .venv

# 仮想環境を有効化（これが 'node_modules' をパスに通す作業に近い）
source .venv/bin/activate

# （参考）仮想環境を終了する場合
deactivate
```

有効化すると、ターミナルの先頭に `(.venv)` と表示されます。これで、このプロジェクト専用のライブラリインストールが可能になります。

### ライブラリ管理

`package.json` に相当するのが `requirements.txt` です。プロジェクトルート（`my-ai-bot` 直下）にこのファイルを作成し、以下を記述してください。

```text:requirements.txt
langchain==0.3.27
langchain-google-genai==2.1.12
python-dotenv==1.2.1
```

インストールは `npm install` の代わりに以下のコマンドを叩きます。

```bash
pip install -r requirements.txt
```

## 2. なぜGemini APIなのか？

本連載ではOpenAIではなく、Googleの**Gemini API**を採用します。理由はシンプルです。

1.  **圧倒的なコストパフォーマンス**: `gemini-2.5-flash` は非常に安価でありながら、`gpt-4o-mini` に匹敵する速度と性能を持っています。
2.  **無料枠の充実**: Google AI Studioから取得したAPIキーなら、一定の制限内（1分間に数回程度のリクエストなど）であれば**無料**で利用できます。「とりあえず課金設定なしで試してみたい」という開発者にとって、これほど強力な選択肢はありません。
3.  **巨大なコンテキストウィンドウ**: 大量のドキュメントを一気に読み込ませるRAG（検索拡張生成）において、Googleの巨大な入力枠はエンジニアにとって強力な武器になります。

そして、これらを直接叩くのではなく、**LangChain** というライブラリを経由して呼び出します。これにより、将来的にモデルをOpenAIやAnthropicに切り替える際も、最小限のコード修正で済むようになります。

## 準備：APIキーの取得と設定

コードを書く前に、Gemini APIを使うための「鍵」を取得し、環境変数として設定しましょう。

1.  **APIキーの取得**: [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセスし、「Create API key」からキーを発行します。
2.  **`.env` ファイルの作成**: プロジェクトのルートディレクトリ（`my-ai-bot` 直下）に `.env` という名前のファイルを作成します。
3.  **キーの記述**: `.env` ファイルを開き、以下のように記述して保存します。

```text:.env
GOOGLE_API_KEY=取得したAPIキーをここに貼り付け
```

> **セキュリティの注意**: `.env` ファイルには機密情報が含まれます。Gitなどで管理する場合は、`.gitignore` ファイルに `.env` を追記して、リポジトリに含まれないようにしてください。

## 3. 実装：Geminiを呼び出す最小構成

それでは、プロジェクトルートに `main.py` を作成し、以下のコードを書いてみましょう。TypeScriptでいう `axios` や `fetch` を使ってAPIを叩く感覚に近いです。

```python:main.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# .envからAPIキーを読み込む（process.env 的な処理）
load_dotenv()

def main():
    # モデルの初期化
    # TypeScriptのクラスインスタンス化と同じ感覚です
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7
    )

    print("AIにリクエストを送信中...")

    # ストリーミング通信での呼び出し
    # chunksを逐次処理するのは、JSのAsync Generatorに近い挙動です
    response_stream = llm.stream(
        [
            {"role": "user", "content": "GenAIOpsエンジニアの役割を、3つの箇条書きで説明して。"}
        ]
    )

    print("=== AIからの返答 ===")
    for chunk in response_stream:
        # 返答が届くたびに画面に出力（ストリーミング）
        print(chunk.content, end="", flush=True)
    print()

if __name__ == "__main__":
    main()
```

### ポイント解説

*   **`load_dotenv()`**: `.env` ファイルに記述した `GOOGLE_API_KEY` をシステム環境変数として読み込みます。
*   **`llm.stream()`**: 最近のAIアプリでは、ユーザー体験（UX）向上のために「書きかけの文章を順次表示する」ストリーミングが必須です。LangChainを使えば、ループで回すだけで簡単に実装できます。

## この章のゴール：動作確認

ファイルが準備できたら、ターミナルで以下のコマンドを実行してみましょう。

```bash
python main.py
```

### 期待される結果
ターミナルに以下のような出力が表示され、AIからの回答が少しずつ（ストリーミングで）表示されれば成功です！

```text
AIにリクエストを送信中...
=== AIからの返答 ===
1. **AIモデルの選定と評価**: 用途に合ったLLMを選び、その性能を継続的にテスト・評価する。
2. **システムの安定運用**: AIアプリケーションが安定して動作するためのインフラ構築や監視を行う。
3. **継続的な改善**: ユーザーのフィードバックやログを分析し、プロンプトやモデルを調整して精度を向上させる。
```

無事にAIと会話ができましたか？これで、Python環境でGemini APIを叩く準備が整いました。

## まとめ

1.  **venv** でプロジェクトごとの「箱」を作る。
2.  **pip** でライブラリを管理する。
3.  **LangChain** を使って **Gemini API** に接続する。

TypeScriptエンジニアにとって、Pythonの文法自体はそれほど難しくありません。むしろ、環境管理やライブラリの使い勝手の違いに戸惑うことが多いでしょう。

次章では、AIアプリ最大の難所である**「会話の記憶（コンテキスト管理）」**について、Webエンジニアお馴染みの「ステートレス」という概念をキーワードに紐解いていきます。

## 本章のソースコード

本章で作成したコードは、以下のGitHubブランチで確認できます。

*   [feature/week1-01-setup-gemini](https://github.com/duotaro/my-ai-bot/tree/feature/week1-01-setup-gemini)