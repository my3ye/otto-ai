"""Website scraper for landing page pipeline.

Scrapes an existing website to extract content for copy synthesis.
Fetches home page + up to 5 internal pages (about, services, etc.).
"""

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("otto.scraper")

MAX_PAGES = 6
MAX_TEXT_PER_PAGE = 3000
TIMEOUT = 15
PRIORITY_PATHS = {"about", "services", "products", "pricing", "contact", "team", "features"}


async def scrape_website(url: str, max_pages: int = MAX_PAGES) -> dict:
    """Scrape a website for content.

    Returns:
        {
            "home": { "url": ..., "title": ..., "meta_description": ..., "headings": [...], "body_text": ..., "testimonials": [...] },
            "pages": [ { same structure } ],
            "nav_links": [...],
            "error": null | "message"
        }
    """
    if not url:
        return {"home": None, "pages": [], "nav_links": [], "error": "No URL provided"}

    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    base_domain = urlparse(url).netloc

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OttoBot/1.0; +https://otto.lk)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as client:
            # Fetch home page
            home_resp = await client.get(url)
            home_resp.raise_for_status()
            home_data = _extract_page(home_resp.text, url)

            # Find internal links from nav/footer
            soup = BeautifulSoup(home_resp.text, "html.parser")
            internal_links = _find_internal_links(soup, url, base_domain)
            home_data["url"] = str(home_resp.url)

            # Fetch sub-pages (prioritize about/services/etc)
            pages = []
            seen = {str(home_resp.url).rstrip("/")}
            ranked = _rank_links(internal_links)

            for link in ranked[:max_pages - 1]:
                normalized = link.rstrip("/")
                if normalized in seen:
                    continue
                seen.add(normalized)
                try:
                    resp = await client.get(link)
                    resp.raise_for_status()
                    page_data = _extract_page(resp.text, link)
                    page_data["url"] = link
                    pages.append(page_data)
                except Exception as exc:
                    log.debug("Failed to fetch %s: %s", link, exc)

            log.info("Scraped %s: home + %d sub-pages", url, len(pages))

            return {
                "home": home_data,
                "pages": pages,
                "nav_links": internal_links[:20],
                "error": None,
            }

    except Exception as exc:
        log.warning("Failed to scrape %s: %s", url, exc)
        return {"home": None, "pages": [], "nav_links": [], "error": str(exc)[:500]}


def _extract_page(html: str, url: str) -> dict:
    """Extract structured content from a single HTML page."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style/nav/footer noise
    for tag in soup.find_all(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else None

    meta_desc = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    # Headings
    headings = []
    for level in ["h1", "h2", "h3"]:
        for h in soup.find_all(level):
            text = h.get_text(strip=True)
            if text and len(text) > 2:
                headings.append({"level": level, "text": text[:200]})

    # Body text (paragraphs + list items)
    body_parts = []
    for tag in soup.find_all(["p", "li"]):
        text = tag.get_text(strip=True)
        if text and len(text) > 10:
            body_parts.append(text)
    body_text = "\n".join(body_parts)[:MAX_TEXT_PER_PAGE]

    # Testimonials (look for common patterns)
    testimonials = _extract_testimonials(soup)

    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings[:30],
        "body_text": body_text,
        "testimonials": testimonials,
    }


def _extract_testimonials(soup: BeautifulSoup) -> list[dict]:
    """Try to find testimonials/reviews on the page."""
    testimonials = []

    # Look for blockquotes
    for bq in soup.find_all("blockquote"):
        text = bq.get_text(strip=True)
        if text and len(text) > 20:
            testimonials.append({"quote": text[:500], "source": "blockquote"})

    # Look for elements with testimonial-like classes
    for cls_pattern in ["testimonial", "review", "quote", "client-say"]:
        for el in soup.find_all(class_=re.compile(cls_pattern, re.I)):
            text = el.get_text(strip=True)
            if text and len(text) > 20:
                testimonials.append({"quote": text[:500], "source": cls_pattern})

    return testimonials[:10]


def _find_internal_links(soup: BeautifulSoup, base_url: str, base_domain: str) -> list[str]:
    """Extract internal links from nav and footer."""
    links = set()
    # Prioritize nav and footer links
    for container in soup.find_all(["nav", "footer", "header"]):
        for a in container.find_all("a", href=True):
            href = a["href"]
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                # Skip anchors, assets, external
                if not parsed.path.endswith((".pdf", ".jpg", ".png", ".css", ".js")):
                    links.add(full.split("#")[0].split("?")[0])

    return list(links)


def _rank_links(links: list[str]) -> list[str]:
    """Rank internal links by relevance (about/services/pricing first)."""
    def score(url: str) -> int:
        path = urlparse(url).path.lower().strip("/")
        for i, keyword in enumerate(PRIORITY_PATHS):
            if keyword in path:
                return i
        return len(PRIORITY_PATHS) + 1

    return sorted(links, key=score)
