#!/bin/bash
# web_fetch.sh — Fetch a URL and return clean plain text content.
# Usage: web_fetch.sh <url> [max_chars]
# Output: cleaned text to stdout; errors to stderr.

set -euo pipefail

URL="${1:?Usage: web_fetch.sh <url> [max_chars]}"
MAX_CHARS="${2:-20000}"

# Fetch HTML with a browser-like UA, follow redirects, timeout 15s
HTML=$(curl -sf --max-time 15 --location \
    -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.5" \
    "$URL" 2>/dev/null) || {
    echo "ERROR: Failed to fetch ${URL}" >&2
    exit 1
}

# Convert HTML to clean plain text
echo "$HTML" | python3 -c "
import sys, re, html2text

h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = True
h.ignore_emphasis = False
h.body_width = 0
h.unicode_snob = True
h.skip_internal_links = True

content = sys.stdin.read()
text = h.handle(content)
text = re.sub(r'\n{3,}', '\n\n', text).strip()

max_chars = int('${MAX_CHARS}')
if len(text) > max_chars:
    text = text[:max_chars] + f'\n\n[TRUNCATED — fetched {len(text)} chars, showing first {max_chars}]'

print(text)
"
