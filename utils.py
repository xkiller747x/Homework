from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile
import sys
from xml.etree import ElementTree
import zipfile


WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass
class HomeworkDocument:
    path: Path
    text: str

    @property
    def name(self) -> str:
        return self.path.name


@dataclass
class HomeworkLoadFailure:
    path: Path
    reason: str


def find_all_files(root_dir: str | Path = "file") -> list[Path]:
    root_path = Path(root_dir)
    if not root_path.exists():
        return []

    return sorted(path for path in root_path.rglob("*") if path.is_file())


def _paragraph_to_text(paragraph: ElementTree.Element) -> str:
    parts: list[str] = []

    for node in paragraph.iter():
        tag_name = node.tag.rsplit("}", 1)[-1]
        if tag_name == "t":
            parts.append(node.text or "")
        elif tag_name == "tab":
            parts.append("\t")
        elif tag_name in {"br", "cr"}:
            parts.append("\n")

    return "".join(parts).strip()


def read_docx(file_path: str | Path) -> str:
    docx_path = Path(file_path)

    with zipfile.ZipFile(docx_path, "r") as zip_file:
        document_xml = zip_file.read("word/document.xml")

    root = ElementTree.fromstring(document_xml)
    paragraphs = []

    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        paragraph_text = _paragraph_to_text(paragraph)
        if paragraph_text:
            paragraphs.append(paragraph_text)

    return "\n".join(paragraphs).strip()


def read_doc(file_path: str | Path) -> str:
    doc_path = Path(file_path).resolve()
    if not sys.platform.startswith("win"):
        raise RuntimeError("当前 .doc 读取方案仅支持 Windows 环境。")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
        temp_txt_path = Path(temp_file.name)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".ps1", mode="w", encoding="utf-8"
    ) as script_file:
        script_path = Path(script_file.name)
        script_path.write_text(
            """
param([string]$source, [string]$target)

$ErrorActionPreference = "Stop"
$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($source, [ref]$false, [ref]$true)
    [System.IO.File]::WriteAllText(
        $target,
        $document.Content.Text,
        [System.Text.UTF8Encoding]::new($false)
    )
}
finally {
    if ($document -ne $null) {
        $document.Close([ref]$false)
    }
    if ($word -ne $null) {
        $word.Quit()
    }
}
""".strip(),
            encoding="utf-8",
        )

    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(doc_path),
                str(temp_txt_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        text = temp_txt_path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(
                "读取 .doc 文件失败：Word 未提取到正文内容，请检查文档是否损坏，"
                "或确认当前环境可正常调用 Microsoft Word。"
            )
        return text
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 PowerShell，无法读取 .doc 文件。") from exc
    except subprocess.CalledProcessError as exc:
        error_message = exc.stderr.strip() or exc.stdout.strip() or "未知错误"
        raise RuntimeError(
            "读取 .doc 文件失败，请确认当前系统已安装 Microsoft Word。"
            f" 详细信息：{error_message}"
        ) from exc
    finally:
        if temp_txt_path.exists():
            temp_txt_path.unlink()
        if script_path.exists():
            script_path.unlink()


def read_word_document(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".docx":
        return read_docx(path)
    if suffix == ".doc":
        return read_doc(path)

    raise ValueError(f"暂不支持读取该文件类型：{path.suffix}")


def load_homework_documents(
    root_dir: str | Path = "file",
) -> tuple[list[HomeworkDocument], list[Path], list[HomeworkLoadFailure]]:
    documents: list[HomeworkDocument] = []
    ignored_files: list[Path] = []
    failed_files: list[HomeworkLoadFailure] = []

    for file_path in find_all_files(root_dir):
        if file_path.suffix.lower() in {".doc", ".docx"}:
            try:
                documents.append(
                    HomeworkDocument(path=file_path, text=read_word_document(file_path))
                )
            except Exception as exc:
                failed_files.append(HomeworkLoadFailure(path=file_path, reason=str(exc)))
        else:
            ignored_files.append(file_path)

    return documents, ignored_files, failed_files
