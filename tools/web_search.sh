#!/bin/bash
# web_search.sh — Search the web via DuckDuckGo and return result titles/URLs/snippets.
# Usage: web_search.sh "<query>" [max_results]
# Output: plain text results to stdout; errors to stderr.

set -euo pipefail

QUERY="${1:?Usage: web_search.sh \"<query>\" [max_results]}"
MAX_RESULTS="${2:-10}"

# URL-encode query
ENCODED_QUERY=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$QUERY")

# DuckDuckGo HTML search (no API key needed)
DDG_URL="https://html.duckduckgo.com/html/?q=${ENCODED_QUERY}"

HTML=$(curl -sf --max-time 15 --location \
    -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.5" \
    -b "kl=en-us" \
    "$DDG_URL" 2>/dev/null) || {
    echo "ERROR: Failed to reach DuckDuckGo" >&2
    exit 1
}

# Parse results with Python
echo "$HTML" | python3 -c "
import sys, re

html = sys.stdin.read()
max_results = int('${MAX_RESULTS}')

# Extract result blocks — DDG HTML wraps each result in <div class='result'>
results = re.findall(
    r'<a[^>]+class=\"result__a\"[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>.*?<a[^>]+class=\"result__snippet\"[^>]*>(.*?)</a>',
    html, re.DOTALL
)

if not results:
    # Fallback: grab any links with result__a class
    titles = re.findall(r'class=\"result__a\"[^>]*>(.*?)</a>', html, re.DOTALL)
    urls = re.findall(r'class=\"result__url\"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = re.findall(r'class=\"result__snippet\"[^>]*>(.*?)</a>', html, re.DOTALL)
    results = list(zip(urls, titles, snippets))[:max_results]

def clean(s):
    s = re.sub(r'<[^>]+>', '', s)       # strip HTML tags
    s = re.sub(r'&amp;', '&', s)
    s = re.sub(r'&lt;', '<', s)
    s = re.sub(r'&gt;', '>', s)
    s = re.sub(r'&quot;', '\"', s)
    s = re.sub(r'&#x27;', \"'\", s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

if not results:
    print('No results found. DuckDuckGo may have changed their HTML format.')
    sys.exit(0)

print(f'Search: ${QUERY}')
print(f'Results ({min(len(results), max_results)} shown):\n')

for i, (url, title, snippet) in enumerate(results[:max_results], 1):
    url = clean(url)
    title = clean(title)
    snippet = clean(snippet)
    # DDG wraps URLs in redirects — extract the actual URL
    actual_url = re.search(r'uddg=([^&]+)', url)
    if actual_url:
        import urllib.parse
        url = urllib.parse.unquote(actual_url.group(1))
    print(f'{i}. {title}')
    print(f'   URL: {url}')
    if snippet:
        print(f'   {snippet}')
    print()
"
