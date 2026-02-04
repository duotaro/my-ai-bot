## はじめに (Introduction)

長年、TypeScript (Node.js/React) を中心にWeb開発をしてきたフルスタックエンジニアの私が、2026年に向けて新たな領域へキャリアの舵を切ることにしました。

その行き先は、**「GenAIOps (Generative AI Operations)」** です。

「ChatGPT APIを使えば、誰でも簡単にAIアプリが作れる」と言われる昨今ですが、それを**「業務レベル」で安定稼働させる**となると、話は全く別です。
ハルシネーション（嘘）の制御、トークンコストの管理、レスポンス速度の最適化……。これら「非機能要件」の壁を乗り越え、AIをシステムに統合するエンジニアリング能力が、今まさに求められています。

### 1ヶ月集中ロードマップの開始

「概念はわかった。で、コードは書けるのか？」
そう自問した私は、入社までの1ヶ月間、GenAIOpsエンジニアとして独り立ちするための集中ロードマップを走ることにしました。

**今週のテーマ (Week 1):**
**「いきなりRAGやWebアプリを作る前に、CLI（黒い画面）でLLMの"生の挙動"を理解する」**

普段TypeScriptを書いている私にとって、Pythonのエコシステムは「似ているようで違う」未知の領域です。
本記事では、Python環境構築のハマりどころから、OpenAI APIを使って**「記憶を持ったチャットボット」**を実装するまでの過程を、TypeScriptエンジニアの視点で記録します。

* **APIを叩くだけでは、なぜ会話が成立しないのか？**
* **「ステートレス」なLLMに、どうやって文脈を持たせるのか？**


## 開発環境の構築：PythonでAIを扱うための「お作法」

GenAIアプリ開発において、Pythonは事実上の標準語です。
文法自体はシンプルですが、プロジェクトごとにライブラリのバージョンを管理する**「仮想環境（Virtual Environment）」**の概念だけは、最初にしっかり理解しておく必要があります。これを行わないと、将来的にライブラリ同士が競合し、環境が壊れる原因になります。

ここでは、最も標準的でシンプルな構成を作ります。

### Step 1: プロジェクトと仮想環境の作成

適当なフォルダを作成し、その中にPythonの仮想環境を作ります。
仮想環境とは、そのプロジェクト専用の「箱」を用意するイメージです。

```bash
# プロジェクトフォルダの作成
mkdir my-ai-bot
cd my-ai-bot

# 仮想環境（.venvという名前のフォルダ）を作成
# Mac/Linux
python3 -m venv .venv
# Windows
python -m venv .venv

```

このコマンドを実行すると、フォルダ内に `.venv` というディレクトリが生成されます。ここにこれからインストールするライブラリが全て格納されます。

### Step 2: 仮想環境の有効化 (Activate)

箱を作っただけでは意味がありません。「今からこの箱を使うぞ」という宣言（有効化）が必要です。

```bash
# Mac/Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

```

ターミナルの行頭に `(.venv)` と表示されれば成功です。これで、システム全体のPython環境を汚さずに開発する準備が整いました。

### Step 3: 必須ライブラリのインストール

GenAI開発の「三種の神器」とも言えるライブラリをインストールします。

* **`openai`**: OpenAI公式のSDK。これがないと始まりません。
* **`python-dotenv`**: APIキーをコードに直書きしないためのセキュリティ用ライブラリ。

```bash
pip install openai python-dotenv

```

### Step 4: APIキーの管理 (.env)

初心者が一番やりがちなミスが、コードの中に `api_key = "sk-..."` と書いてしまい、そのままGitHubにアップロードしてキー流出・不正利用される事故です。
これを防ぐため、環境変数ファイル `.env` を作成して管理します。

1. プロジェクト直下に `.env` という名前のファイルを作成。
2. 以下のようにキーを記述（スペースやクォートは不要です）。

```text
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx

```

3. （Git管理する場合） `.gitignore` ファイルを作成し、`.env` を記述してコミット対象から外す。

これで、安全に開発を進める土台（Base）が完成しました。


環境構築で土台ができました。ここからは実際にコードを書いていきます。

最初のステップは、**「PythonからOpenAI APIにリクエストを投げ、返答を受け取る」という最小構成の実装です。
ここで重要なのは、ただ動かすだけでなく、APIが何を要求し、何を返してきているのか、そのデータ構造**を理解することです。

---

## 初めてのAPIコールと「メッセージ構造」の理解

エディタ（VS Code等）で、プロジェクトフォルダに `main.py` というファイルを作成します。これが今回のアプリケーションのエントリーポイントになります。

### 最小構成のコード (main.py)

まずは、対話ループなどは考えず、**「一言話しかけて、一言返してもらう」**だけのシンプルなコードを書きます。

```python
import os
from dotenv import load_dotenv
from openai import OpenAI

# .envファイルから環境変数を読み込む
load_dotenv()

# クライアントの初期化 (API Keyは環境変数から自動で読まれる)
client = OpenAI()

def main():
    print("AIにリクエストを送信中...")

    # APIリクエストの実行
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # コスパ最強のモデル
        messages=[
            {"role": "user", "content": "GenAIOpsエンジニアってどんな仕事？一言で教えて。"}
        ]
    )

    # レスポンスの表示
    print("=== AIからの返答 ===")
    print(response.choices[0].message.content)

if __name__ == "__main__":
    main()

```

### 実行方法

ターミナルで以下のコマンドを叩きます。

```bash
python main.py

```

数秒後、AIからの回答が表示されれば成功です。
これが、あなたの初めての「GenAIアプリ」です。

### 【重要】エンジニアが理解すべき「メッセージ構造」

このコードの肝は、`messages` パラメータにあります。
OpenAIのChat API（GPT-3.5/4系）は、単なるテキストではなく、**「メッセージオブジェクトのリスト（配列）」**を入力として受け取ります。

```python
messages=[
    {"role": "user", "content": "..."}
]

```

ここで登場する **`role`（役割）** は、GenAIOpsの基本中の基本となる概念です。主に3つの役割があります。

| Role | 役割 | 説明 |
| --- | --- | --- |
| **system** | 設定・指示 | 「あなたは優秀なエンジニアです」等のキャラ設定や、制約事項を与える。（※今回は未設定） |
| **user** | ユーザー | 人間からの入力。 |
| **assistant** | AI | AIからの出力。 |

この構造は、HTTPリクエストのヘッダー/ボディのようなものです。
今は `user` からの一方的な投げかけだけですが、このリストに `system` や `assistant` のメッセージを積み上げていくことで、複雑な会話が成立します。


GenAIOpsエンジニアとして、最も基本的かつ重要な概念である**「ステートレス性（Statelessness）」**について解説し、コードを修正するセクションです。

---

## AIは記憶喪失？ 「文脈」の実装

ここまででAPIを叩くことに成功しました。次はこれを対話形式（チャットボット）にしてみましょう。
単純に考えれば、「ユーザー入力を `while` ループで受け取って、APIに投げ続ければいい」と思うかもしれません。

しかし、やってみると**奇妙な現象**が起きます。

### 失敗例：ただループさせただけの場合

```text
You: 私の名前は田中です。覚えてね。
AI: わかりました、田中さんですね。覚えました。

You: 私の名前は何ですか？
AI: 申し訳ありませんが、あなたの名前を知りません。

```

AIは平気な顔で記憶喪失になります。
直前に「覚えました」と言ったのに、なぜでしょうか？

### 技術的背景：LLMは「完全なステートレス」である

Webエンジニアの方なら、**「HTTPはステートレスなプロトコルである」**という話をご存知でしょう。OpenAI APIも全く同じです。

APIサーバー側（OpenAI）は、**「あなたとの過去の会話」を一切保存していません。**
彼らにとって、1回目のリクエストと2回目のリクエストは、完全に独立した赤の他人のリクエストなのです。

したがって、会話を成立させるためには、**クライアント側（私たちのPythonコード）が会話の全履歴を管理し、毎回のリクエストで「過去のやり取り全て」をセットにして送信する**必要があります。

これを**「コンテキスト（文脈）の注入」**と呼びます。

### 修正コード：記憶を持たせる (main.py)

では、コードを修正して「記憶」を実装しましょう。
ポイントは、`messages` リストを関数の外に出し、会話のたびに追記（`append`）していくことです。

```python
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

def main():
    # 1. 会話履歴（コンテキスト）を保持するリスト
    # ここに「system」ロールを入れて、AIのキャラ設定を行います
    chat_history = [
        {"role": "system", "content": "あなたは優秀なSREエンジニアです。技術的な質問に簡潔に答えてください。"}
    ]

    print("Bot: 起動しました。（終了するには 'exit' と入力）")

    while True:
        user_input = input("You: ")
        
        if user_input.lower() == "exit":
            break

        # 2. ユーザーの発言を履歴に追加
        chat_history.append({"role": "user", "content": user_input})

        # 3. 履歴「すべて」をAPIに投げる
        # これにより、AIは過去の会話（自分の発言含む）を「読む」ことができる
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_history 
        )

        bot_reply = response.choices[0].message.content
        print(f"Bot: {bot_reply}")

        # 4. AIの返答も履歴に追加
        # これを忘れると、AIは「自分がさっき何を言ったか」を忘れてしまう
        chat_history.append({"role": "assistant", "content": bot_reply})

if __name__ == "__main__":
    main()

```

### 実行結果

```text
You: 私の名前は田中です。
Bot: 承知しました、田中さん。SREに関する質問があればどうぞ。

You: 私の名前は？
Bot: 田中さんですね。

```

これでようやく、AIに「記憶」が宿りました。
コード上では単にリスト（配列）に辞書を追加しているだけですが、これが**LLMアプリ開発における「状態管理」の基本形**です。

### GenAIOps視点での気づき：コストの構造

この仕組みを実装して気づくべき恐ろしい事実があります。
それは、**「会話が長くなればなるほど、送信する文字数（トークン数）が雪だるま式に増えていく」**ということです。

* 1往復目：送信量 少
* 10往復目：送信量 大（過去9回分の会話も全部送っているから！）

APIの料金は「入力トークン数」にも課金されます。つまり、**長く話せば話すほど、1回の発言にかかるコストは高くなっていきます。**
また、モデルには「最大トークン数（コンテキストウィンドウ）」という記憶容量の限界があるため、無限に話し続けるといつかエラー（`context_length_exceeded`）になります。

実務レベルのアプリでは、

* 「古い会話から削除する」
* 「過去の会話を要約して圧縮する」

といった**メモリ管理戦略**が必要になります。これがGenAIOpsエンジニアの腕の見せ所です。

---

## 6. Step 3: TypeScriptエンジニアの意地「型ヒント」

Week 1の総仕上げです。「動けばいい」から「堅牢に書く」へ。
ここまででチャットボットは完成しました。しかし、普段TypeScriptを書いているあなたなら、先ほどのコードを見て少し**ムズムズ**しているのではないでしょうか？

```python
# 何が入ってくるかわからない... まるで 'any' だ...
def function(data):
    pass

```

Pythonは動的型付け言語ですが、Python 3.5以降では**Type Hints（型ヒント）**という機能が導入されています。
これはTypeScriptと同様に、**「実行時には影響しないが、エディタ（VS Code等）での静的解析や補完を強力にする」**ための仕組みです。

これを使わない手はありません。

### TS vs Python：型の書き方比較

| 概念 | TypeScript | Python |
| --- | --- | --- |
| 変数 | `const name: string = "Bob"` | `name: str = "Bob"` |
| 関数 | `(a: number): string => ...` | `def func(a: int) -> str:` |
| 配列 | `string[]` または `Array<string>` | `list[str]` (3.9以降) |
| 辞書 (Obj) | `Record<string, string>` | `dict[str, str]` |
| 任意 (Null) | `string | null` | `Optional[str]` |

### コードを「型安全」にリファクタリングする

先ほどのコードに型ヒントを導入し、関数に切り出して構造化してみましょう。
これだけで、コードの可読性は劇的に向上します。

```python
import os
from typing import List, Dict # 型定義用のモジュール
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# TypeScriptの 'type Message = { ... }' に相当する型エイリアス
# 辞書のキーと値がともに文字列であることを明示
Message = Dict[str, str]

def get_ai_response(messages: List[Message]) -> str:
    """
    OpenAI APIを叩いて返答を取得する関数
    Args:
        messages: 会話履歴のリスト
    Returns:
        AIからの応答テキスト
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    # None対策：万が一contentが空の場合は空文字を返す
    return response.choices[0].message.content or ""

def main() -> None:
    chat_history: List[Message] = [
        {"role": "system", "content": "あなたは優秀なエンジニアです。"}
    ]

    print("Bot: 起動しました。（型安全Ver.）")

    while True:
        user_input: str = input("You: ")
        if user_input.lower() == "exit":
            break

        chat_history.append({"role": "user", "content": user_input})

        # ここで引数の型が違えば、VS Codeが赤線で警告してくれる！
        bot_reply = get_ai_response(chat_history)
        
        print(f"Bot: {bot_reply}")
        chat_history.append({"role": "assistant", "content": bot_reply})

if __name__ == "__main__":
    main()

```

### 導入のメリット

こう書くことで、例えば `get_ai_response` 関数に間違って文字列だけを渡そうとすると、エディタ上で即座にエラー（警告）が出ます。
「実行して初めてエラーで落ちる」というPython特有のストレスを、TypeScriptに近い開発体験まで引き上げることができます。

---

## 7. 学びのまとめ：GenAIOpsの入り口に立って

1週目のロードマップ、お疲れ様でした。
「黒い画面でチャットするだけ」の地味な成果物に見えるかもしれませんが、あなたは既にGenAIOpsの核心部分に触れています。

1. **環境構築:** Python特有の仮想環境とパッケージ管理（`pip` / `.venv`）を理解した。
2. **APIの挙動:** LLMは**ステートレス（記憶喪失）であり、エンジニアが文脈（コンテキスト）を管理**しなければ会話が成立しないことを痛感した。
3. **コスト感覚:** 会話履歴が増える＝送信トークンが増える＝**課金が増える**という構造を肌で感じた。
4. **型安全性:** Pythonでも型ヒントを使えば、堅牢なコードが書けることを知った。

これらは、流行りのフレームワークを使っているだけでは見落としてしまう「基礎体力」です。

### Next Step: Week 2の予告

次週はいよいよ、このチャットボットをWebの世界に繋ぎます。
テーマは**「RAG（検索拡張生成）とAPIサーバー構築」**です。

* AIに社内ドキュメントや独自データを読み込ませる（RAG）。
* **FastAPI** を使って、PythonでWeb APIサーバーを立てる。
* Postmanやフロントエンドから呼び出せるようにする。

CLIの「黒い画面」から飛び出し、実用的なアプリケーションへの進化を目指しましょう。
