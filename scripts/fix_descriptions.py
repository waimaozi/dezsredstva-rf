#!/usr/bin/env python3

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


ARTICLES_DIR = Path(__file__).resolve().parent.parent / "src" / "content" / "articles"
DESCRIPTION_MIN = 150
DESCRIPTION_MAX = 160
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
HEADING_PREFIXES = (
    "Почему это важно",
    "Что показало исследование",
    "Практическое значение",
    "На что обратить внимание",
    "Что важно для практики",
    "Как использовать эти выводы в работе",
    "Что стоит проверить на объекте",
)


@dataclass
class Article:
    path: Path
    frontmatter: str
    body: str
    title: str
    description: str


def parse_article(path: Path) -> Article | None:
    raw_text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw_text)
    if not match:
        return None

    frontmatter = match.group(1)
    body = raw_text[match.end():].strip()
    title = extract_scalar(frontmatter, "title")
    description = extract_scalar(frontmatter, "description")
    if title is None or description is None:
        return None

    return Article(
        path=path,
        frontmatter=frontmatter,
        body=body,
        title=title,
        description=description,
    )


def extract_scalar(frontmatter: str, field: str) -> str | None:
    pattern = re.compile(rf"^{field}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(frontmatter)
    if not match:
        return None

    value = match.group(1).strip()
    if value.startswith(('"', "'")) and value.endswith(('"', "'")) and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def normalize_text(value: str) -> str:
    value = value.lower().replace("ё", "е")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s]", "", value, flags=re.UNICODE)
    return value.strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+.+$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sentence_candidates(body: str) -> list[str]:
    clean = strip_markdown(body)
    if not clean:
        return []
    sentences = SENTENCE_SPLIT_RE.split(clean)
    return [sentence.strip(" \n\r\t-") for sentence in sentences if sentence.strip()]


def truncate_description(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" ,;:-")
    if len(text) <= DESCRIPTION_MAX:
        return text

    hard_limit = max(DESCRIPTION_MIN, DESCRIPTION_MAX - 1)
    cut = text[: hard_limit + 1]
    boundary = max(cut.rfind(" "), cut.rfind(","), cut.rfind(";"), cut.rfind(":"))
    if boundary >= DESCRIPTION_MIN:
        cut = cut[:boundary]
    else:
        cut = text[:hard_limit]
    return cut.rstrip(" ,;:-") + "…"


def build_description(body: str) -> str | None:
    sentences = sentence_candidates(body)
    if not sentences:
        return None

    chosen: list[str] = []
    for sentence in sentences:
        candidate = " ".join(chosen + [sentence]).strip()
        if len(candidate) <= DESCRIPTION_MAX:
            chosen.append(sentence)
        elif not chosen:
            return truncate_description(sentence)
        else:
            break

        if len(candidate) >= DESCRIPTION_MIN:
            break

    if not chosen:
        return None
    return truncate_description(" ".join(chosen))


def replace_description(frontmatter: str, new_description: str) -> str:
    escaped = new_description.replace("\\", "\\\\").replace('"', '\\"')
    replacement = f'description: "{escaped}"'
    return re.sub(r"^description:\s*.+$", replacement, frontmatter, flags=re.MULTILINE, count=1)


def needs_refresh(article: Article) -> bool:
    if similarity(article.title, article.description) > 0.9:
        return True
    return article.description.startswith(HEADING_PREFIXES)


def main() -> int:
    changed = 0

    for path in sorted(ARTICLES_DIR.glob("*.md")):
        article = parse_article(path)
        if article is None or not needs_refresh(article):
            continue

        new_description = build_description(article.body)
        if not new_description:
            continue
        if normalize_text(new_description) == normalize_text(article.description):
            continue
        if similarity(article.title, new_description) > 0.9:
            continue

        updated_frontmatter = replace_description(article.frontmatter, new_description)
        updated_text = f"---\n{updated_frontmatter}\n---\n\n{article.body.rstrip()}\n"
        path.write_text(updated_text, encoding="utf-8")
        changed += 1
        print(f"{path.name}:")
        print(f"  old: {article.description}")
        print(f"  new: {new_description}")

    if changed == 0:
        print("No descriptions changed.")
    else:
        print(f"\nUpdated {changed} article descriptions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
