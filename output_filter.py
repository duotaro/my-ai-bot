import re
from typing import Optional

# 機密情報のパターン（簡易版）
SENSITIVE_PATTERNS = [
    r"sk-[a-zA-Z0-9]{32,}",  # OpenAI/AnthropicのようなAPIキー
    r"pk-lf-[a-zA-Z0-9-]+",  # Langfuse Public Key
    r"sk-lf-[a-zA-Z0-9-]+",  # Langfuse Secret Key
    r"AIza[0-9A-Za-z_-]{35}",  # Google API Key
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # メールアドレス (例)
]

# 有害コンテンツのキーワード（簡易版）
HARMFUL_KEYWORDS = [
    "暴力",
    "差別",
    "誹謗中傷",
    # ... 実際にはより詳細なリストが必要
]


class OutputFilterError(Exception):
    """出力フィルタリングエラー"""
    pass


def filter_output(output_text: str) -> str:
    """
    LLMの出力をフィルタリングする。

    Args:
        output_text: LLMからの出力テキスト

    Returns:
        フィルタリングされた出力テキスト

    Raises:
        OutputFilterError: 機密情報や有害コンテンツが検出された場合
    """
    # 1. 機密情報の検知
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, output_text):
            raise OutputFilterError(
                "出力に機密情報の可能性があるパターンが検出されました"
            )

    # 2. 有害コンテンツの検知（簡易版）
    for keyword in HARMFUL_KEYWORDS:
        if keyword in output_text:
            # 実際には、前後の文脈を考慮した判定が必要
            # （例：「暴力的な表現を避けるべき」は有害ではない）
            raise OutputFilterError(
                "出力に不適切なコンテンツが含まれている可能性があります"
            )

    return output_text