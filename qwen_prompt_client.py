#!/usr/bin/env python3
"""Simple Qwen client with prompt template support.

Usage example:
    $env:DASHSCOPE_API_KEY="your_api_key"
    python qwen_prompt_client.py --user-input "Write a short product intro" \
        --system-prompt "You are a concise copywriter." \
        --prompt-template "Task: {task}\nTone: {tone}\nLanguage: {language}" \
        --var task="introduce Qwen" \
        --var tone="professional" \
        --var language="Chinese"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from string import Formatter
from typing import Dict
from urllib import error, request

DEFAULT_MODEL = "qwen-plus"
REGION_BASE_URLS = {
    "beijing": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "singapore": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
    "virginia": "https://dashscope-us.aliyuncs.com/compatible-mode/v1/chat/completions",
}


class SafeDict(dict):
    """Leave unknown placeholders unchanged instead of crashing."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def parse_kv_pairs(items: list[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --var value: {item!r}. Use key=value.")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid --var value: {item!r}. Key cannot be empty.")
        result[key] = value
    return result


def extract_placeholders(template: str) -> list[str]:
    placeholders: list[str] = []
    for _, field_name, _, _ in Formatter().parse(template):
        if field_name:
            placeholders.append(field_name)
    return placeholders


def build_user_prompt(template: str, variables: Dict[str, str], user_input: str | None) -> str:
    payload = SafeDict(variables)
    if user_input:
        payload.setdefault("user_input", user_input)

    prompt = template.format_map(payload)

    missing = [name for name in extract_placeholders(template) if name not in payload]
    if missing:
        missing_text = ", ".join(sorted(set(missing)))
        print(
            f"Warning: missing template variables: {missing_text}. "
            "They were kept as literal placeholders.",
            file=sys.stderr,
        )
    return prompt


def call_qwen(
    api_key: str,
    model: str,
    base_url: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }

    req = request.Request(
        url=base_url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Call Alibaba Qwen through the OpenAI-compatible API with prompt support."
    )
    parser.add_argument("--api-key", default=os.getenv("DASHSCOPE_API_KEY"), help="DashScope API key.")
    parser.add_argument(
        "--region",
        choices=sorted(REGION_BASE_URLS),
        default="beijing",
        help="Alibaba Cloud region for the API endpoint.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional full chat completions endpoint. Overrides --region when set.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Qwen model name.")
    parser.add_argument(
        "--system-prompt",
        default="You are a helpful assistant.",
        help="System prompt sent as the first message.",
    )
    parser.add_argument(
        "--prompt-template",
        default="{user_input}",
        help="User prompt template. Example: 'Translate to {language}: {user_input}'.",
    )
    parser.add_argument(
        "--user-input",
        default="",
        help="Raw user input. It can be injected into the template with {user_input}.",
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        help="Template variable in key=value format. Repeat for multiple variables.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature. Valid range in the docs is >=0 and <2.",
    )
    parser.add_argument(
        "--show-request",
        action="store_true",
        help="Print the rendered system and user prompt before sending the request.",
    )

    args = parser.parse_args()

    if not args.api_key:
        print(
            "Missing API key. Set DASHSCOPE_API_KEY or pass --api-key.",
            file=sys.stderr,
        )
        return 1

    if not 0 <= args.temperature < 2:
        print("temperature must be >= 0 and < 2", file=sys.stderr)
        return 1

    try:
        variables = parse_kv_pairs(args.var)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    base_url = args.base_url or REGION_BASE_URLS[args.region]
    user_prompt = build_user_prompt(args.prompt_template, variables, args.user_input)

    if args.show_request:
        print("=== system prompt ===")
        print(args.system_prompt)
        print("=== user prompt ===")
        print(user_prompt)
        print("=== response ===")

    try:
        data = call_qwen(
            api_key=args.api_key,
            model=args.model,
            base_url=base_url,
            system_prompt=args.system_prompt,
            user_prompt=user_prompt,
            temperature=args.temperature,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
