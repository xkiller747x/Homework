from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def load_homework_documents(
    root_dir: str | Path = "file",
) -> tuple[list[HomeworkDocument], list[Path]]:
    documents: list[HomeworkDocument] = []
    ignored_files: list[Path] = []

    for file_path in find_all_files(root_dir):
        if file_path.suffix.lower() == ".docx":
            documents.append(HomeworkDocument(path=file_path, text=read_docx(file_path)))
        else:
            ignored_files.append(file_path)

    return documents, ignored_files
