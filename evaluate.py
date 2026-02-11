import json
from langfuse import get_client
from server import rag_chain

# --- 1. Langfuseクライアントの初期化 ---
# 環境変数から自動的にAPIキーを読み取ります
langfuse = get_client()

# --- 2. 評価データセットの読み込み ---
with open("eval_dataset.json", "r", encoding="utf-8") as f:
    eval_data = json.load(f)

# --- 3. Langfuseにデータセットを登録 ---
dataset_name = "rag-eval-v1"
langfuse.create_dataset(name=dataset_name)

for item in eval_data:
    langfuse.create_dataset_item(
        dataset_name=dataset_name,
        input={"question": item["question"]},
        expected_output=item["expected_answer"],
        metadata={"criteria": item["evaluation_criteria"]},
    )

print(f"データセット '{dataset_name}' に {len(eval_data)} 件のアイテムを登録しました。")

# --- 4. データセットの各アイテムに対してRAGを実行 ---
dataset = langfuse.get_dataset(dataset_name)

for item in dataset.items:
    question = item.input["question"]
    print(f"評価中: {question}")

    # item.run() でトレースとデータセットアイテムを自動紐付け
    with item.run(run_name="rag-eval-run-v1") as span:
        response = rag_chain.invoke(question)
        print(f"  → 回答: {response.content[:80]}...")

# --- 5. 完了 ---
langfuse.flush()
print("\n評価が完了しました。Langfuse UIで結果を確認してください。")