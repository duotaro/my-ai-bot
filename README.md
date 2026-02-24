# TypeScriptエンジニアが挑む！GenAIOps独習ロードマップ 〜GeminiとLangChainで始めるAIアプリ開発〜 
TypeScript/Node.jsエンジニアが、Python、Gemini、LangChain、FastAPI、AWS、Next.jsを組み合わせて、実務レベルのAIアプリケーション（GenAIOps）を1ヶ月で構築するための実践ガイド。

## 仮想環境の準備
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

## Cloud Run へのデプロイ

### 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) のインストールと起動
- [Google Cloud SDK（gcloud CLI）](https://cloud.google.com/sdk/docs/install) のインストール
- Google Cloud プロジェクトの作成と課金アカウントの紐付け

### 初期デプロイ手順

#### 1. gcloud CLI の初期設定

```bash
# 認証
gcloud auth login

# プロジェクトをデフォルトに設定（YOUR_PROJECT_ID を実際のIDに置き換える）
gcloud config set project YOUR_PROJECT_ID

# 必要な API を有効化
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com
```

#### 2. Artifact Registry にリポジトリを作成

```bash
gcloud artifacts repositories create my-ai-bot \
    --repository-format=docker \
    --location=asia-northeast1 \
    --description="my-ai-bot Docker repository"
```

#### 3. Docker イメージをビルドしてプッシュ

```bash
# Docker 認証を設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# イメージをビルド（M1/M2/M3 Mac は --platform linux/amd64 が必須）
docker build --platform linux/amd64 \
    -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-ai-bot/server:latest .

# Artifact Registry にプッシュ
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-ai-bot/server:latest
```

#### 4. Secret Manager にシークレットを登録

```bash
echo -n "your-google-api-key" | \
    gcloud secrets create GOOGLE_API_KEY --data-file=-

echo -n "your-langfuse-secret-key" | \
    gcloud secrets create LANGFUSE_SECRET_KEY --data-file=-

echo -n "your-langfuse-public-key" | \
    gcloud secrets create LANGFUSE_PUBLIC_KEY --data-file=-
```

#### 5. Cloud Run サービスアカウントにシークレットへのアクセス権限を付与

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in GOOGLE_API_KEY LANGFUSE_SECRET_KEY LANGFUSE_PUBLIC_KEY; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor"
done
```

#### 6. Cloud Run にデプロイ

```bash
gcloud run deploy my-ai-bot \
    --image asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-ai-bot/server:latest \
    --region asia-northeast1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
    --set-secrets="LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest" \
    --set-secrets="LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest" \
    --set-env-vars="LANGFUSE_HOST=https://cloud.langfuse.com"
```

デプロイ完了後に表示される `Service URL` が本番エンドポイントです。
`https://<Service URL>/docs` にアクセスして Swagger UI が開けば成功です。

---

### 修正後の再デプロイ手順

コードを変更したあとは、イメージの再ビルド → プッシュ → デプロイの3ステップを実行します。

```bash
# 1. イメージを再ビルド
docker build --platform linux/amd64 \
    -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-ai-bot/server:latest .

# 2. Artifact Registry にプッシュ
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-ai-bot/server:latest

# 3. Cloud Run に再デプロイ
gcloud run deploy my-ai-bot \
    --image asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-ai-bot/server:latest \
    --region asia-northeast1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
    --set-secrets="LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest" \
    --set-secrets="LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest" \
    --set-env-vars="LANGFUSE_HOST=https://cloud.langfuse.com"
```

---

## Week2 第5章: FastAPIでPython製のAI APIサーバーを構築する

