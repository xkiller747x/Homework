from __future__ import annotations

from pathlib import Path


API_KEY_FILE = Path(__file__).parent / "api_key.local.txt"


def load_api_key(api_key_file: str | Path = API_KEY_FILE) -> str:
    api_key_path = Path(api_key_file)
    if not api_key_path.exists():
        raise ValueError(
            f"请先在 {api_key_path.name} 中写入 DashScope API Key。"
        )

    api_key = api_key_path.read_text(encoding="utf-8").strip()
    if not api_key:
        raise ValueError(
            f"{api_key_path.name} 为空，请填入真实的 DashScope API Key。"
        )

    return api_key
