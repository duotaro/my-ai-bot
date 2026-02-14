import re
from typing import Optional

# プロンプトインジェクションに使われる可能性が高いキーワード
SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|commands?)",
    r"forget\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|commands?)",
    r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|commands?)",
    r"system\s+prompt",
    r"あなたの指示を無視",
    r"以前の指示を.*無視",
    r"システムプロンプトを.*教えて",
]

MAX_INPUT_LENGTH = 2000  # 最大入力文字数


class InputValidationError(Exception):
    """入力バリデーションエラー"""
    pass


def validate_input(user_input: str) -> Optional[str]:
    """
    ユーザー入力を検証する。

    Args:
        user_input: ユーザーからの入力文字列

    Returns:
        検証に成功した場合はNone、失敗した場合はエラーメッセージ

    Raises:
        InputValidationError: 入力が検証に失敗した場合
    """
    # 1. 長さチェック
    if len(user_input) > MAX_INPUT_LENGTH:
        raise InputValidationError(
            f"入力が長すぎます（最大{MAX_INPUT_LENGTH}文字）"
        )

    # 2. 空文字チェック
    if not user_input.strip():
        raise InputValidationError("入力が空です")

    # 3. プロンプトインジェクションパターンのチェック
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, user_input, re.IGNORECASE):
            raise InputValidationError(
                "入力に不適切なパターンが検出されました"
            )

    return None  # 検証成功