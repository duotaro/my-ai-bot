# 作って終わりにしない生成AIアプリ開発 〜GenAIOps実践ロードマップ〜

Python・Gemini・LangChain・FastAPIを使って生成AIアプリを構築し、観測・評価・改善・デプロイまでを一気通貫で学ぶ実践ガイドの**サンプルコードリポジトリ**です。

本連載はZennで公開しています。

## このリポジトリについて

本リポジトリは、連載記事の各章に対応したサンプルコードを動作確認するためのものです。
**章ごとにブランチが用意されており**、読み進めている章のブランチに切り替えることで、その章のコードをそのまま実行できます。

### ブランチ構成

| ブランチ | 対応章 |
|---|---|
| `feature/week1-01-setup-gemini` | 第1章: Python環境構築とGemini APIの最小構成 |
| `feature/week1-02-memory-context` | 第2章: 会話履歴の管理とコンテキストウィンドウ |
| `feature/week1-03-python-typing` | 第3章: 型ヒントとPydanticによる堅牢なコード |
| `feature/week2-01-rag-basics` | 第4章: AIに「ドキュメント」を読ませる技術（RAG入門） |
| `feature/week2-02-fastapi-server` | 第5章: FastAPIでRAGをAPIサーバー化する |
| `feature/week3-01-docker-container` | 第6章: Dockerコンテナ化 |
| `feature/week3-02-observability-langfuse` | 第7章: LangFuseでAIの挙動を観測する |
| `feature/week3-03-evaluation-prompt-management` | 第8章: プロンプト評価と管理 |
| `feature/week4-01-deploy-and-ui` | 第9章: Cloud Runへのデプロイ |
| `feature/week4-02-summary-and-next-steps` | 第10章: まとめと次のステップ |

## 環境構築

### Python仮想環境のセットアップ

```bash
# プロジェクトフォルダへ移動
mkdir my-ai-bot
cd my-ai-bot

# 仮想環境（.venvフォルダ）を作成
python3 -m venv .venv

# 仮想環境を有効化
source .venv/bin/activate

# 依存ライブラリをインストール
pip install -r requirements.txt

# （参考）仮想環境を終了する場合
deactivate
```

### 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、APIキーを設定します。

```bash
cp .env.example .env
# .env を編集して GEMINI_API_KEY などを設定
```
