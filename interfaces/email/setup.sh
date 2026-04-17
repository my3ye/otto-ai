#!/usr/bin/env bash
# Otto Email Server Setup Script
# Bootstraps docker-mailserver (Postfix + Dovecot) for otto.lk
#
# Run this AFTER DNS records are pointed to this server.
# See DNS_SETUP.md for required records.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}=== Otto Email Server Setup ===${NC}"

# 1. Pull the docker-mailserver setup helper
echo -e "\n${YELLOW}1. Downloading docker-mailserver setup helper...${NC}"
if [ ! -f setup.py ]; then
    curl -o setup.py https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh
    chmod +x setup.py
fi

# 2. Generate self-signed SSL cert (replace with real cert once DNS is set)
echo -e "\n${YELLOW}2. Generating SSL certificate...${NC}"
if [ ! -f data/config/ssl/cert.pem ]; then
    openssl req -new -x509 -days 365 -nodes \
        -subj "/CN=mail.otto.lk/O=Ottolabs/C=LK" \
        -keyout data/config/ssl/key.pem \
        -out data/config/ssl/cert.pem
    echo -e "${GREEN}Self-signed cert created. Replace with Let's Encrypt cert after DNS propagates.${NC}"
fi

# 3. Create the otto mailbox
echo -e "\n${YELLOW}3. Creating otto@otto.lk mailbox...${NC}"
docker run --rm \
    -v "${SCRIPT_DIR}/data/config:/tmp/docker-mailserver" \
    docker.io/mailserver/docker-mailserver:latest setup email add otto@otto.lk "${OTTO_EMAIL_PASSWORD:-changeme_set_password}"

# 4. Generate DKIM keys
echo -e "\n${YELLOW}4. Generating DKIM keys...${NC}"
docker run --rm \
    -v "${SCRIPT_DIR}/data/config:/tmp/docker-mailserver" \
    docker.io/mailserver/docker-mailserver:latest setup config dkim domain otto.lk

echo -e "\n${GREEN}DKIM key generated. Get DNS value with:${NC}"
echo "  cat data/config/opendkim/keys/otto.lk/mail.txt"

# 5. Start the stack
echo -e "\n${YELLOW}5. Starting mail server...${NC}"
docker compose up -d

echo -e "\n${GREEN}=== Mail server started ===${NC}"
echo -e "SMTP submission: port 587 (STARTTLS)"
echo -e "IMAPS:           port 993 (SSL)"
echo -e "PostfixAdmin:    http://localhost:8180"
echo -e "\nNext steps:"
echo -e "  1. Update ~/memory/.env with: OTTO_EMAIL_ADDRESS=otto@otto.lk OTTO_EMAIL_PASSWORD=<password>"
echo -e "  2. Configure DNS records (see DNS_SETUP.md)"
echo -e "  3. Obtain Let's Encrypt cert: certbot certonly --standalone -d mail.otto.lk"
echo -e "  4. Restart: docker compose restart mailserver"
