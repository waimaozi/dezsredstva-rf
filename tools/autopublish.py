#!/usr/bin/env python3
"""
Auto-publish pipeline for дезинфицирующиесредства.рф
Fetches new disinfection research from PubMed → generates Russian digest → commits to repo

Usage:
  python3 tools/autopublish.py              # fetch & publish 1 new article
  python3 tools/autopublish.py --count 3    # fetch & publish 3 articles
  python3 tools/autopublish.py --dry-run    # preview without committing
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# --- Config ---
REPO_DIR = Path(__file__).parent.parent
ARTICLES_DIR = REPO_DIR / "src" / "content" / "articles"
STATE_FILE = REPO_DIR / "tools" / ".pubmed_state.json"

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_MODEL = "gemini-2.5-flash"
KIE_URL = f"https://api.kie.ai/{KIE_MODEL}/v1/chat/completions"

# PubMed search queries for disinfection research
PUBMED_QUERIES = [
    '("disinfectant" OR "disinfection" OR "surface decontamination") AND ("efficacy" OR "effectiveness" OR "evaluation")',
    '("hospital-acquired infection" OR "HAI") AND ("cleaning" OR "disinfection")',
    '("quaternary ammonium" OR "sodium hypochlorite" OR "hydrogen peroxide") AND ("antimicrobial" OR "virucidal")',
]


def load_state():
    """Load previously published PMIDs."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"published_pmids": [], "last_run": None}


def save_state(state):
    """Save state."""
    state["last_run"] = datetime.utcnow().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def pubmed_search(query, max_results=10):
    """Search PubMed and return list of PMIDs."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "date",
        "retmode": "json",
        "datetype": "pdat",
        "reldate": 90,
    })
    url = f"{PUBMED_SEARCH_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  Warning: PubMed search error: {e}")
        return []


def pubmed_fetch_abstract(pmid):
    """Fetch article details from PubMed."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
        "rettype": "abstract",
    })
    url = f"{PUBMED_FETCH_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            xml_text = resp.read().decode("utf-8")

        def extract_tag(xml, tag):
            match = re.search(f"<{tag}[^>]*>(.*?)</{tag}>", xml, re.DOTALL)
            return match.group(1).strip() if match else ""

        def extract_all(xml, tag):
            return re.findall(f"<{tag}[^>]*>(.*?)</{tag}>", xml, re.DOTALL)

        title = extract_tag(xml_text, "ArticleTitle")
        title = re.sub(r"<[^>]+>", "", title)

        abstract_texts = extract_all(xml_text, "AbstractText")
        abstract = "\n\n".join(re.sub(r"<[^>]+>", "", t) for t in abstract_texts)

        journal = extract_tag(xml_text, "Title")
        year = extract_tag(xml_text, "Year")

        last_names = extract_all(xml_text, "LastName")
        authors = ", ".join(last_names[:5])
        if len(last_names) > 5:
            authors += " et al."

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "year": year,
            "authors": authors,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }
    except Exception as e:
        print(f"  Warning: PubMed fetch error for {pmid}: {e}")
        return None


def is_relevant(article):
    """Quick relevance check - filter out dental, veterinary, and unrelated articles."""
    irrelevant_keywords = [
        "dental", "endodontic", "periodontal", "orthodontic", "tooth", "teeth",
        "pulp", "caries", "fluoride", "implant", "prosthetic", "denture",
        "veterinary", "canine", "feline", "poultry", "cattle", "swine",
        "cosmetic", "skincare", "hair", "nail",
        "cancer", "tumor", "oncolog", "chemotherapy",
        "gene therapy", "genomic", "proteom",
    ]
    text = (article.get("title", "") + " " + article.get("abstract", "")).lower()

    # Must have at least one relevant keyword
    relevant_keywords = [
        "disinfect", "sanitiz", "decontaminat", "biocid", "antimicrobial",
        "surface", "cleaning", "hygiene", "infection control", "hospital",
        "healthcare", "nosocomial", "pathogen", "biofilm",
        "chlorine", "hypochlorite", "quaternary ammonium", "hydrogen peroxide",
        "alcohol", "peracetic", "uv-c", "ultraviolet",
    ]

    has_relevant = any(kw in text for kw in relevant_keywords)
    has_irrelevant = any(kw in text for kw in irrelevant_keywords)

    if not has_relevant:
        return False
    if has_irrelevant and not any(kw in text for kw in ["disinfect", "decontaminat", "sanitiz"]):
        return False
    return True


def generate_digest(article):
    """Generate Russian digest using kie.ai Gemini Flash."""
    if not KIE_API_KEY:
        print("  Warning: KIE_API_KEY not set, using placeholder")
        return {
            "title_ru": f"[AUTO] {article['title']}",
            "body_ru": article["abstract"],
            "tags": ["исследования"],
        }

    prompt = (
        "Ты — главный редактор экспертного портала о дезинфекции и санитарной обработке в России.\n"
        "Твоя аудитория: эпидемиологи, технологи клининга, медсёстры, специалисты пищевых производств.\n\n"
        "На основе абстракта научной статьи создай ОРИГИНАЛЬНЫЙ ЭКСПЕРТНЫЙ ДАЙДЖЕСТ на русском.\n"
        "НЕ переводи статью дословно. Пиши свой текст, используя данные из исследования.\n\n"
        "Формат ответа — строго JSON:\n"
        '{\n'
        '  "title_ru": "Заголовок — конкретный, информативный, без кликбейта",\n'
        '  "body_ru": "Текст 500-700 слов. Структура:\\n\\n'
        '## Почему это важно\\n(1 абзац — контекст проблемы для российской практики)\\n\\n'
        '## Что показало исследование\\n(2 абзаца — суть работы и ключевые цифры)\\n\\n'
        '## Практическое значение\\n(1-2 абзаца — что это меняет для специалиста: '
        'какие режимы пересмотреть, на что обратить внимание, как это соотносится с российскими СанПиН/МУ)\\n\\n'
        '## На что обратить внимание\\n(1 абзац — ограничения исследования, что ещё не доказано)",\n'
        '  "tags": ["тег1", "тег2", "тег3", "тег4"],\n'
        '  "category": "одно из: поверхности|инструменты|ЛПУ|пищепром|общепит|методы|вещества|оборудование"\n'
        '}\n\n'
        f"Оригинальная статья:\n"
        f"Title: {article['title']}\n"
        f"Authors: {article['authors']}\n"
        f"Journal: {article['journal']} ({article['year']})\n"
        f"Abstract: {article['abstract']}\n\n"
        "Ответь ТОЛЬКО JSON, без markdown блоков."
    )

    payload = json.dumps({
        "model": KIE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2000,
    })

    try:
        # Use subprocess + curl to avoid urllib SSL/proxy issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(payload)
            payload_file = f.name

        cmd = [
            "curl", "-s", "-X", "POST", KIE_URL,
            "-H", f"Authorization: Bearer {KIE_API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", f"@{payload_file}",
            "--max-time", "60",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=65)
        os.unlink(payload_file)

        if proc.returncode != 0:
            print(f"  Warning: curl error: {proc.stderr[:200]}")
            return None

        result = json.loads(proc.stdout)
        content = result["choices"][0]["message"]["content"]
        content = re.sub(r"^```json\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content.strip())
        return json.loads(content)
    except Exception as e:
        print(f"  Warning: kie.ai error: {e}")
        return None


def slugify(text):
    """Create URL slug from Russian text."""
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    text = text.lower()
    result = ""
    for char in text:
        if char in translit_map:
            result += translit_map[char]
        elif char.isascii() and (char.isalnum() or char in " -"):
            result += char
        else:
            result += " "
    result = re.sub(r"\s+", "-", result.strip())
    result = re.sub(r"-+", "-", result)
    result = result.strip("-")
    return result[:80]


def create_article_file(article, digest):
    """Create .md file in articles directory."""
    slug = slugify(digest["title_ru"])
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{slug}.md"
    filepath = ARTICLES_DIR / filename

    if filepath.exists():
        slug += f"-{article['pmid']}"
        filename = f"{slug}.md"
        filepath = ARTICLES_DIR / filename

    tags_yaml = "\n".join(f'  - "{tag}"' for tag in digest.get("tags", ["исследования"]))
    category = digest.get("category", "методы")

    frontmatter = (
        f'---\n'
        f'title: "{digest["title_ru"]}"\n'
        f'description: "{digest["title_ru"][:160]}"\n'
        f'date: {date_str}\n'
        f'category: "{category}"\n'
        f'tags:\n'
        f'{tags_yaml}\n'
        f'source: "{article["url"]}"\n'
        f'---\n'
    )

    body = digest["body_ru"]
    source_line = (
        f'\n\n---\n\n'
        f'**Источник:** [{article["authors"]}. *{article["journal"]}* ({article["year"]})]'
        f'({article["url"]})\n\n'
        f'*Дайджест подготовлен редакцией Дезинфицирующиесредства.рф на основе '
        f'рецензируемого научного исследования. Материал носит информационный характер '
        f'и не заменяет официальные инструкции производителей и нормативные документы.*\n'
    )

    content = frontmatter + "\n" + body + source_line
    filepath.write_text(content, encoding="utf-8")
    return filepath


def git_commit_and_push(files, message):
    """Commit and push changes."""
    os.chdir(REPO_DIR)
    for f in files:
        subprocess.run(["git", "add", str(f)], check=True)
    subprocess.run(["git", "commit", "-m", message], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Auto-publish disinfection research digests")
    parser.add_argument("--count", type=int, default=1, help="Number of articles to publish")
    parser.add_argument("--dry-run", action="store_true", help="Preview without committing")
    parser.add_argument("--query-index", type=int, default=None, help="Use specific query (0-based)")
    args = parser.parse_args()

    print("Autopublish pipeline started")
    print(f"  Target: {args.count} article(s), dry_run={args.dry_run}")

    state = load_state()
    published = set(state.get("published_pmids", []))
    new_files = []
    published_count = 0

    queries = PUBMED_QUERIES
    if args.query_index is not None:
        queries = [PUBMED_QUERIES[args.query_index % len(PUBMED_QUERIES)]]

    for qi, query in enumerate(queries):
        if published_count >= args.count:
            break

        print(f"\nQuery {qi+1}: {query[:60]}...")
        pmids = pubmed_search(query, max_results=20)
        print(f"  Found {len(pmids)} articles")

        for pmid in pmids:
            if published_count >= args.count:
                break
            if pmid in published:
                continue

            print(f"\nProcessing PMID {pmid}...")
            article = pubmed_fetch_abstract(pmid)
            if not article or not article["abstract"]:
                print("  No abstract, skipping")
                continue

            if not is_relevant(article):
                print(f"  Filtered out (not relevant): {article['title'][:60]}...")
                published.add(pmid)  # mark as seen so we don't retry
                continue

            print(f"  Title: {article['title'][:80]}...")
            print("  Generating digest...")
            digest = generate_digest(article)
            if not digest:
                print("  Generation failed, skipping")
                continue

            print(f"  Title RU: {digest['title_ru'][:60]}...")

            if args.dry_run:
                print("  [DRY RUN] Would create article file")
                print(f"  Tags: {digest.get('tags', [])}")
            else:
                filepath = create_article_file(article, digest)
                new_files.append(filepath)
                print(f"  Created: {filepath.name}")

            published.add(pmid)
            published_count += 1
            time.sleep(1)

    if new_files and not args.dry_run:
        print(f"\nCommitting {len(new_files)} article(s)...")
        state["published_pmids"] = list(published)
        save_state(state)
        new_files.append(STATE_FILE)
        git_commit_and_push(
            new_files,
            f"content: auto-publish {len(new_files)-1} research digest(s)"
        )
        print("Pushed to GitHub!")
    else:
        state["published_pmids"] = list(published)
        save_state(state)

    print(f"\nDone. Published: {published_count}, Total in DB: {len(published)}")


if __name__ == "__main__":
    main()
