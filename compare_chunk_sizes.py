from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# 評価用の質問
test_questions = [
    "Gemini CLIの主な機能は何ですか？",
    "Gemini CLIは誰が開発しましたか？",
]

# 試すチャンクサイズ
chunk_sizes = [200, 500, 1000, 2000]

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
loader = TextLoader("sample_knowledge.txt")
documents = loader.load()

for chunk_size in chunk_sizes:
    print(f"\n{'='*60}")
    print(f"chunk_size={chunk_size}")
    print(f"{'='*60}")

    # チャンク分割
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size * 0.1),  # 10%をオーバーラップ
    )
    chunks = text_splitter.split_documents(documents)
    print(f"チャンク数: {len(chunks)}")

    # ベクトルDB構築
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=f"test_chunk_{chunk_size}"
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # 検索テスト
    for question in test_questions:
        print(f"\nQ: {question}")
        results = retriever.invoke(question)
        print(f"取得されたチャンク:")
        for i, doc in enumerate(results, 1):
            print(f"  [{i}] {doc.page_content[:100]}...")

    # クリーンアップ
    vector_store.delete_collection()
