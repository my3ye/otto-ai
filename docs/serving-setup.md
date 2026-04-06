# WebAssist Landing Page Serving Setup

## Overview

Generated landing pages are served as static HTML at `https://webassist.otto.lk/{id}`.

Each landing page is a self-contained directory under `/var/www/webassist/{id}/` containing at minimum an `index.html`.

## Infrastructure

| Component | Detail |
|---|---|
| **Web server** | nginx 1.22.1 (Debian 12 package) |
| **Config** | `/etc/nginx/sites-available/webassist.otto.lk` |
| **Document root** | `/var/www/webassist/` |
| **SSL** | Let's Encrypt via certbot (auto-renews) |
| **Certificate** | `/etc/letsencrypt/live/webassist.otto.lk/` |
| **Owner** | `web3relic:web3relic` (Otto process can write directly) |

## URL Structure

```
https://webassist.otto.lk/{slug-or-uuid}
  → /var/www/webassist/{slug-or-uuid}/index.html
```

Example:
```
https://webassist.otto.lk/acme-corp-2026
  → /var/www/webassist/acme-corp-2026/index.html
```

## Deploying a Landing Page

From the Otto process (runs as `web3relic`):

```bash
# Create the directory and write the HTML
mkdir -p /var/www/webassist/{id}
cp generated.html /var/www/webassist/{id}/index.html

# Optional: copy assets (images, css, js)
cp -r assets/ /var/www/webassist/{id}/
```

No nginx reload needed — files are served immediately.

## Features

- **HTTP→HTTPS redirect**: All HTTP requests redirect to HTTPS (301)
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- **Gzip compression**: CSS, JS, JSON, SVG compressed automatically
- **Asset caching**: Static assets (images, fonts, CSS, JS) cached 24h with `immutable`
- **HTML caching**: 1 hour (pages may regenerate)
- **Custom 404**: Branded error page linking to webassist.ink
- **Health check**: `GET /_health` returns 200

## Integration with Landing Page API

The `POST /landing-pages/generate` pipeline writes the final HTML to the serving directory. The `html_url` field on the landing page record points to `https://webassist.otto.lk/{slug}`.

Flow:
1. API receives generation request → creates DB record with slug
2. Pipeline runs: research → competitors → design → HTML generation
3. Generator writes `index.html` to `/var/www/webassist/{slug}/`
4. Page is immediately live at `https://webassist.otto.lk/{slug}`

## Maintenance

```bash
# Check nginx status
sudo systemctl status nginx

# Test config after changes
sudo nginx -t

# Reload (zero-downtime)
sudo systemctl reload nginx

# Check SSL cert expiry
sudo certbot certificates

# Force cert renewal
sudo certbot renew --force-renewal

# List all landing pages
ls /var/www/webassist/

# Remove a landing page
rm -rf /var/www/webassist/{id}
```

## Config Location

Full nginx config: `/etc/nginx/sites-available/webassist.otto.lk`
Symlinked to: `/etc/nginx/sites-enabled/webassist.otto.lk`
