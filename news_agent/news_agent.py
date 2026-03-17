#!/usr/bin/env python3
"""
Agentic daily news summarizer.

Workflow:
1) Plan: define sources and time window.
2) Gather: fetch RSS feeds with retries.
3) Normalize: parse items, clean text, dedupe by link/title similarity.
4) Prioritize: score by recency + source diversity.
5) Summarize: extractive summary (no external API) with sentence scoring.
6) Publish: write Markdown digest + console output.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

# ---- Configuration ----

DEFAULT_SOURCES = {
    "BBC": "https://feeds.bbci.co.uk/news/rss.xml",
    "Reuters": "https://feeds.reuters.com/reuters/topNews",
    "AP": "https://apnews.com/apf-topnews?format=rss",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "AlJazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "TheGuardian": "https://www.theguardian.com/world/rss",
}

USER_AGENT = "news-agent/1.0 (+https://example.com)"

SOURCES_BY_TOPIC = {
    "world": DEFAULT_SOURCES,
    "tech": {
        "TheVerge": "https://www.theverge.com/rss/index.xml",
        "ArsTechnica": "https://feeds.arstechnica.com/arstechnica/index",
        "TechCrunch": "https://techcrunch.com/feed/",
        "Wired": "https://www.wired.com/feed/rss",
        "HackerNews": "https://news.ycombinator.com/rss",
        "MITTechReview": "https://www.technologyreview.com/feed/",
    },
    "finance": {
        "ReutersBusiness": "https://feeds.reuters.com/reuters/businessNews",
        "WSJMarkets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "CNBCTop": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "FT": "https://www.ft.com/rss/home",
    },
}

SUMMARY_MODE_EXTRACTIVE = "extractive"
SUMMARY_MODE_LLM = "llm"

# ---- Data ----

@dataclass
class Item:
    source: str
    title: str
    link: str
    summary: str
    published: Optional[dt.datetime]

# ---- Utilities ----

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_rss(feed_xml: str, source: str) -> List[Item]:
    items: List[Item] = []
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError:
        return items

    # RSS 2.0 items
    for channel in root.findall("./channel"):
        for it in channel.findall("./item"):
            title = text_or_empty(it.find("title"))
            link = text_or_empty(it.find("link"))
            desc = text_or_empty(it.find("description"))
            pub = text_or_empty(it.find("pubDate"))
            published = parse_date(pub)
            items.append(Item(source, title, link, desc, published))

    # Atom entries
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = text_or_empty(entry.find("{http://www.w3.org/2005/Atom}title"))
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        summary = text_or_empty(entry.find("{http://www.w3.org/2005/Atom}summary"))
        updated = text_or_empty(entry.find("{http://www.w3.org/2005/Atom}updated"))
        published = parse_date(updated)
        items.append(Item(source, title, link, summary, published))

    return items


def parse_date(s: str) -> Optional[dt.datetime]:
    s = s.strip()
    if not s:
        return None
    # RFC 2822
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            d = dt.datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            pass
    return None


def text_or_empty(el: Optional[ET.Element]) -> str:
    if el is None or el.text is None:
        return ""
    return html.unescape(el.text.strip())


def clean_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch(url: str, timeout: int = 20, retries: int = 2, backoff: float = 1.5) -> str:
    last_err = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_err = e
            time.sleep(backoff ** i)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def within_window(item: Item, hours: int) -> bool:
    if item.published is None:
        return True
    return item.published >= now_utc() - dt.timedelta(hours=hours)


def dedupe(items: List[Item]) -> List[Item]:
    seen = set()
    out = []
    for it in items:
        key = (normalize_title(it.title), normalize_url(it.link))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def normalize_title(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120]


def normalize_url(s: str) -> str:
    s = s.split("?")[0]
    s = s.rstrip("/")
    return s


def score_items(items: List[Item]) -> List[Tuple[Item, float]]:
    # Recency + source diversity bonus
    now = now_utc()
    source_counts = Counter([it.source for it in items])
    scored: List[Tuple[Item, float]] = []
    for it in items:
        age_hours = 48
        if it.published:
            age_hours = max(0.5, (now - it.published).total_seconds() / 3600)
        recency = 1.0 / age_hours
        diversity = 1.0 / (1 + source_counts[it.source])
        scored.append((it, recency + diversity))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def sentence_split(text: str) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


def summarize(text: str, max_sentences: int = 2) -> str:
    sentences = sentence_split(text)
    if not sentences:
        return ""
    words = re.findall(r"[a-zA-Z][a-zA-Z']+", text.lower())
    if not words:
        return " ".join(sentences[:max_sentences])
    freq = Counter(words)

    scores: Dict[str, float] = {}
    for sent in sentences:
        sent_words = re.findall(r"[a-zA-Z][a-zA-Z']+", sent.lower())
        if not sent_words:
            continue
        score = sum(freq[w] for w in sent_words) / len(sent_words)
        scores[sent] = score

    top = sorted(sentences, key=lambda s: scores.get(s, 0), reverse=True)
    chosen = []
    for s in top:
        if len(chosen) >= max_sentences:
            break
        chosen.append(s)
    return " ".join(chosen)


def llm_summarize(text: str, max_sentences: int = 2, model: str = "gpt-5") -> str:
    try:
        from openai import OpenAI
    except Exception:
        return ""

    prompt = (
        "Summarize the following news item in "
        f"{max_sentences} sentences. Be concise and factual.\n\n"
        f"{text}"
    )
    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": prompt}],
        )
        return (response.output_text or "").strip()
    except Exception:
        return ""


def llm_available() -> bool:
    try:
        from openai import OpenAI  # noqa: F401
        return True
    except Exception:
        return False


def build_digest(items: List[Item], max_items: int, summary_mode: str, llm_model: str) -> str:
    lines = []
    today = dt.datetime.now().strftime("%Y-%m-%d")
    lines.append(f"# Daily News Digest ({today})")
    lines.append("")
    for it in items[:max_items]:
        title = clean_text(it.title)
        summary = ""
        if it.summary:
            if summary_mode == SUMMARY_MODE_LLM:
                summary = llm_summarize(it.summary, max_sentences=2, model=llm_model)
            if not summary:
                summary = summarize(it.summary, max_sentences=2)
        published = it.published.astimezone().strftime("%Y-%m-%d %H:%M %Z") if it.published else ""
        lines.append(f"## {title}")
        if published:
            lines.append(f"- Source: {it.source}")
            lines.append(f"- Published: {published}")
        else:
            lines.append(f"- Source: {it.source}")
        if it.link:
            lines.append(f"- Link: {it.link}")
        if summary:
            lines.append(f"- Summary: {summary}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def get_sources(topic: str) -> Dict[str, str]:
    topic = (topic or "world").lower()
    return SOURCES_BY_TOPIC.get(topic, DEFAULT_SOURCES)


def run(hours: int, max_items: int, out_path: Optional[str], topic: str, summary_mode: str, llm_model: str) -> int:
    # Plan
    sources = get_sources(topic)

    if summary_mode == SUMMARY_MODE_LLM and not llm_available():
        print("[warn] OpenAI SDK not available. Falling back to extractive summaries.")
        summary_mode = SUMMARY_MODE_EXTRACTIVE

    # Gather
    all_items: List[Item] = []
    for name, url in sources.items():
        try:
            xml = fetch(url)
            items = parse_rss(xml, name)
            all_items.extend(items)
        except Exception as e:
            print(f"[warn] {name}: {e}")

    # Normalize
    for it in all_items:
        it.title = clean_text(it.title)
        it.summary = clean_text(it.summary)

    all_items = [it for it in all_items if it.title]
    all_items = [it for it in all_items if within_window(it, hours)]
    all_items = dedupe(all_items)

    # Prioritize
    scored = score_items(all_items)
    ordered = [it for it, _ in scored]

    # Summarize + Publish
    digest = build_digest(ordered, max_items, summary_mode, llm_model)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(digest)
        print(f"Wrote {out_path}")
    else:
        print(digest)

    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Daily news summarizer")
    parser.add_argument("--hours", type=int, default=int(os.environ.get("NEWS_WINDOW_HOURS", "24")))
    parser.add_argument("--max-items", type=int, default=int(os.environ.get("NEWS_MAX_ITEMS", "12")))
    parser.add_argument("--out", type=str, default=os.environ.get("NEWS_OUT", ""))
    parser.add_argument("--topic", type=str, default=os.environ.get("NEWS_TOPIC", "world"))
    parser.add_argument(
        "--summary-mode",
        type=str,
        default=os.environ.get("NEWS_SUMMARY_MODE", SUMMARY_MODE_EXTRACTIVE),
        choices=[SUMMARY_MODE_EXTRACTIVE, SUMMARY_MODE_LLM],
    )
    parser.add_argument("--llm-model", type=str, default=os.environ.get("NEWS_LLM_MODEL", "gpt-5"))
    parser.add_argument("--list-topics", action="store_true", help="List available topics and exit")
    args = parser.parse_args(argv[1:])

    if args.list_topics:
        print("Available topics:", ", ".join(sorted(SOURCES_BY_TOPIC.keys())))
        return 0

    return run(args.hours, args.max_items, args.out or None, args.topic, args.summary_mode, args.llm_model)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
