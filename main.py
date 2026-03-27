from __future__ import annotations

from pathlib import Path

from config import API_KEY_FILE, load_api_key
from model import DEFAULT_MODEL_NAME, grade_homework
from utils import load_homework_documents


MODEL_NAME = DEFAULT_MODEL_NAME
HOMEWORK_DIR = Path("file")
RESULT_FILE = Path("result.txt")


def write_results(result_lines: list[str], result_file: Path = RESULT_FILE) -> None:
    result_file.write_text("\n".join(result_lines), encoding="utf-8")


def main() -> None:
    api_key = load_api_key()

    homeworks, ignored_files, failed_files = load_homework_documents(HOMEWORK_DIR)
    result_lines: list[str] = []

    if not homeworks:
        write_results(result_lines)
        print("未找到可批改的 .doc 或 .docx 作业文件，请检查 file 文件夹。")
        if failed_files:
            print("以下 Word 文件读取失败：")
            for failed_file in failed_files:
                print(f"- {failed_file.path}：{failed_file.reason}")
        return

    for homework in homeworks:
        try:
            score = grade_homework(
                api_key=api_key,
                homework_text=homework.text,
                homework_name=homework.name,
                model_name=MODEL_NAME,
            )
            result_lines.append(f"{homework.name} {score}")
            print(f"已完成批改：{homework.name} -> {score}")
        except Exception as exc:
            print(f"批改失败：{homework.name}，原因：{exc}")

    write_results(result_lines)

    if ignored_files:
        print("以下文件未参与批改（当前仅支持 .doc 和 .docx）：")
        for file_path in ignored_files:
            print(f"- {file_path}")

    if failed_files:
        print("以下 Word 文件读取失败：")
        for failed_file in failed_files:
            print(f"- {failed_file.path}：{failed_file.reason}")

    print(f"批改结果已写入：{RESULT_FILE}")
    print(f"API Key 来源：{API_KEY_FILE.name}")


if __name__ == "__main__":
    main()
