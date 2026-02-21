FROM python:3.12-slim

WORKDIR /app

# sentence-transformers のビルドに必要なシステムパッケージ
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 依存ライブラリのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 埋め込みモデルをビルド時にダウンロードしてキャッシュ
# こうすることで、コンテナ起動時のコールドスタートが速くなる
RUN python -c "from langchain_community.embeddings import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')"

# アプリケーションコードのコピー
COPY . .

# Cloud Run はデフォルトでポート8080を使用する
EXPOSE 8080

# PORT環境変数を参照（Cloud Runが自動設定する）
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}"]