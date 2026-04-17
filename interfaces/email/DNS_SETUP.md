# Otto Email Server — DNS Setup Guide

Self-hosted Postfix + Dovecot via docker-mailserver on otto.lk.

## Server Details

- **Server IP:** 34.172.144.34
- **Mail domain:** otto.lk
- **Mail hostname:** mail.otto.lk
- **Primary mailbox:** otto@otto.lk

---

## Required DNS Records

Add these records to the otto.lk DNS zone (wherever DNS is managed).

### 1. MX Record (receives inbound email)
```
Type:  MX
Name:  @  (or otto.lk)
Value: mail.otto.lk
TTL:   3600
Priority: 10
```

### 2. A Record (resolves mail.otto.lk to server IP)
```
Type:  A
Name:  mail
Value: 34.172.144.34
TTL:   3600
```

### 3. SPF Record (prevents spoofing, improves deliverability)
```
Type:  TXT
Name:  @  (or otto.lk)
Value: v=spf1 mx a ip4:34.172.144.34 ~all
TTL:   3600
```

### 4. DKIM Record (generated after first server start)

After running `setup.sh`, get the DKIM value:
```bash
cat ~/interfaces/email/data/config/opendkim/keys/otto.lk/mail.txt
```

Add the output as a TXT record:
```
Type:  TXT
Name:  mail._domainkey.otto.lk
Value: v=DKIM1; k=rsa; p=<long key from file>
TTL:   3600
```

### 5. DMARC Record (policy for failed SPF/DKIM)
```
Type:  TXT
Name:  _dmarc.otto.lk
Value: v=DMARC1; p=quarantine; rua=mailto:postmaster@otto.lk; fo=1
TTL:   3600
```

### 6. PTR Record (reverse DNS — required for deliverability)

Set on your GCP VM:
- GCP Console → Compute Engine → VM instance → Network interface → Edit
- Set "External IP" → "Reserved static IP"
- Then set PTR/rDNS: `mail.otto.lk` pointing to `34.172.144.34`

Or via GCP CLI:
```bash
gcloud compute addresses update <static-ip-name> --ptr-record=mail.otto.lk
```

---

## GCP Firewall Rules

GCP blocks port 25 by default. Open required ports:
```bash
# SMTP receive (port 25 — needs GCP policy lift request)
gcloud compute firewall-rules create allow-smtp \
  --allow tcp:25 --target-tags mail-server

# SMTP submission (port 587)
gcloud compute firewall-rules create allow-smtp-submission \
  --allow tcp:587 --target-tags mail-server

# SMTPS (port 465)
gcloud compute firewall-rules create allow-smtps \
  --allow tcp:465 --target-tags mail-server

# IMAPS (port 993)
gcloud compute firewall-rules create allow-imaps \
  --allow tcp:993 --target-tags mail-server
```

**Note on port 25:** GCP requires a support ticket to unblock outbound port 25.
Alternative: use Mailgun/Sendgrid as SMTP relay for outbound delivery (configure
in mailserver.env: RELAY_HOST=smtp.mailgun.org), which avoids the GCP port 25 restriction.

---

## SSL Certificate

After DNS propagates (24-48h), replace self-signed cert with Let's Encrypt:
```bash
# Install certbot
sudo apt install certbot

# Stop mail server temporarily
cd ~/interfaces/email && docker compose stop mailserver

# Obtain cert
sudo certbot certonly --standalone -d mail.otto.lk

# Copy certs
sudo cp /etc/letsencrypt/live/mail.otto.lk/fullchain.pem data/config/ssl/cert.pem
sudo cp /etc/letsencrypt/live/mail.otto.lk/privkey.pem data/config/ssl/key.pem
sudo chown web3relic:web3relic data/config/ssl/*.pem

# Restart
docker compose up -d mailserver
```

---

## Quick Start

```bash
cd ~/interfaces/email

# Set mailbox password
export OTTO_EMAIL_PASSWORD=<strong-password>

# Run setup (creates mailbox + DKIM keys + starts server)
./setup.sh

# Check status
docker ps | grep otto-mailserver
curl http://localhost:8100/email/status
```

---

## Adding to ~/memory/.env

```bash
echo "OTTO_EMAIL_ADDRESS=otto@otto.lk" >> ~/memory/.env
echo "OTTO_EMAIL_PASSWORD=<password>" >> ~/memory/.env
echo "OTTO_SMTP_HOST=mail.otto.lk" >> ~/memory/.env
echo "OTTO_IMAP_HOST=mail.otto.lk" >> ~/memory/.env
# Restart memory API
sudo systemctl restart otto-memory
```

---

## Port Reference

| Port | Protocol | Purpose | Service |
|------|----------|---------|---------|
| 25   | SMTP     | Receive inbound mail from internet | Postfix |
| 465  | SMTPS    | Secure SMTP submission (legacy SSL) | Postfix |
| 587  | SMTP/TLS | SMTP submission (STARTTLS) | Postfix |
| 143  | IMAP     | IMAP access (STARTTLS) | Dovecot |
| 993  | IMAPS    | IMAP access (SSL) | Dovecot |
| 8180 | HTTP     | PostfixAdmin web UI | Management |
