#!/usr/bin/env python3
"""
Shared RSS utilities for agents.
"""

from __future__ import annotations

import datetime as dt
import html
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RssItem:
    source: str
    title: str
    link: str
    summary: str
    published: Optional[dt.datetime]


def fetch(
    url: str,
    user_agent: str,
    timeout: int = 20,
    retries: int = 2,
    backoff: float = 1.5,
) -> str:
    last_err = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_err = e
            time.sleep(backoff ** i)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def parse_rss(feed_xml: str, source: str) -> List[RssItem]:
    items: List[RssItem] = []
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
            items.append(RssItem(source, title, link, desc, published))

    # Atom entries
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = text_or_empty(entry.find("{http://www.w3.org/2005/Atom}title"))
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        summary = text_or_empty(entry.find("{http://www.w3.org/2005/Atom}summary"))
        updated = text_or_empty(entry.find("{http://www.w3.org/2005/Atom}updated"))
        published = parse_date(updated)
        items.append(RssItem(source, title, link, summary, published))

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
    import re

    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
