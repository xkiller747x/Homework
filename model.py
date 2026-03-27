from __future__ import annotations

import json
import re
from pathlib import Path
from urllib import error, request


QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_MODEL_NAME = "qwen-plus"
DEFAULT_PROMPT_PATH = Path(__file__).parent / "prompts" / "grading_prompt.txt"


def load_prompt(prompt_path: str | Path = DEFAULT_PROMPT_PATH) -> str:
    return Path(prompt_path).read_text(encoding="utf-8").strip()


def _normalize_message_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")))
        return "".join(text_parts).strip()

    return str(content).strip()


def _extract_score(response_text: str) -> str:
    match = re.search(r"(?<!\d)(100|\d{1,2})(?!\d)", response_text)
    if not match:
        raise ValueError(f"模型返回内容中没有找到有效分数：{response_text}")

    score = int(match.group())
    if not 0 <= score <= 100:
        raise ValueError(f"模型返回了超出范围的分数：{score}")

    return str(score)


def grade_homework(
    api_key: str,
    homework_text: str,
    homework_name: str,
    model_name: str = DEFAULT_MODEL_NAME,
    prompt_path: str | Path = DEFAULT_PROMPT_PATH,
) -> str:
    if not api_key.strip():
        raise ValueError("API Key 不能为空。")

    prompt = load_prompt(prompt_path)
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"作业文件名：{homework_name}\n作业内容如下：\n{homework_text}",
        },
    ]

    payload = json.dumps(
        {
            "model": model_name,
            "messages": messages,
            "temperature": 0,
        }
    ).encode("utf-8")

    api_request = request.Request(
        QWEN_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(api_request, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"调用千问接口失败：HTTP {exc.code} - {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"调用千问接口失败：{exc.reason}") from exc

    try:
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"接口返回格式异常：{response_data}") from exc

    response_text = _normalize_message_content(content)
    return _extract_score(response_text)
