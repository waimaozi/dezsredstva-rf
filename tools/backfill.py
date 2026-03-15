#!/usr/bin/env python3
"""
Backfill: generate 15 articles with backdated dates.
Uses autopublish.py logic but overrides dates.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
ARTICLES_DIR = REPO_DIR / "src" / "content" / "articles"
STATE_FILE = REPO_DIR / "tools" / ".pubmed_state.json"

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_MODEL = "gemini-2.5-flash"
KIE_URL = f"https://api.kie.ai/{KIE_MODEL}/v1/chat/completions"

TARGET_COUNT = 15
START_DATE = datetime(2026, 3, 1)

QUERIES = [
    '("disinfectant" OR "disinfection") AND ("efficacy" OR "surface") AND ("hospital" OR "healthcare")',
    '("surface decontamination" OR "environmental cleaning") AND ("pathogen" OR "bacteria" OR "virus")',
    '("hydrogen peroxide" OR "sodium hypochlorite" OR "quaternary ammonium") AND ("disinfection" OR "biocidal")',
    '("infection control" OR "nosocomial") AND ("cleaning" OR "disinfection" OR "hygiene")',
    '("biofilm" OR "contamination") AND ("surface" OR "equipment") AND ("hospital" OR "food")',
]

IRRELEVANT = [
    "dental", "endodontic", "periodontal", "orthodontic", "tooth", "teeth",
    "pulp", "caries", "fluoride", "implant", "prosthetic", "denture",
    "veterinary", "canine", "feline", "poultry", "cattle", "swine",
    "cosmetic", "skincare", "cancer", "tumor", "oncolog", "chemotherapy",
    "gene therapy", "genomic", "proteom",
]

RELEVANT = [
    "disinfect", "sanitiz", "decontaminat", "biocid", "antimicrobial",
    "surface", "cleaning", "hygiene", "infection control", "hospital",
    "healthcare", "nosocomial", "pathogen", "biofilm",
    "chlorine", "hypochlorite", "quaternary ammonium", "hydrogen peroxide",
]


def pubmed_search(query, max_results=30):
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query, "retmax": max_results,
        "sort": "date", "retmode": "json", "datetype": "pdat", "reldate": 180,
    })
    try:
        with urllib.request.urlopen(f"{PUBMED_SEARCH_URL}?{params}", timeout=15) as r:
            return json.loads(r.read()).get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  Search error: {e}")
        return []


def pubmed_fetch(pmid):
    params = urllib.parse.urlencode({
        "db": "pubmed", "id": pmid, "retmode": "xml", "rettype": "abstract",
    })
    try:
        with urllib.request.urlopen(f"{PUBMED_FETCH_URL}?{params}", timeout=15) as r:
            xml = r.read().decode("utf-8")
        def ext(tag):
            m = re.search(f"<{tag}[^>]*>(.*?)</{tag}>", xml, re.DOTALL)
            return re.sub(r"<[^>]+>", "", m.group(1).strip()) if m else ""
        def ext_all(tag):
            return [re.sub(r"<[^>]+>", "", t) for t in re.findall(f"<{tag}[^>]*>(.*?)</{tag}>", xml, re.DOTALL)]
        title = ext("ArticleTitle")
        abstract = "\n\n".join(ext_all("AbstractText"))
        names = ext_all("LastName")
        authors = ", ".join(names[:5]) + (" et al." if len(names) > 5 else "")
        return {"pmid": pmid, "title": title, "abstract": abstract,
                "journal": ext("Title"), "year": ext("Year"), "authors": authors,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
    except Exception as e:
        print(f"  Fetch error {pmid}: {e}")
        return None


def is_relevant(a):
    text = (a.get("title", "") + " " + a.get("abstract", "")).lower()
    has_rel = any(k in text for k in RELEVANT)
    has_irrel = any(k in text for k in IRRELEVANT)
    if not has_rel:
        return False
    if has_irrel and not any(k in text for k in ["disinfect", "decontaminat", "sanitiz"]):
        return False
    return True


def generate_digest(article):
    if not KIE_API_KEY:
        return {"title_ru": article["title"], "body_ru": article["abstract"], "tags": ["исследования"]}
    prompt = (
        "Ты — редактор научно-популярного блога о дезинфекции на русском языке.\n\n"
        "На основе абстракта научной статьи напиши качественный дайджест на русском.\n\n"
        "Формат — строго JSON:\n"
        '{"title_ru":"Заголовок","body_ru":"Текст 400-600 слов. Введение -> Что изучали -> '
        'Результаты -> Практическое значение. Профессионально.","tags":["тег1","тег2","тег3"]}\n\n'
        f"Title: {article['title']}\nAuthors: {article['authors']}\n"
        f"Journal: {article['journal']} ({article['year']})\nAbstract: {article['abstract']}\n\n"
        "Ответь ТОЛЬКО JSON."
    )
    payload = json.dumps({"model": KIE_MODEL, "messages": [{"role": "user", "content": prompt}],
                          "temperature": 0.3, "max_tokens": 2000})
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(payload)
            pf = f.name
        proc = subprocess.run(["curl", "-s", "-X", "POST", KIE_URL,
            "-H", f"Authorization: Bearer {KIE_API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", f"@{pf}", "--max-time", "60"],
            capture_output=True, text=True, timeout=65)
        os.unlink(pf)
        result = json.loads(proc.stdout)
        content = result["choices"][0]["message"]["content"]
        content = re.sub(r"^```json\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content.strip())
        return json.loads(content)
    except Exception as e:
        print(f"  kie.ai error: {e}")
        return None


def slugify(text):
    tr = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z',
          'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
          'с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
          'щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}
    r = "".join(tr.get(c, c if c.isascii() and (c.isalnum() or c in " -") else " ") for c in text.lower())
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", r.strip())).strip("-")[:80]


def main():
    print(f"Backfill: generating {TARGET_COUNT} articles with dates {START_DATE.date()} to today")

    # Load state
    state = {"published_pmids": []}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    seen = set(state.get("published_pmids", []))

    # Collect PMIDs from all queries
    all_pmids = []
    for q in QUERIES:
        pmids = pubmed_search(q, 30)
        all_pmids.extend(pmids)
        print(f"  Query found {len(pmids)} articles")
        time.sleep(0.5)

    # Deduplicate
    all_pmids = list(dict.fromkeys(all_pmids))
    print(f"Total unique PMIDs: {len(all_pmids)}")

    # Calculate dates (spread evenly)
    today = datetime(2026, 3, 15)
    days_range = (today - START_DATE).days
    date_step = max(1, days_range // TARGET_COUNT)

    created = 0
    new_files = []

    for pmid in all_pmids:
        if created >= TARGET_COUNT:
            break
        if pmid in seen:
            continue

        article = pubmed_fetch(pmid)
        if not article or not article["abstract"]:
            continue
        if not is_relevant(article):
            seen.add(pmid)
            continue

        print(f"\n[{created+1}/{TARGET_COUNT}] PMID {pmid}: {article['title'][:60]}...")
        digest = generate_digest(article)
        if not digest:
            continue

        # Assign backdated date
        article_date = START_DATE + timedelta(days=date_step * created)
        date_str = article_date.strftime("%Y-%m-%d")

        slug = slugify(digest["title_ru"])
        filepath = ARTICLES_DIR / f"{slug}.md"
        if filepath.exists():
            filepath = ARTICLES_DIR / f"{slug}-{pmid}.md"

        tags_yaml = "\n".join(f'  - "{t}"' for t in digest.get("tags", ["исследования"]))
        content = (
            f'---\ntitle: "{digest["title_ru"]}"\n'
            f'description: "{digest["title_ru"][:160]}"\n'
            f'date: {date_str}\ntags:\n{tags_yaml}\n'
            f'source: "{article["url"]}"\n---\n\n'
            f'{digest["body_ru"]}\n\n---\n\n'
            f'*Источник: [{article["authors"]}. {article["journal"]} ({article["year"]})]({article["url"]})*\n'
        )
        filepath.write_text(content, encoding="utf-8")
        new_files.append(filepath)
        seen.add(pmid)
        created += 1
        print(f"  -> {filepath.name} (date: {date_str})")
        time.sleep(1.5)  # rate limit kie.ai

    if new_files:
        state["published_pmids"] = list(seen)
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

        os.chdir(REPO_DIR)
        for f in new_files:
            subprocess.run(["git", "add", str(f)], check=True)
        subprocess.run(["git", "add", str(STATE_FILE)], check=True)
        subprocess.run(["git", "commit", "-m",
            f"content: backfill {len(new_files)} research digests (dates {START_DATE.date()} to {today.date()})"],
            check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
        print(f"\nDone! Created and pushed {len(new_files)} articles.")
    else:
        print("\nNo articles created.")


if __name__ == "__main__":
    main()
